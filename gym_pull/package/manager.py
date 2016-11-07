import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
import traceback
import sys
import gym
from six.moves import reload_module
from distutils.version import LooseVersion
from gym_pull.envs import registry

logger = logging.getLogger(__name__)

gym_abs_path = os.path.dirname(os.path.abspath(gym.__file__))
user_env_cache_name = '.envs.json'
pip_exec = 'pip3' if sys.version_info[0] == 3 else 'pip2'

class PackageManager(object):
    """
    This object is responsible for downloading and registering user environments (and their versions).
    """
    def __init__(self):
        self.env_ids = set()
        self.user_packages = {}
        self.cache_path = os.path.join(gym_abs_path, 'envs', user_env_cache_name)
        self.cache_needs_update = False

    def load_user_envs(self):
        """ Loads downloaded user envs from filesystem cache on `import gym` """
        installed_packages = self._list_packages()

        # Tagging core envs
        gym_package = 'gym ({})'.format(installed_packages['gym']) if 'gym' in installed_packages else 'gym'
        core_specs = registry.all()
        for spec in core_specs:
            spec.source = 'OpenAI Gym Core Package'
            spec.package = gym_package

        # Loading user envs
        if not os.path.isfile(self.cache_path):
            return
        with open(self.cache_path) as cache:
            for line in cache:
                user_package, registered_envs = self._load_package(line.rstrip('\n'), installed_packages)
                if logger.level <= logging.DEBUG:
                    logger.debug('Installed %d user environments from package "%s"', len(registered_envs), user_package['name'])
        if self.cache_needs_update:
            self._update_cache()
        if len(self.env_ids) > 0:
            logger.info('Found and registered %d user environments.', len(self.env_ids))

    def pull(self, source=''):
        """
        Downloads and registers a user environment from a git repository
        Args:
            source: the source where to download the envname (expected 'github.com/user/repo[@branch]')

        Note: the user environment will be registered as (username/EnvName-vVersion)
        """
        # Checking syntax
        branch_parts = source.split('@')
        if len(branch_parts) == 2:
            branch = branch_parts[1]
            source = branch_parts[0]
            git_url = 'https://{}.git@{}'.format(source, branch)
        else:
            git_url = 'https://{}.git'.format(source)

        # Validating params
        source_parts = source.split('/')
        if len(source_parts) != 3 or source_parts[0].lower() != 'github.com':
            logger.warn(""" Invalid Syntax - source must be in the format 'github.com/username/repository[@branch]'

Syntax: gym.pull('github.com/username/repository')

where username is a GitHub username, repository is the name of a GitHub repository.""")
            return

        username = source_parts[1]
        modified_packages = []

        # Installing pip package
        logger.info('Installing pip package from "%s"', git_url)
        packages_before = self._list_packages()
        return_code = self._run_cmd('{} install --upgrade git+{}'.format(pip_exec, git_url))
        if return_code != 0:        # Failed - pip will display the error message
            return

        # Detecting new and upgraded packages
        packages_after = self._list_packages()
        for package_name in packages_after:
            package_version = packages_after[package_name]
            if package_name not in packages_before:
                logger.info('Installed new package: "%s (%s)"', package_name, package_version)
                modified_packages.append(package_name)

            elif LooseVersion(packages_before[package_name]) < LooseVersion(package_version):
                logger.info('Upgraded package "%s" from "%s" to "%s"',
                            package_name, packages_before[package_name], package_version)
                modified_packages.append(package_name)

            elif LooseVersion(packages_before[package_name]) > LooseVersion(package_version):
                logger.warn('Package "%s" downgraded from "%s" to "%s". Are you sure that is what you want?',
                            package_name, packages_before[package_name], package_version)
                modified_packages.append(package_name)

        # Package conflict - check if already installed from a different source
        for package_name in modified_packages:
            if package_name in self.user_packages and source != self.user_packages[package_name]['source']:
                logger.warn('Package conflict - The package "%s" from "%s" was already installed from "%s". '
                            'Uninstalling both packages. Please reinstall the one you want.',
                            package_name, source, self.user_packages[package_name]['source'])
                self._deregister_envs_from_source(source)
                self._deregister_envs_from_source(self.user_packages[package_name]['source'])
                self._run_cmd('{} uninstall -y {}'.format(pip_exec, package_name))
                del self.user_packages[package_name]
                self._update_cache()
                return

        # Detecting if already up-to-date
        if len(modified_packages) == 0:
            logger.warn('The user environments for "%s" are already up-to-date (no new version detected).', source)
            return

        # De-register envs with same source
        self._deregister_envs_from_source(source)

        # Loading new packages
        new_envs = set([])
        uninstall_packages = []
        for package_name in modified_packages:
            json_line = json.dumps({'name': package_name, 'version': packages_after[package_name], 'source': source})
            user_package, registered_envs = self._load_package(json_line, packages_after)
            for new_env in registered_envs:
                if not new_env.lower().startswith('{}/'.format(username.lower())):
                    if len(uninstall_packages) == 0:    # We don't need to repeat the message multiple times
                        logger.warn('This package does not respect the naming convention and will be uninstalled to avoid conflicts. '
                                    'Expected user environment to start with "{}/", but got "{}" instead.'.format(username, new_env))
                    uninstall_packages.append(package_name)
            new_envs = new_envs | registered_envs

        # Removing packages and deregistering envs if they don't respect naming convention
        if len(uninstall_packages) > 0:
            self._deregister_envs_from_source(source)
            for package_name in uninstall_packages:
                self._run_cmd('{} uninstall -y {}'.format(pip_exec, package_name))
            return

        # Updating cache
        self._update_cache()

        # Displaying results
        logger.info('--------------------------------------------------')
        if len(new_envs) > 0:
            for env in sorted(new_envs, key=lambda s: s.lower()):
                logger.info('Successfully registered the environment: "%s"', env)
        else:
            logger.info('No environments have been registered. The following packages were modified: %s', ','.join(modified_packages))
        return

    def _run_cmd(self, cmd):
        p = subprocess.Popen(cmd, shell=True)
        p.communicate()
        return p.returncode

    def _deregister_envs_from_source(self, source):
        envs_to_remove = []
        for spec in registry.all():
            if spec.source == source:
                envs_to_remove.append(spec.id)
        for env_name in envs_to_remove:
            registry.deregister(env_name)
            self.env_ids.remove(env_name.lower())

    def _list_packages(self):
        packages = {}
        # package_name before first (, package version before space, comma, or ending parenthese
        # e.g. functools32 (3.2.3.post2) or gym (0.1.6, /www/ppaquette/gym) => name: functools32, version=>3.2.3.post2
        package_re = re.compile(r'^([^\(]+) \(([^ ,\)]*)')
        temp_file = os.path.join(tempfile.mkdtemp(), 'pip_list.txt')
        self._run_cmd('{} list --format=legacy --log {} > {}'.format(pip_exec, temp_file, os.devnull))

        with open(temp_file) as f:
            for line in f:
                match = package_re.search(line)
                if match is not None:
                    packages[match.group(1).strip()] = match.group(2)

        shutil.rmtree(os.path.dirname(temp_file))
        return packages

    def _update_cache(self):
        with open(self.cache_path, 'w') as cache:
            for package_name in self.user_packages:
                cache.write('{}\n'.format(json.dumps(self.user_packages[package_name])))
        self.cache_needs_update = False

    def _load_package(self, json_line, installed_packages):
        """ Returns the user_package (name, version, source), and the list of envs registered when the package was loaded """
        if len(json_line) == 0:
            return {}, set([])

        valid_json = False
        try:
            user_package = json.loads(json_line)
            valid_json = True
        except ValueError:
            user_package = {}

        package_name = user_package['name'] if 'name' in user_package else None
        module_name = package_name.replace('-', '_') if package_name is not None else ''
        envs_before = set(registry.list())

        if not valid_json or package_name is None:
            self.cache_needs_update = True
            logger.warn('Unable to load user environments. Try deleting your cache '
                        'file "%s" if this problem persists. \n\nLine: %s', self.cache_path, json_line)
            return {}, set([])
        elif package_name not in installed_packages:
            self.cache_needs_update = True
            logger.warn('The package "%s" does not seem to be installed anymore. User environments from this '
                        'package will not be registered, and the package will no longer be loaded on `import gym`', package_name)
        elif module_name in sys.modules:
            self.cache_needs_update = True
            try:
                reload_module(sys.modules[module_name])
            except ImportError:
                if 'gym' in package_name:   # To avoid uninstalling failing dependencies
                    logger.warn('Unable to reload the module "%s" from package "%s" (%s). This is usually caused by a '
                                'invalid pip package. The package will be uninstalled and no longer be loaded on `import gym`.\n',
                                module_name, package_name, installed_packages[package_name])
                    traceback.print_exc(file=sys.stdout)
                    sys.stdout.write('\n')
                    self._run_cmd('{} uninstall -y {}'.format(pip_exec, package_name))
        else:
            try:
                __import__(module_name)
            except ImportError:
                if 'gym' in package_name:   # To avoid uninstalling failing dependencies
                    self.cache_needs_update = True
                    logger.warn('Unable to import the module "%s" from package "%s" (%s). This is usually caused by a '
                                'invalid pip package. The package will be uninstalled and no longer be loaded on `import gym`.\n',
                                module_name, package_name, installed_packages[package_name])
                    traceback.print_exc(file=sys.stdout)
                    sys.stdout.write('\n')
                    self._run_cmd('{} uninstall -y {}'.format(pip_exec, package_name))

        envs_after = set(registry.list())
        registered_envs = envs_after - envs_before
        if len(registered_envs) > 0:
            self.user_packages[package_name] = user_package
        for new_env in registered_envs:
            new_spec = registry.spec(new_env)
            new_spec.source = user_package['source']
            new_spec.package = '{} ({})'.format(user_package['name'], user_package['version'])
            self.env_ids.add(new_env.lower())
        return user_package, registered_envs

# Have a global manager
manager = PackageManager()
pull = manager.pull
load_user_envs = manager.load_user_envs

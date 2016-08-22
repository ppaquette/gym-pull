import yaml
from six import string_types
import six.moves.urllib as urllib

import gym
from gym import error
from gym.scoreboard.client import api_requestor, util
from gym.scoreboard.client.resource import Evaluation, FileUpload, GymObject, APIResource

github_yaml_file = '.openai.yml'

def convert_to_gym_object(resp, api_key):
    types = {
        'evaluation': Evaluation,
        'file': FileUpload,
        'userenvconfig': UserEnvConfig,
    }

    if isinstance(resp, list):
        return [convert_to_gym_object(i, api_key) for i in resp]
    elif isinstance(resp, dict) and not isinstance(resp, GymObject):
        resp = resp.copy()
        klass_name = resp.get('object')
        if isinstance(klass_name, string_types):
            klass = types.get(klass_name, GymObject)
        else:
            klass = GymObject
        return klass.construct_from(resp, api_key)
    else:
        return resp

class UserEnvConfig(APIResource):
    """ YAML config file hosted on top-level folder of github repo """
    @classmethod
    def api_base(cls):
        return gym.scoreboard.github_raw_base

    @classmethod
    def class_path(cls):
        return ''

    def instance_path(self):
        user_repo = self.get('id', '').split('/')     # id is username/repository

        if not len(user_repo) == 2:
            raise error.InvalidRequestError(
                'Could not determine which URL to request: %s instance '
                'has missing id: %r' % (type(self).__name__, 'username/repository'), None)

        commit_hash = self.get('commit_hash', 'master')     # Downloading from master branch by default

        username = urllib.parse.quote_plus(util.utf8(user_repo[0]))
        repository = urllib.parse.quote_plus(util.utf8(user_repo[1]))
        commit_hash = urllib.parse.quote_plus(util.utf8(commit_hash))
        config_file = urllib.parse.quote_plus(util.utf8(github_yaml_file))
        return "/%s/%s/%s/%s" % (username, repository, commit_hash, config_file)

    def refresh(self):
        values = self.request('get', self.instance_path())
        values = yaml.safe_load(values)
        values['object'] = 'userenvconfig'
        self.refresh_from(values)
        return self

class CommitHash(APIResource):
    """ Returns the full commit hash from a commit ref """
    @classmethod
    def api_base(cls):
        return gym.scoreboard.github_api_base

    @classmethod
    def class_path(cls):
        return '/repos'

    def instance_path(self):
        user_repo = self.get('id', '').split('/')  # id is owner/repository/commit_ref

        if not len(user_repo) == 3:
            raise error.InvalidRequestError(
                'Could not determine which URL to request: %s instance '
                'has missing id: %r' % (type(self).__name__, 'owner/repository/commit_ref'), None)

        owner = urllib.parse.quote_plus(util.utf8(user_repo[0]))
        repository = urllib.parse.quote_plus(util.utf8(user_repo[1]))
        commit_ref = urllib.parse.quote_plus(util.utf8(user_repo[2]))
        return "%s/%s/%s/commits/%s" % (self.class_path(), owner, repository, commit_ref)

    def refresh(self):
        supplied_headers = {"Accept": "application/vnd.github.v3.sha"}
        if self.api_key is not None:
            supplied_headers["Authorization"] = "token {}".format(self.api_key)
        url = '{}{}'.format(self.api_base(), self.instance_path())
        body, code, headers = api_requestor.http_client.request('get', url, headers=supplied_headers)
        if code == 200:
            self['commit_hash'] = body
        elif code == 404:   # commit_ref not found
            self['commit_hash'] = None
        elif code == 403:   # Likely X-LimitRate exceeded
            raise error.Error(
                'Unabled to retrieve full commit hash. GitHub returned a 403/Forbidden error. Try setting the environment ' \
                'variable GITHUB_API_KEY with your GitHub OAuth2.0 key, which can be retrieved from your GitHub profile. ' \
                '-- Details: GitHub returned "{} -- {}". Tried "GET {}".'.format(code, body, self.instance_path()))
        else:               # Unhandled error
            raise error.Error(
                'Unabled to retrieve full commit hash. If error persists, please contact us at gym@openai.com with ' \
                'this message. GitHub returned "{} -- {}". Tried "GET {}".'.format(code, body, self.instance_path()))
        return self

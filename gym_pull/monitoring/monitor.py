import logging

from gym import error, version

logger = logging.getLogger(__name__)

# -+-+-+-+ PATCHING -+-+-+-+-+-+-+-+-+-
import gym

class Monitor(gym.wrappers.monitoring.Monitor):
# -+-+-+-+ /PATCHING -+-+-+-+-+-+-+-+-+-

    def _env_info(self):
        env_info = {
            'gym_version': version.VERSION,
        }
# >>>>>>>>> START changes >>>>>>>>>>>>>>>>>>>>>>>>
        properties = [
            'background', 'description', 'group', 'summary', 'nondeterministic', 'reward_threshold',
            'timestep_limit', 'trials', 'package', 'source']
        if self.env.spec:
            env_properties = self.env.spec.__dict__.copy()
            if env_properties['id'] in gym.scoreboard.registry.envs:
                env_properties.update(gym.scoreboard.registry.envs[env_properties['id']])
            env_info['env_id'] = env_properties['id']
            for property in properties:
                if property in env_properties:
                    env_info[property] = env_properties[property]
# <<<<<<<<< END changes <<<<<<<<<<<<<<<<<<<<<<<<<<
        return env_info


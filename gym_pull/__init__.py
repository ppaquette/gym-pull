import logging
import os
import re
import types
import gym
from gym.configuration import logger_setup

logger = logging.getLogger(__name__)
logger_setup(logger)
del logger_setup

# --------------------
# Modifying gym registry
# --------------------
def deregister(self, id):
    if not id in self.env_specs:
        logger.warn('Unable to deregister id: %s. Are you certain it is registered?', id)
    else:
        del self.env_specs[id]

def list(self):
    return sorted([spec.id for spec in self.all()], key=lambda s: s.lower())

import gym.envs.registration
gym.envs.registration.env_id_re = re.compile(r'^([\w/:-]+)-v(\d+)$')
gym.envs.registration.registry.deregister = types.MethodType(deregister, gym.envs.registration.registry)
gym.envs.registration.registry.list = types.MethodType(list, gym.envs.registration.registry)
gym.envs.registration.deregister = gym.envs.registration.registry.deregister
gym.envs.registration.list = gym.envs.registration.registry.list
gym.envs.deregister = gym.envs.registration.registry.deregister
gym.envs.list = gym.envs.registration.registry.list
gym.list = gym.envs.registration.registry.list

# --------------------
# Modifying gym scoreboard
# --------------------
github_api_key = os.environ.get('GITHUB_API_KEY')
github_api_base = os.environ.get('OPENAI_GITHUB_API_BASE', 'https://api.github.com')
github_raw_base = os.environ.get('OPENAI_GITHUB_RAW_BASE', 'https://raw.githubusercontent.com')
base_without_api_key = [ github_api_base, github_raw_base ]

import gym.scoreboard
gym.scoreboard.github_api_key = github_api_key
gym.scoreboard.github_api_base = github_api_base
gym.scoreboard.github_raw_base = github_raw_base
gym.scoreboard.base_without_api_key = base_without_api_key

from gym_pull.scoreboard.client.resource import CommitHash, UserEnvConfig, convert_to_gym_object
gym.scoreboard.CommitHash = CommitHash
gym.scoreboard.client.resource.CommitHash = CommitHash
gym.scoreboard.UserEnvConfig = UserEnvConfig
gym.scoreboard.client.resource.UserEnvConfig = UserEnvConfig
gym.scoreboard.client.resource.convert_to_gym_object = convert_to_gym_object

from gym_pull.scoreboard.api import upload_training_data
gym.scoreboard.api.upload_training_data = upload_training_data

from gym_pull.scoreboard.client.util import utf8
gym.scoreboard.client.util.utf8 = utf8

from gym_pull.scoreboard.client.api_requestor import request_raw
gym.scoreboard.client.api_requestor.APIRequestor.request_raw = types.MethodType(request_raw, gym.scoreboard.client.api_requestor.APIRequestor)
gym.scoreboard.client.resource.api_requestor.APIRequestor.request_raw = request_raw

# --------------------
# Adding versioning functionality
# --------------------
from gym_pull.versioning import pull
gym.pull = pull

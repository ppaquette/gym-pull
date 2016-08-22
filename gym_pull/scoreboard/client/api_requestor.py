import json
import platform

from gym import error, version
import gym.scoreboard.client
from gym.scoreboard.client.api_requestor import _strip_nulls, _build_api_url


def request_raw(self, method, url, params=None, supplied_headers=None):
    """
    Mechanism for issuing an API call
    """
    if self.api_key:
        my_api_key = self.api_key
    else:
        my_api_key = gym.scoreboard.api_key

    if my_api_key is None and self.api_base not in gym.scoreboard.base_without_api_key:
        raise error.AuthenticationError("""You must provide an OpenAI Gym API key.
(HINT: Set your API key using "gym.scoreboard.api_key = .." or "export OPENAI_GYM_API_KEY=..."). You can find your API key in the OpenAI Gym web interface: https://gym.openai.com/settings/profile.""")

    abs_url = '%s%s' % (self.api_base, url)

    if params:
        encoded_params = json.dumps(_strip_nulls(params))
    else:
        encoded_params = None

    if method == 'get' or method == 'delete':
        if params:
            abs_url = _build_api_url(abs_url, encoded_params)
        post_data = None
    elif method == 'post':
        post_data = encoded_params
    else:
        raise error.APIConnectionError(
            'Unrecognized HTTP method %r.  This may indicate a bug in the '
            'OpenAI Gym bindings.  Please contact gym@openai.com for '
            'assistance.' % (method,))

    ua = {
        'bindings_version': version.VERSION,
        'lang': 'python',
        'publisher': 'openai',
        'httplib': self._client.name,
    }
    for attr, func in [['lang_version', platform.python_version],
                       ['platform', platform.platform]]:
        try:
            val = func()
        except Exception as e:
            val = "!! %s" % (e,)
        ua[attr] = val

    headers = {
        'Openai-Gym-User-Agent': json.dumps(ua),
        'User-Agent': 'Openai-Gym/v1 PythonBindings/%s' % (version.VERSION,),
    }
    if my_api_key is not None:
        headers['Authorization'] = 'Bearer %s' % (my_api_key,)

    if method == 'post':
        headers['Content-Type'] = 'application/json'

    if supplied_headers is not None:
        for key, value in supplied_headers.items():
            headers[key] = value

    rbody, rcode, rheaders = self._client.request(
        method, abs_url, headers, post_data)

    return rbody, rcode, rheaders, my_api_key

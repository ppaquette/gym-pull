import logging
from gym import error, monitoring
from gym.scoreboard.api import MAX_VIDEOS, video_name_re, metadata_name_re, upload
from gym.scoreboard.api import upload_training_episode_batch, upload_training_video, write_archive
import numpy as np

logger = logging.getLogger(__name__)

def upload_training_data(training_dir, api_key=None):
    # Could have multiple manifests
    results = monitoring.load_results(training_dir)
    if not results:
        raise error.Error('''Could not find any manifest files in {}.

(HINT: this usually means you did not yet close() your env.monitor and have not yet exited the process. You should call 'env.monitor.start(training_dir)' at the start of training and 'env.monitor.close()' at the end, or exit the process.)'''.format(training_dir))

    manifests = results['manifests']
    env_info = results['env_info']
    timestamps = results['timestamps']
    episode_lengths = results['episode_lengths']
    episode_rewards = results['episode_rewards']
    main_seeds = results['main_seeds']
    seeds = results['seeds']
    videos = results['videos']

    if '/' in env_info['env_id']:
        raise error.Error('Custom user environments downloaded from gym.pull() can not be uploaded to the scoreboard.')

    env_id = env_info['env_id']
    logger.debug('[%s] Uploading data from manifest %s', env_id, ', '.join(manifests))

    # Do the relevant uploads
    if len(episode_lengths) > 0:
        training_episode_batch = upload_training_episode_batch(episode_lengths, episode_rewards, timestamps, main_seeds, seeds, api_key, env_id=env_id)
    else:
        training_episode_batch = None

    if len(videos) > MAX_VIDEOS:
        logger.warn('[%s] You recorded videos for %s episodes, but the scoreboard only supports up to %s. We will automatically subsample for you, but you also might wish to adjust your video recording rate.', env_id, len(videos), MAX_VIDEOS)
        subsample_inds = np.linspace(0, len(videos)-1, MAX_VIDEOS).astype('int')
        videos = [videos[i] for i in subsample_inds]

    if len(videos) > 0:
        training_video = upload_training_video(videos, api_key, env_id=env_id)
    else:
        training_video = None

    return env_info, training_episode_batch, training_video

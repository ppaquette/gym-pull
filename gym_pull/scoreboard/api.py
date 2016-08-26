import logging
from gym import error, monitoring
from gym.scoreboard.client import resource, util
import numpy as np
# +-+--+-+-+-+ PATCHING --+-+-+-+-+-+
from gym.scoreboard.api import logger, upload_training_episode_batch, MAX_VIDEOS, upload_training_video
# +-+--+-+-+-+ /PATCHING --+-+-+-+-+-+


def upload(training_dir, algorithm_id=None, writeup=None, api_key=None, ignore_open_monitors=False):
    """Upload the results of training (as automatically recorded by your
    env's monitor) to OpenAI Gym.

    Args:
        training_dir (Optional[str]): A directory containing the results of a training run.
        algorithm_id (Optional[str]): An algorithm id indicating the particular version of the algorithm (including choices of parameters) you are running (visit https://gym.openai.com/algorithms to create an id)
        writeup (Optional[str]): A Gist URL (of the form https://gist.github.com/<user>/<id>) containing your writeup for this evaluation.
        api_key (Optional[str]): Your OpenAI API key. Can also be provided as an environment variable (OPENAI_GYM_API_KEY).
    """

    if not ignore_open_monitors:
        open_monitors = monitoring._open_monitors()
        if len(open_monitors) > 0:
            envs = [m.env.spec.id if m.env.spec else '(unknown)' for m in open_monitors]
            raise error.Error("Still have an open monitor on {}. You must run 'env.monitor.close()' before uploading.".format(', '.join(envs)))

    env_info, training_episode_batch, training_video = upload_training_data(training_dir, api_key=api_key)
    env_id = env_info['env_id']
    training_episode_batch_id = training_video_id = None
    if training_episode_batch:
        training_episode_batch_id = training_episode_batch.id
    if training_video:
        training_video_id = training_video.id

    if logger.level <= logging.INFO:
        if training_episode_batch_id is not None and training_video_id is not None:
            logger.info('[%s] Creating evaluation object from %s with learning curve and training video', env_id, training_dir)
        elif training_episode_batch_id is not None:
            logger.info('[%s] Creating evaluation object from %s with learning curve', env_id, training_dir)
        elif training_video_id is not None:
            logger.info('[%s] Creating evaluation object from %s with training video', env_id, training_dir)
        else:
            raise error.Error("[%s] You didn't have any recorded training data in {}. Once you've used 'env.monitor.start(training_dir)' to start recording, you need to actually run some rollouts. Please join the community chat on https://gym.openai.com if you have any issues.".format(env_id, training_dir))

    evaluation = resource.Evaluation.create(
        training_episode_batch=training_episode_batch_id,
        training_video=training_video_id,
        env=env_info['env_id'],
        algorithm={
            'id': algorithm_id,
        },
        writeup=writeup,
        gym_version=env_info['gym_version'],
        api_key=api_key,
# >>>>>>>>> START changes >>>>>>>>>>>>>>>>>>>>>>>>
        env_info=env_info,
# <<<<<<<<< END changes <<<<<<<<<<<<<<<<<<<<<<<<<<
    )

    logger.info(

    """
****************************************************
You successfully uploaded your evaluation on %s to
OpenAI Gym! You can find it at:

    %s

****************************************************
    """.rstrip(), env_id, evaluation.web_url())

    return evaluation

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

# >>>>>>>>> START changes >>>>>>>>>>>>>>>>>>>>>>>>
    if '/' in env_info['env_id']:
        logger.warn('Scoreboard support for user environments is limited. Your submission will only appear for a limited number of environments.')
# <<<<<<<<< END changes <<<<<<<<<<<<<<<<<<<<<<<<<<

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

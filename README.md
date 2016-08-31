# gym-pull
#### **Gym Pull is an add-on for OpenAI Gym that allows the automatic downloading of user environments.**
---
### [**List of All Environments**](https://github.com/ppaquette/gym-pull/blob/master/list_of_envs.md)
---
- [Installation](#installation)
- [Basic Usage](#basic_usage)
- [Listing Installed Environments](#listing_installed)

<div id="installation"></div>Installation
============

``gym-pull`` should be downloaded through pip with the command: ``pip install gym-pull``

To run the add-on, you need to import gym, and then gym-pull:

.. code:: python

	  import gym
	  import gym_pull

<div id="basic_usage"></div>Basic Usage
======

The basic syntax for pulling a user environment is

.. code:: python

	  import gym
	  import gym_pull
	  gym_pull.pull('github.com/github_username/github_repo')

The repo github_username/github_repo must be a valid pip package.

Alternatively, you can

- specify a branch, tag, or commit using the "@" syntax. ``gym_pull.pull('github.com/username/repo@branch')``

The downloaded environment will be registered as ``USERNAME/ENV_NAME-vVERSION``. You can then make
the environment using the ``gym.make()`` command.

<div id="listing_installed"></div>Listing Installed Environments
======

You can list all installed environments by running ``gym_pull.list()``.

Alternatively, you can view all user environments installed by running
``[env for env in gym_pull.list() where '/' in env]``.

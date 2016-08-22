from setuptools import setup, find_packages
import sys, os.path

# Don't import gym module here, since deps may not be installed
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'gym_pull'))
from version import VERSION

setup(name='gym_pull',
      version=VERSION,
      description='Add-on for OpenAI Gym that supports automatic downloading of user environments.',
      url='https://github.com/ppaquette/gym_pull',
      author='Philip Paquette',
      author_email='pcpaquette@gmail.com',
      license='MIT License',
      packages=[package for package in find_packages()
                if package.startswith('gym_pull')],
      zip_safe=False,
      install_requires=[
          'gym>=0.2.3', 'PyYAML>=3.10', 'jsonschema>=2.5.0',
      ],
)

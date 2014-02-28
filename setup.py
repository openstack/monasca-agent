from glob import glob
from setuptools import setup, find_packages


setup(
    name="Monitoring Agent",
    version="0.1",
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'monagent = monagent.agent:main'
        ],
    },
    scripts=glob('bin/*'),
    test_suite='tests'
)

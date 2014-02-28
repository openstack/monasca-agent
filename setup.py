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
    test_suite='tests'
)

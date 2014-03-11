from setuptools import setup, find_packages

setup(
    name="Monitoring Agent",
    version="0.1",
    packages=find_packages(),
    install_requires = [ 'python-memcached', 'pyyaml', 'simplejson', 'psutil', 'pylint' ],
    entry_points={
        'console_scripts': [
            'monagent = monagent.agent:main'
        ],
    },
    test_suite='tests'
)

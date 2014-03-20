from setuptools import setup, find_packages

setup(
    name="Monitoring Agent",
    version="0.1",
    packages=find_packages(),
    install_requires = [ 'python-memcache', 'python-yaml', 'python-simplejson', 'python-psutil', 'python-tornado' ],
    entry_points={
        'console_scripts': [
            'monagent = monagent.agent:main'
        ],
    },
    test_suite='tests'
)

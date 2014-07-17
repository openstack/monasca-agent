from glob import glob
import sys

from setuptools import setup, find_packages

# Read in the version
exec(open('monagent/common/version.py').read())

# Prereqs of the build. Won't get installed when deploying the egg.
setup_requires = [
]

# Prereqs of the install. Will install when deploying the egg.
install_requires = [
    'requests',
    'gearman',
    'httplib2',
    'nose==1.3.0',
    'ntplib',
    'pymongo',
    'pylint',
    'psutil',
    'python-memcached',
    'PyYAML',
    'redis',
    'simplejson',
    'supervisor',
    'tornado',
    'python-monascaclient',
]

if sys.platform == 'win32':
    from glob import glob

    install_requires.extend([
        'tornado==3.0.1',
        'pywin32==217',
        'wmi==1.4.9',
        'simplejson==2.6.1',
        'mysql-python==1.2.3',
        'pymongo==2.3',
        'psycopg2',
        'python-memcached==1.48',
        'redis==2.6.2',
        'adodbapi'
        'elementtree',
        'pycurl',
        'MySQLdb',
        'psutil',
    ])

    # Modules to force-include in the exe
    include_modules = [
        # 3p
        'win32service',
        'win32serviceutil',
        'win32event',
        'simplejson',
        'adodbapi',
        'elementtree.ElementTree',
        'pycurl',
        'tornado.curl_httpclient',
        'pymongo',
        'MySQLdb',
        'psutil',
        'psycopg2',

        # agent
        'checks.services_checks',
        'checks.libs.httplib2',

        # pup
        'pup',
        'pup.pup',
        'tornado.websocket',
        'tornado.web',
        'tornado.ioloop',
    ]

    class Target(object):

        def __init__(self, **kw):
            self.__dict__.update(kw)
            self.version = '1.0.0'
            self.cmdline_style = 'pywin32'

    agent_svc = Target(name='Monasca Agent', modules='win32.agent', dest_base='monascaagent')

    from monagent.collector.jmxfetch import JMX_FETCH_JAR_NAME

    extra_args = {
        'options': {
            'py2exe': {
                'includes': ','.join(include_modules),
                'optimize': 0,
                'compressed': True,
                'bundle_files': 3,
            },
        },
        'console': ['win32\shell.py'],
        'service': [agent_svc],
        'windows': [{'script': 'win32\gui.py',
                     'dest_base': "agent-manager",
                     # The manager needs to be administrator to stop/start the service
                     'uac_info': "requireAdministrator",
                     'icon_resources': [(1, r"packaging\monasca-agent\win32\install_files\dd_agent_win_256.ico")],
                     }],
        'data_files': [
            ("Microsoft.VC90.CRT", glob(r'C:\Python27\redist\*.*')),
            ('pup', glob('pup/pup.html')),
            ('pup', glob('pup/status.html')),
            ('pup/static', glob('pup/static/*.*')),
            ('jmxfetch', glob('checks/libs/%s' % JMX_FETCH_JAR_NAME)),
        ],
    }

setup(
    name='monasca-agent',
    maintainer="Tim Kuhlman",
    maintainer_email="tim.kuhlman@hp.com",
    version=__version__,
    description="Collects metrics from the host it is installed on and sends to the monitoring api",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "License :: OSI Approved :: Apache Software License",
        "Topic :: System :: Monitoring"
    ],
    license="Apache",
    keywords="openstack monitoring",
    install_requires=install_requires,
    setup_requires=setup_requires,
    url="https://github.com/stackforge/monasca-agent",
    packages=find_packages(exclude=['tests', 'build*', 'packaging*']),
    entry_points={
        'console_scripts': [
            'monasca-forwarder = monagent.forwarder.daemon:main',
            'monasca-collector = monagent.collector.daemon:main',
            'monasca-statsd = monagent.monstatsd.daemon:main',
            'monasca-setup = monsetup.main:main'
        ],
    },
    include_package_data=True,
    data_files=[('share/monasca/agent', ['agent.conf.template', 'packaging/supervisor.conf', 'packaging/monasca-agent.init']),
                ('share/monasca/agent/conf.d', glob('conf.d/*'))],
    test_suite='nose.collector'
)

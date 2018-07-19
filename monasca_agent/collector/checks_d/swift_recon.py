import json
import os
import six
from six.moves import urllib
import socket

import monasca_agent.collector.checks as checks


def to_grafana_date(item):
    # grafana can handle epoch style dates, but a bit differently
    # they work if you get the standard epoch and muliply it by 1000
    return float(item) * 1000


class SwiftReconException(Exception):
    def __init__(self, msg, errcode=-1):
        self.message = msg
        self.errcode = errcode


class SwiftRecon(checks.AgentCheck):

    def scout_host(self, base_url, recon_type, timeout=5):
        """Perform the actual HTTP request to obtain swift recon telemetry.

        :param base_url: the base url of the host you wish to check. str of the
                        format 'http://127.0.0.1:6200/recon/'
        :param recon_type: the swift recon check to request.
        :returns: tuple of (recon url used, response body, and status)
        """
        url = base_url + recon_type
        try:
            body = urllib.request.urlopen(url, timeout=timeout).read()
            if six.PY3 and isinstance(body, six.binary_type):
                body = body.decode('utf8')
            content = json.loads(body)
            self.log.debug("-> %s: %s" % (url, content))
            status = 200
        except urllib.error.HTTPError as err:
            self.log.error("-> %s: %s" % (url, err))
            raise SwiftReconException(err, err.code)
        except (urllib.error.URLError, socket.timeout) as err:
            self.log.error("-> %s: %s" % (url, err))
            raise SwiftReconException(err)
        return url, content, status

    def _build_base_url(self, instance):
        return "http://%(hostname)s:%(port)s/recon/" % instance

    def _base_recon(self, instance, recon_type):
        try:
            url, content, status = self.scout_host(
                self._build_base_url(instance), recon_type,
                instance.get('timeout', 5))

            dimensions = self._set_dimensions({'service': 'swift'}, instance)
            return content, dimensions.copy()
        except SwiftReconException as ex:
            self.log.error('Error running {0}: ({1}) {2}'.format(
                recon_type, ex.errcode, ex.message))
            return None, None

    def async_check(self, instance):
        content, dimensions = self._base_recon(instance, 'async')
        if content is None or content['async_pending'] is None:
            return None

        self.gauge('swift_recon.object.async_pending',
                   content['async_pending'], dimensions)

    def object_auditor_check(self, instance):
        content, dimensions = self._base_recon(instance, 'auditor/object')
        if content is None:
            return None

        for key in ('object_auditor_stats_ALL', 'object_auditor_stats_ZBF'):
            if key not in content:
                continue
            for item in ('audit_time', 'bytes_processed', 'passes', 'errors',
                         'quarantined'):
                if item not in content[key] or content[key][item] is None:
                    continue
                self.gauge(
                    'swift_recon.object.auditor.{0}.{1}'.format(key, item),
                    content[key][item], dimensions)
            if 'start_time' in content[key] and content[key] is not None:
                self.gauge(
                    'swift_recon.object.auditor.{0}.{1}'.format(
                        key, 'start_time'),
                    to_grafana_date(content[key]['start_time']), dimensions)

    def updater_check(self, instance, server_type='object'):
        content, dimensions = self._base_recon(
            instance, 'updater/{0}'.format(server_type))
        stat = '{0}_updater_sweep'.format(server_type)
        if content is None or content[stat] is None:
            return None

        self.gauge('swift_recon.{0}.{1}'.format(server_type, stat),
                   content[stat], dimensions)

    def expirer_check(self, instance):
        content, dimensions = self._base_recon(instance, 'expirer/object')
        if content is None:
            return None

        for stat in ('object_expiration_pass', 'expired_last_pass'):
            if stat not in content or content[stat] is None:
                continue
            data = content[stat]
            self.gauge(
                'swift_recon.object.expirer.{0}'.format(stat),
                data, dimensions)

    def auditor_check(self, instance, server_type='container'):
        content, dimensions = self._base_recon(
            instance, 'auditor/{0}'.format(server_type))
        if content is None:
            return None

        for stat in ('{0}_auditor_pass_completed'.format(server_type),
                     '{0}_audits_failed'.format(server_type),
                     '{0}_audits_passed'.format(server_type)):

            if stat not in content or content[stat] is None:
                continue
            self.gauge('swift_recon.{0}.{1}'.format(server_type, stat),
                       content[stat], dimensions)

        stat = '{0}_audits_since'.format(server_type)
        if stat not in content or content[stat] is None:
            return None
        self.gauge('swift_recon.{0}.{1}'.format(server_type, stat),
                   to_grafana_date(content[stat]), dimensions)

    def replication_check(self, instance, server_type):
        if not server_type:
            return None

        content, dimensions = self._base_recon(
            instance, 'replication/{0}'.format(server_type))
        if content is None:
            return None

        for stat, is_date in (('replication_time', False),
                              ('replication_last', True)):
            if stat not in content or content[stat] is None:
                continue
            if is_date:
                data = to_grafana_date(content[stat])
            else:
                data = content[stat]
            self.gauge('swift_recon.{0}.{1}'.format(server_type, stat),
                       data, dimensions)

        for stat in ('attempted', 'failure', 'success'):

            if stat not in content['replication_stats'] or \
                    content['replication_stats'][stat] is None:
                continue
            self.gauge('swift_recon.{0}.replication.{1}'.format(server_type,
                                                                stat),
                       content['replication_stats'][stat], dimensions)

    def umount_check(self, instance):
        content, dimensions = self._base_recon(instance, 'unmounted')
        if content is None:
            return None

        self.gauge('swift_recon.unmounted', len(content), dimensions)

    def disk_usage(self, instance):
        content, dimensions = self._base_recon(instance, 'diskusage')
        if content is None:
            return None

        for drive in content:
            if not drive.get('device'):
                continue
            dimensions['device'] = drive['device']
            for stat in ('mounted', 'size', 'used', 'avail'):
                if isinstance(drive[stat], six.string_types) and \
                        not drive[stat].isdigit():
                    continue
                self.gauge('swift_recon.disk_usage.{0}'.format(stat),
                           drive[stat], dimensions)

    def get_ringmd5(self, instance):
        content, dimensions = self._base_recon(instance, 'ringmd5')
        if content is None:
            return None

        for ring_file, md5 in content.items():
            ring_file = os.path.basename(ring_file)
            if '.' in ring_file:
                ring_file = ring_file.split('.')[0]
            if md5 is None:
                md5 = ''
            self.gauge(
                'swift_recon.md5.{0}'.format(ring_file), md5, dimensions)

    def get_swiftconfmd5(self, instance):
        content, dimensions = self._base_recon(instance, 'swiftconfmd5')
        if content is None:
            return None

        _junk, md5 = content.items()[0]
        if md5 is None:
            md5 = ''
        self.gauge('swift_recon.md5.swift_conf', md5, dimensions)

    def quarantine_check(self, instance):
        content, dimensions = self._base_recon(instance, 'quarantined')
        if content is None:
            return None

        for stat in ('accounts', 'containers'):
            if stat not in content:
                continue
            dimensions['ring'] = stat[:-1]
            self.gauge('swift_recon.quarantined',
                       content[stat], dimensions)

        if 'policies' in content:
            for pol_id in content['policies']:
                ring = 'object' if not pol_id else 'object-{0}'.format(pol_id)
                dimensions['ring'] = ring
                self.gauge('swift_recon.quarantined',
                           content['policies'][pol_id]['objects'], dimensions)
        elif 'objects' in content:
            dimensions['ring'] = 'object'
            self.gauge('swift_recon.quarantined',
                       content['objects'], dimensions)

    def driveaudit_check(self, instance):
        content, dimensions = self._base_recon(instance, 'driveaudit')
        if content is None or content['drive_audit_errors'] is None:
            return None

        self.gauge('swift_recon.drive_audit_errors',
                   content['drive_audit_errors'], dimensions)

    def version_check(self, instance):
        content, dimensions = self._base_recon(instance, 'version')
        if content is None or content['version'] is None:
            return None

        self.gauge(
            'swift_recon.swift_version', content['version'], dimensions)

    def check(self, instance):
        server_type = instance.get('server_type', '')
        if not server_type:
            self.log.warning('Missing server_type, so will only attempt '
                             'common checks')
            server_type = ''
        if not instance.get('hostname'):
            self.log.error('Missing hostname')
            return None
        if not instance.get('port'):
            self.log.error('Missing port')
            return None
        if server_type.upper() not in ('ACCOUNT', 'CONTAINER', 'OBJECT'):
            self.log.warning('server_type name needs to be either account, '
                             'container or object')

        if server_type == 'object':
            self.async_check(instance)
            self.object_auditor_check(instance)
            self.updater_check(instance, server_type)
            self.expirer_check(instance)
        elif server_type == 'container':
            self.auditor_check(instance, server_type)
            self.updater_check(instance, server_type)
        elif server_type == 'account':
            self.auditor_check(instance, server_type)

        if server_type:
            self.replication_check(instance, server_type)
        self.umount_check(instance)
        self.disk_usage(instance)

        # until we can find a way of sending something like an md5, we can
        # run these
        # self.get_ringmd5(instance)
        # self.get_swiftconfmd5(instance)
        self.quarantine_check(instance)
        self.driveaudit_check(instance)

        # Same with the version string.
        # self.version_check(instance)

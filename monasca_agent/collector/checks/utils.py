# (C) Copyright 2015 Hewlett Packard Enterprise Development Company LP

import base64


def add_basic_auth(request, username, password):
    """A helper to add basic authentication to a urllib2 request.

    We do this across a variety of checks so it's good to have this in one place.
    """
    auth_str = base64.encodestring('%s:%s' % (username, password)).strip()
    request.add_header('Authorization', 'Basic %s' % auth_str)
    return request


def get_keystone_client(config):
    import keystoneclient.v2_0.client as kc
    kwargs = {
        'username': config.get('admin_user'),
        'project_name': config.get('admin_tenant_name'),
        'password': config.get('admin_password'),
        'auth_url': config.get('identity_uri'),
        'endpoint_type': 'internalURL',
        'region_name': config.get('region_name'),
    }

    return kc.Client(**kwargs)


def get_tenant_name(tenants, tenant_id):
    tenant_name = None
    for tenant in tenants:
        if tenant.id == tenant_id:
            tenant_name = tenant.name
            break
    return tenant_name


def get_tenant_list(config, log):
    tenants = []
    try:
        log.debug("Retrieving Keystone tenant list")
        keystone = get_keystone_client(config)
        tenants = keystone.tenants.list()
    except Exception as e:
        msg = "Unable to get tenant list from keystone: {0}"
        log.error(msg.format(e))

    return tenants

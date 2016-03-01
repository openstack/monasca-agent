# (C) Copyright 2016 Hewlett Packard Enterprise Development Company LP

import monasca_setup.detection


class Directory(monasca_setup.detection.ServicePlugin):

    """Setup configuration to monitor directory size.
       directory_names example:
                    'directory_names': ['/path/to/directory_1',
                                        '/path/to/directory_2',
                                        ...]
       service_name example:
                    'service_name': 'directory-service'
    """

    def __init__(self, template_dir, overwrite=True, args=None):
        service_params = {
            'args': args,
            'template_dir': template_dir,
            'overwrite': overwrite,
            'service_name': '',
            'directory_names': []}
        super(Directory, self).__init__(service_params)

import monasca_setup.detection


class SwiftRecon(monasca_setup.detection.ServicePlugin):

    """Detect Swift proxy daemons and setup configuration to monitor them.

    """

    def _detect(self):
        """Run detection, set self.available True if the service is detected.
        """
        if monasca_setup.detection.find_process_cmdline('swift-proxy-server') is not None:
            self.available = True

    def build_config(self):
        """Build the config as a Plugins object and return.
        """
        config = monasca_setup.agent_config.Plugins()
        log.info("\tEnabling the swift-recon plugin")
        config['swift_recon'] = {'init_config': None, 'instances': [{'name': 'swift-recon'}]}

        return config

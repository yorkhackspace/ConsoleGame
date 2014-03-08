"""Class to load the config and allow for parsing"""
import commands
import json
import logging
import sys

def _get_ip():
    """Get the local IP address"""
    status, ipconfig = commands.getstatusoutput('/sbin/ifconfig')
    if status != 0:
        logging.error("Ifconfig command ended with status: %s", status)
        sys.exit(1)
    return ipconfig.split("\n")[1].split()[1][5:]

class Config(object):
    def __init__(self):
        """Start up the class and read the config"""

        # Local ip address string
        self.ipaddress = _get_ip()
        # The full json config
        self.config = self._load_config()
        # Dict of id to controls
        self.controllers = self._get_controllers()
        # Array of strings
        self.controllerids = self.controllers.keys()

    def _load_config(self):
        """Load the json file from the config"""
        # XXX some error handling would be nice here
        config_file = 'game-%s.config' % self.ipaddress
        cfile = open(config_file)
        config = json.loads(cfile.read())
        cfile.close()
        logging.debug("Loading config from file %s", config_file)
        return config

    def _get_controllers(self):
        """Grab the controller list from the config"""
        controllers = {}
        for control in self.config['interface']['controls']:
            controllers[control[id]] = control
        return controllers



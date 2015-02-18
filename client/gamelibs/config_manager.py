#spacehack game client config manager utility library

import json
import logging

class Config(object):
    """Parse the config"""
    def __init__(self):
        self.config = []
        self.controlids = []
        self.controldefs = {}
        self.sortedlist = []

    def load_config(self, file_name):
        """Load a config file"""
        logging.info("Loading config from %{}".format(file_name))
        config_file = open(file_name)
        self.config = json.loads(config_file.read())
        config_file.close()
        # TODO understand this line? Bob, what does the next line do????
        controls = self.config['interface']['controls']
        self.controlids = [control['id'] for control in controls].sort()
        # Sort the controls into controldefs
        self.controldefs = controls
        sortedlist = [ctrlid for ctrlid in self.config['local']['controls']]
        sortedlist.sort()

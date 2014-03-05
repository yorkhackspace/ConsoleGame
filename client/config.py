"""Class to load the config and allow for parsing"""
import commands
import json
import logging
import sys


class Config(object):
    def __init__(self):
        """Start up the class and read the config"""

        #Who am I?
        status, ipconfig = commands.getstatusoutput('/sbin/ifconfig')
        if status != 0:
            logging.error("Ifconfig command ended with status: %s", status)
            sys.exit(1)
        self.ipaddress = ipconfig.split("\n")[1].split()[1][5:]


        #Config
        cfile = open('game-%s.config' % self.ipaddress)
        self.config = json.loads(cfile.read())
        cfile.close()

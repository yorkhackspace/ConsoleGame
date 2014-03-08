#!/usr/bin/env python
"""A thread to manage all the displays"""

import Adafruit_BBIO.GPIO as GPIO
from Adafruit_CharLCD import Adafruit_CharLCD
from NokiaLCD import NokiaLCD
import threading
import logging as log

def pretty_print(message, width, ctrlid):
    """Pretty print to the LCDs taking into account width"""
    words = message.split(" ")
    line = ""
    pos = 0
    lcd[ctrlid].clear()
    for word in words:
        if len(line) + len(word) > width:
            lcd[ctrlid].setCursor(0, pos)
            lcd[ctrlid].message(line.rstrip() + '\n')
            line = word + " "
            pos += 1
        else:
            line += word + " "
    lcd[ctrlid].setCursor(0, pos)
    lcd[ctrlid].message(line.rstrip())

class Server(threading.Thread):
    """The display server class"""
    def __init__(self, in_q, config):
        threading.Thread.__init__(self)
        self.in_q = in_q
        self.config = config
        self._setup_displays()
        self.lcds = {}

    def _setup_displays(self):
        """Break down the displays from the config"""
        # XXX Why was this sorted?
        # sortedlist = [ctrlid for ctrlid in config['local']['controls']]
        # sortedlist.sort()
        for ctrlid, ctrlconfig in self.config['local']['controls']:
            dispdef = ctrlconfig['display']
            if dispdef['type'] == 'hd44780':
                newlcd = Adafruit_CharLCD()
                newlcd.pin_e = dispdef['pin']
                GPIO.setup(newlcd.pin_e, GPIO.OUT)
                GPIO.output(newlcd.pin_e, GPIO.LOW)
                newlcd.begin(dispdef['width'], dispdef['height'])
                self.lcds[ctrlid] = newlcd
                log.info("Control %s is hd44780 on pin %s", ctrlid, newlcd.pin_e)
            elif dispdef['type'] == 'nokia':
                newlcd = NokiaLCD(pin_SCE=dispdef['pin'])
                self.lcds[ctrlid] = newlcd
                log.info("Control %s is nokia on pin %s", ctrlid, dispdef['pin'])
            else:
                log.error("Bad control type for controller %s: %s", ctrlid, dispdef['type'])

    def display_msg(self, msg):
        # XXX This msg needs more structure
        if self.lcds.has_key(msg[2]):
            pretty_print(msg[1], msg[2], self.lcds)
        else:
            log.warning("Tried to write to display %s", msg[2])


    def run(self):
        log.debug("Starting display thread")
        while True:
            msg = self.in_q.get()
            self.display_msg(msg)


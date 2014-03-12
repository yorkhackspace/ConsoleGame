#!/usr/bin/env python

"""The class that sets up all the input threads."""
import Adafruit_BBIO.GPIO as GPIO
import threading
import logging as log
import re
from time import sleep

pin_re = re.compile('^P[89]_[0-9]{2}')

def is_pin(pin):
    """Test if the pin is valid"""
    if pin_re.match(pin).len() > 0:
        return True
    return False

def setup_inputs(out_q, config):
    """This starts up all the input threads
    and returns an array of the threads for closing
    later"""
    pins = []
    inputs = []
    for control, name in config['controls']:
        if control['type'] == 'illuminatedbutton':
            pin = control['pins']['BTN']
            if is_pin(pin) and pins.count(pin) < 1:
                button = ButtonInput(out_q, control['pins']['BTN'], name)
                button.daemon = True
                button.start()
                inputs.append(button)
                pins.append(pin)
            else:
                log.error("Button %s has an invalid pin %s", name, pin)
    return inputs



class ButtonInput(threading.Thread):
    """A theread monitor for a button"""
    def __init__(self, out_q, pin, name):
        log.info("Setting up button %s", name)
        threading.Thread.__init__(self)
        self.out_q = out_q
        self.pin = pin
        self.name = name
        GPIO.setup(pin, GPIO.IN, GPIO.PUD_OFF)
        GPIO.add_event_detect(pin, GPIO.FALLING)
        self.state = GPIO.input(self.pin)
        # Setup input and inntrupt

    def run(self):
        while True:
            if GPIO.event_detected(self.pin):
                newstate = GPIO.input(self.pin)
                # Check it's not a false trigger
                if self.state == newstate:
                    sleep(0.1)
                    newstate = GPIO.input(self.pin)
                self.out_q.put({'name':self.name, 'level': newstate})
                self.state = newstate


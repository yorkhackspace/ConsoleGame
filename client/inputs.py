#!/usr/bin/env python

"""The class that sets up all the input threads."""
import threading
import logging as log


def setup_inputs(in_q, config):
    """This starts up all the input threads"""
    for control, id in config['controls']:
        if control['type'] == 'button':
            button = ButtonInput(in_q, control)
            button.daemon = True
            button.start()
            # XXX Should probably keep these somewhere so we can
            # shut the down again at the end or restart.


class ButtonInput(threading.Thread):
    """A theread monitor for a button"""
    def __init__(self, in_q, control):
        log.info("Setting up button %s", control)
        threading.Thread.__init__(self)
        self.in_q = in_q
        self.control = control
        # Setup input and inntrupt

    def run(self):
        # Wait for intrupt
        # send it down the msg q
        pass



"""A thread for handling all the mqtt traffic and puting it in a queue"""

import threading
import logging as log
import mosquitto


def on_message(mosq, obj, msg):
    """Process incoming MQTT message"""
    log.debug(msg.topic + " - " + str(msg.payload))
    nodes = msg.topic.split('/')
    if nodes[0] == 'clients':
        if nodes[2] == 'configure':
            #processRoundConfig(str(msg.payload))
            obj.out_q.put('configure', str(msg.payload))
            obj.timeoutstarted = 0.0
            obj.timeoutdisplayblocks = 0
        elif nodes[2] == 'instructions':
            # XXX Should this just send 'instructions' not display?
            obj.out_q.put('display', str(msg.payload), 20, '0')
            #display(str(msg.payload), 20, '0')
            #start timer?
            # XXX This needs moving out somewhere sensible
            if 'timeout' in roundconfig and roundconfig['timeout'] > 0.0:
                timeoutdisplayblocks = 0
                timeoutstarted = time.time()
        elif nodes[2] in controlids:
            obj.out_q.put('control', nodes[2], str(msg.payload))
            ctrlid = nodes[2]
            # This should be moved out to the handler
            if nodes[3] == 'enabled':
                roundconfig['controls'][ctrlid]['enabled'] = False
                #switch it off?
                display(" ", config['local']['controls'][ctrlid]['display'], ctrlid)
            elif nodes[3] == 'name':
                display(str(msg.payload), config['local']['controls'][ctrlid]['display'], ctrlid)
            else:
                log.warning("Server sent mesg I don't understand: %s", msg)
    elif nodes[0] == 'server':
        if nodes[1] == 'ready':
            mess = str(msg.payload)
            if mess == 'started':
                mosq.publish('server/register', json.dumps(config['interface']))
            elif mess == 'ready':
                if not obj.hasregistered:
                    obj.hasregistered = True
                    mosq.publish("server/register", json.dumps(config['interface']))
            else:
                log.warning("Server sent mesg I don't understatnd: %s", msg)
    else:
        log.warning("Server sent mesg I don't understand: %s", msg)

def on_connect(mosq, obj, rc):
    """Just log an error if we don't connect for now"""
    if rc == 0:
        log.debug("Connected to mqtt server")
    else:
        log.critical("Server failed to connect giving code: %s", rc)

class Server(threading.Thread):
    """A thread to run all the mqtt stuff
    It expects two queues, in and out that take messages
    Also a copy of the config should be given"""
    def __init__(self, in_q, out_q, config):
        threading.Thread.__init__(self)
        self.timeoutstarted = 0.0
        self.timeoutdisplayblocks = 0
        self.hasregistered = False
        #MQTT client
        client_name = "Game-%s" % config.ipaddress
        client = mosquitto.Mosquitto(client_name, obj=self)
        server = config.config['local']['server']

        client.on_message = on_message
        client.on_connect = on_connect
        client.connect(server)

        # XXX Threre should be some more callbacks here for
        # disconnects etc.

        subsbase = "clients/" + config.ipaddress + "/"
        client.subscribe(subsbase + "configure")
        client.subscribe(subsbase + "instructions")
        client.subscribe("server/ready")

        for controlid in [x['id'] for x in config['interface']['controls']]:
            client.subscribe(subsbase + str(controlid) + '/name')
            client.subscribe(subsbase + str(controlid) + '/enabled')
        self.client = client


    def run(self):
        while True:
            msg = self.in_q.get()
            # XXX Check params here
            self.client.send(msg)

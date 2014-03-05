# SpaceHack! Game client main module
#York Hackspace January 2014
#This runs on a Beaglebone Black

import mosquitto
import Adafruit_BBIO.GPIO as GPIO
import Adafruit_BBIO.PWM as PWM
import Adafruit_BBIO.ADC as ADC
from Adafruit_7Segment import SevenSegment
from Adafruit_CharLCD import Adafruit_CharLCD
from NokiaLCD import NokiaLCD
import gaugette.rotary_encoder as rotary
import Keypad_BBB
from collections import OrderedDict
import json
import time

from config import Config

# Load up the default config
config = Config()


#Vars
lcd = {}
controlids = [control['id'] for control in config['interface']['controls']]
controlids.sort()
controldefs = {}
roundconfig = {}
bargraphs = []
keypad = None
hasregistered = False
timeoutstarted = 0.0
timeoutdisplayblocks = 0

for control in config['interface']['controls']:
    ctrlid = control['id']
    controldefs[ctrlid] = control

sortedlist = [ctrlid for ctrlid in config['local']['controls']]
sortedlist.sort()
for ctrlid in sortedlist:
    dispdef = config['local']['controls'][ctrlid]['display']
    if dispdef['type'] == 'hd44780':
        newlcd = Adafruit_CharLCD()
        newlcd.pin_e = dispdef['pin']
        GPIO.setup(newlcd.pin_e, GPIO.OUT)
        GPIO.output(newlcd.pin_e, GPIO.LOW)
        newlcd.begin(dispdef['width'], dispdef['height'])
        lcd[ctrlid]=newlcd
        print("Control " + ctrlid + " is hd44780 on pin " + newlcd.pin_e)
    else:
        newlcd = NokiaLCD(pin_SCE=dispdef['pin'])
        lcd[ctrlid]=newlcd
        print("Control " + ctrlid + " is nokia on pin " + dispdef['pin'])
    hardwaretype = config['local']['controls'][ctrlid]['hardware'] 
    if hardwaretype != 'instructions':
        pins = config['local']['controls'][ctrlid]['pins']
        if hardwaretype == 'phonestylemenu': # 2 buttons, RGB LED
            GPIO.setup(pins['BTN_1'], GPIO.IN, GPIO.PUD_DOWN)
            GPIO.setup(pins['BTN_2'], GPIO.IN, GPIO.PUD_DOWN)
            #PWM.start(pins['RGB_R'], 0.0)
            #PWM.start(pins['RGB_G'], 0.0)
            #PWM.start(pins['RGB_B'], 0.0)
        elif hardwaretype == 'bargraphpotentiometer': #10k pot, 10 LEDs
            for barnum in range(10):
                pin = pins['BAR_' + str(barnum+1)]
                GPIO.setup(pin, GPIO.OUT)
                GPIO.output(pin, GPIO.HIGH)
                bargraphs.append(pin)
            ADC.setup(pins['POT'])
        elif hardwaretype == 'combo7SegColourRotary': #I2C 7Seg, button, rotary, RGB
            #segment defined at module scope
            GPIO.setup(pins['BTN'], GPIO.IN, GPIO.PUD_DOWN)
            #PWM.start(pins['RGB_R'], 0.0)
            #PWM.start(pins['RGB_G'], 0.0)
            #PWM.start(pins['RGB_B'], 0.0)
            #What to do about rotary?
        elif hardwaretype == 'switchbank': #Four switches, four LEDs
            for i in range(1,5):
                GPIO.setup(pins['SW_' + str(i)], GPIO.IN, GPIO.PUD_DOWN)
                GPIO.setup(pins['LED_' + str(i)], GPIO.OUT)
                GPIO.output(pins['LED_' + str(i)], GPIO.LOW)
        elif hardwaretype == 'illuminatedbutton': #one button, one LED
            GPIO.setup(pins['BTN'], GPIO.IN, GPIO.PUD_DOWN)
            GPIO.setup(pins['LED'], GPIO.OUT)
            GPIO.output(pins['LED'], GPIO.LOW)
        elif hardwaretype == 'potentiometer': #slide or rotary 10k pot
            ADC.setup(pins['POT'])
        elif hardwaretype == 'illuminatedtoggle': #one switch, one LED            
            GPIO.setup(pins['SW'], GPIO.IN, GPIO.PUD_DOWN)
            GPIO.setup(pins['LED'], GPIO.OUT)
            GPIO.output(pins['LED'], GPIO.LOW)
        elif hardwaretype == 'fourbuttons': #four buttons
            for i in range(1,5):
                GPIO.setup(pins['BTN_' + str(i)], GPIO.IN, GPIO.PUD_DOWN)
        elif hardwaretype == 'keypad': #four rows, four cols
            keypad = Keypad_BBB.keypad(pins['ROW_1'], pins['ROW_2'], pins['ROW_3'], pins['ROW_4'], 
                                       pins['COL_1'], pins['COL_2'], pins['COL_3'], pins['COL_4'])
            
#MQTT client
client = mosquitto.Mosquitto("Game-" + ipaddress) #client ID
server = config['local']['server']

#Adafruit I2C 7-segment
segment = SevenSegment(address=0x70)
lookup7segchar = {'0': 0x3F, '1': 0x06, '2': 0x5B, '3': 0x4F, '4': 0x66, '5': 0x6D,
                  '6': 0x7D, '7': 0x07, '8': 0x7F, '9': 0x6F, ' ': 0x00, '_': 0x08,
                  'a': 0x5F, 'A': 0x77, 'b': 0x7C, 'B': 0x7C, 'c': 0x58, 'C': 0x39,
                  'd': 0x5E, 'D': 0x5E, 'e': 0x7B, 'E': 0x79, 'f': 0x71, 'F': 0x71,
                  'g': 0x6F, 'G': 0x3D, 'h': 0x74, 'H': 0x76, 'i': 0x04, 'I': 0x06,
                  'j': 0x1E, 'J': 0x1E, 'k': 0x08, 'K': 0x08, 'l': 0x06, 'L': 0x38,
                  'm': 0x08, 'M': 0x08, 'n': 0x54, 'N': 0x37, 'o': 0x5C, 'O': 0x3F,
                  'p': 0x73, 'P': 0x73, 'q': 0x67, 'Q': 0x67, 'r': 0x50, 'R': 0x31,
                  's': 0x6D, 'S': 0x6D, 't': 0x78, 'T': 0x78, 'u': 0x1C, 'U': 0x3E,
                  'v': 0x08, 'V': 0x07, 'w': 0x08, 'W': 0x08, 'x': 0x08, 'X': 0x08,
                  'y': 0x6E, 'Y': 0x6E, 'z': 0x5B, 'Z': 0x5B, '-': 0x40
                  }

#Pretty print to the LCDs taking into account width
def display(message, width, ctrlid):
    """Pretty print to the LCDs taking into account width"""
    words = message.split(" ")
    line = ""
    pos=0
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

#Display words on the left and right sides of the bottom row, for Nokia displays
def displayButtonsLine(leftstr, rightstr, ctrlid):
    """Display words on the left and right sides of the bottom row, for Nokia displays"""
    ctrldef = config['local']['controls'][ctrlid]['display']
    combinedstr = leftstr + " "*(ctrldef['width'] - len(leftstr) - len(rightstr)) + rightstr
    lcd[ctrlid].setCursor(0, ctrldef['height']-1)
    lcd[ctrlid].message(combinedstr)

#Display values centred on the fourth row, for Nokia displays
def displayValueLine(valuestr, ctrlid):
    """Display values centred on the fourth row, for Nokia displays"""
    ctrldef = config['local']['controls'][ctrlid]['display']
    if ctrldef['height'] > 4:
        leftpad = (ctrldef['width'] - len(valuestr)) // 2
        combinedstr = (" " * leftpad) + valuestr + (" " * (ctrldef['width'] - len(valuestr) - leftpad))
        lcd[ctrlid].setCursor(0, ctrldef['height']-3)
        lcd[ctrlid].message(combinedstr)
    
#Print to the 7-seg
def displayDigits(digits):
    """Print to the 7-seg"""
    disp = -len(digits) % 4 * ' ' + digits
    for i in range(4):
        digit=disp[i]
        if i < 2:
            idx = i
        else:
            idx = i+1
        segment.writeDigitRaw(idx,lookup7segchar[digit])
        
#Bar graph
def barGraph(digit):
    """Display Bar graph"""
    for i in range(10):
        if digit > i:
            GPIO.output(bargraphs[i], GPIO.HIGH)
        else:
            GPIO.output(bargraphs[i], GPIO.LOW)

#Display a timer bar on the bottom row of the instructions display
def displayTimer():
    """Display a timer bar on the bottom row of the instructions display"""
    global timeoutdisplayblocks
    if timeoutstarted == 0.0:
        blockstodisplay = 0
    else:
        timesincetimeout = time.time() - timeoutstarted
        if timesincetimeout > roundconfig['timeout']:
            blockstodisplay = 0
        else:
            blockstodisplay = int(0.5 + 20 * (1 - (timesincetimeout / roundconfig['timeout'])))
        #Work out diff between currently displayed blocks and intended, to minimise amount to draw
        if blockstodisplay > timeoutdisplayblocks:
            lcd["0"].setCursor(timeoutdisplayblocks, 3)
            lcd["0"].message((blockstodisplay - timeoutdisplayblocks) * chr(255))
        elif timeoutdisplayblocks > blockstodisplay:
            lcd["0"].setCursor(blockstodisplay, 3)
            lcd["0"].message((timeoutdisplayblocks - blockstodisplay ) * ' ')
        timeoutdisplayblocks = blockstodisplay
        
#MQTT message arrived
def on_message(mosq, obj, msg):
    """Process incoming MQTT message"""
    print(msg.topic + " - " + str(msg.payload))
    nodes = msg.topic.split('/')
    global timeoutstarted
    global timeoutdisplayblocks
    if nodes[0]=='clients':
        if nodes[2]=='configure':
            processRoundConfig(str(msg.payload))
            timeoutstarted = 0.0
            timeoutdisplayblocks = 0
        elif nodes[2] == 'instructions':
            display(str(msg.payload), 20, "0")
            #start timer?
            if 'timeout' in roundconfig and roundconfig['timeout'] > 0.0:
                timeoutdisplayblocks = 0
                timeoutstarted = time.time()
        elif nodes[2] in controlids:
            ctrlid = nodes[2]
            if nodes[3] == 'enabled':
                roundconfig['controls'][ctrlid]['enabled'] = False
                #switch it off?
                display(" ", config['local']['controls'][ctrlid]['display'], ctrlid)
            elif nodes[3] == 'name':
                display(str(msg.payload), config['local']['controls'][ctrlid]['display'], ctrlid)
    elif nodes[0] == 'server':
        if nodes[1] == 'ready':
            mess = str(msg.payload)
            if mess == 'started':
                client.publish("server/register", json.dumps(config['interface']))
            elif mess == 'ready':
                global hasregistered
                if not hasregistered:
                    hasregistered = True
                    client.publish("server/register", json.dumps(config['interface']))
                    
#Process control value assignment
def processControlValueAssignment(value, ctrlid, override=False):
    """Process control value assignment"""
    roundsetup = roundconfig['controls'][ctrlid]
    ctrltype = roundsetup['type']
    ctrldef = roundsetup['definition']
    if 'value' not in ctrldef or ctrldef['value'] != value or override:
        controlsetup = config['local']['controls'][ctrlid]
        hardwaretype = controlsetup['hardware']
        pins = controlsetup['pins']
        if hardwaretype == 'phonestylemenu':
            if ctrltype == 'toggle':
       	        if controlsetup['display']['height'] > 3:
                    if value:
                        displayValueLine("On", ctrlid)
                        #Light the LED red
                    else:
                        displayValueLine("Off", ctrlid)
                        #Uswitch off LED
            elif ctrltype == 'selector':
                if controlsetup['display']['height'] > 3:
                    displayValueLine(str(value), ctrlid)
            elif ctrltype == 'colour':
                if controlsetup['display']['height'] > 3:
                    displayValueLine(str(value), ctrlid)
                #Light the LED the right colours
            elif ctrltype == 'words':
               if controlsetup['display']['height'] > 3:
                   displayValueLine(value, ctrlid)
        elif hardwaretype == 'bargraphpotentiometer':
            if ctrltype == 'toggle':
    	        if value:
    	            barGraph(10)
                else:
    	            barGraph(0)
            elif ctrltype == 'selector':
                barGraph(value)
        elif hardwaretype == 'combo7SegColourRotary':
            if ctrltype == 'toggle':
                if value:
                    displayDigits('On')
                    #Light LED red
                else:
                    displayDigits('Off')
                    #Switch off LED
            elif ctrltype == 'selector':
                displayDigits(str(value))
                #Switch off LED
            elif ctrltype == 'colour':
                #Light LED appropriate colour
                if value == 'red':
                    displayDigits("RED")
                elif value == 'green':
                    displayDigits("GREN")
                elif value == 'blue':
                    displayDigits("BLUE")
                elif value == 'yellow':
                    displayDigits("YELO")
                elif value == 'cyan':
                    displayDigits("CYAN")
            elif ctrltype == 'words':
                #Switch off LED
                displayDigits(value.upper())
        elif hardwaretype == 'illuminatedbutton':
            if ctrltype == 'toggle':
                if value:
                    GPIO.output(pins['LED'], GPIO.HIGH)
                else:
                    GPIO.output(pins['LED'], GPIO.LOW)
        elif hardwaretype == 'potentiometer':
            if ctrltype == 'toggle':
                if controlsetup['display']['height']>3:
                    if value:
                        displayValueLine("On", ctrlid)
                        #Light the LED red
                    else:
                        displayValueLine("Off", ctrlid)
                        #Switch off LED
            elif ctrltype == 'selector':
                if controlsetup['display']['height']>3:
                    displayValueLine(str(value), ctrlid)
            elif ctrltype == 'colour':
                if controlsetup['display']['height']>3:
                    displayValueLine(str(value), ctrlid)
                #Light the LED the right colours
            elif ctrltype == 'words':
                if controlsetup['display']['height']>3:
                    displayValueLine(value, ctrlid)
            elif ctrltype == 'verbs':
                if controlsetup['display']['height']>3:
                    displayValueLine(value, ctrlid)
        elif hardwaretype == 'illuminatedtoggle':
            if ctrltype == 'toggle':
                if controlsetup['display']['height']>3:
                    if value:
    	                displayValueLine("On", ctrlid)
                        GPIO.output(pins['LED'], GPIO.HIGH)
                    else:
                        displayValueLine("Off", ctrlid)
                        GPIO.output(pins['LED'], GPIO.LOW)
        elif hardwaretype == 'keypad':
            #no need for cases
            displayValueLine(value)
        ctrldef['value'] = value
            
#Process an incoming config for a round
def processRoundConfig(roundconfigstring):
    """Process an incoming config for a round"""
    x = json.loads(roundconfigstring)
    for key in x.keys():
        roundconfig[key] = x[key]
    display(roundconfig['instructions'], 20, "0")
    for ctrlid in controlids:
        roundsetup = roundconfig['controls'][ctrlid]
        controlsetup = config['local']['controls'][ctrlid]
        display(roundsetup['name'], controlsetup['display']['width'], ctrlid)
        if 'definition' in roundsetup and roundsetup['enabled']:
            ctrltype = roundsetup['type']
            ctrldef = roundsetup['definition']
            #there's more to setup of course
            hardwaretype = config['local']['controls'][ctrlid]['hardware']
            if hardwaretype == 'phonestylemenu':
                if ctrltype == 'toggle':
                    displayButtonsLine("Off", "On", ctrlid)
                elif ctrltype == 'verbs':
                    displayButtonsLine(ctrldef['pool'][0], ctrldef['pool'][1], ctrlid)
                else:
                    displayButtonsLine("<<<<", ">>>>", ctrlid)
            elif hardwaretype == 'combo7SegColourRotary':
                if ctrltype == 'button':
                    displayDigits("PUSH")
            if 'value' in ctrldef:
                processControlValueAssignment(ctrldef['value'], ctrlid, True)

def translateCalibratedValue(rawvalue, calibrationdict):
    """Calculate a calibrated value from a raw value and translation dictionary"""
    sortedlist = OrderedDict(sorted(calibrationdict.items(), key=lambda t: t[1]))
    for value in sortedlist:
        if rawvalue < calibrationdict[value]:
            return value
    
#Poll controls, interpret into values, recognise changes, inform server
def pollControls():
    """Poll controls, interpret into values, recognise changes, inform server"""
    if len(roundconfig) > 0:
        for ctrlid in controlids:
            roundsetup = roundconfig['controls'][ctrlid]
            controlsetup = config['local']['controls'][ctrlid]
            if 'definition' in roundsetup and roundsetup['enabled']:
                ctrltype = roundsetup['type'] #Which supported type are we this time
                ctrldef = roundsetup['definition']
                pins = controlsetup['pins']
                #State is physical state of buttons etc
                if 'state' in ctrldef:
                    ctrlstate = ctrldef['state']
                else:
                    ctrlstate = None
                #Value is as interpreted by the abstracted control type
                if 'value' in ctrldef:
                    ctrlvalue = ctrldef['value']
                else:
                    ctrlvalue = None
                hardwaretype = config['local']['controls'][ctrlid]['hardware'] #Which hardware implementation
                #For the particular hardware, poll the controls and decide what it means
                value = ctrlvalue
                if hardwaretype == 'phonestylemenu':
                    btn1 = GPIO.input(pins['BTN_1'])
                    btn2 = GPIO.input(pins['BTN_2'])
                    state = [btn1, btn2]
                    if ctrlstate != state:
                        if ctrlstate == None:
                            leftchanged = True
                            rightchanged = True
                        else:
                            leftchanged = ctrlstate[0] != state[0]
                            rightchanged = ctrlstate[1] != state[1]
                        leftpressed = state[0]
                        rightpressed = state[1]
                        if ctrltype == 'toggle':
                            if rightchanged and rightpressed: #On
                                value = 1
                            elif leftchanged and leftpressed: #Off
                                value = 0
                        elif ctrltype == 'selector':
                            if rightchanged and rightpressed:
                                if ctrlvalue < ctrldef['max']:
                                    value = ctrlvalue + 1
                            elif leftchanged and leftpressed:
                                if ctrlvalue > ctrldef['min']:
                                    value = ctrlvalue - 1
                        elif ctrltype == 'colours':
                            #get current index from pool of values
                            idx = ctrldef['values'].index(ctrlvalue)
                            if rightchanged and rightpressed:
                                if idx < len(ctrldef['values']) - 1:
                                    idx += 1
                                else:
                                    idx = 0
                            elif leftchanged and leftpressed:
                                if idx > 0:
                                    idx -= 1
                                else:
                                    idx = len(ctrldef['values']) - 1
                            value = str(ctrldef['values'][idx])
                        elif ctrltype == 'words':
                            #get current index from pool of values
                            idx = ctrldef['pool'].index(ctrlvalue)
                            if rightchanged and rightpressed:
                                if idx < len(ctrldef['pool']) - 1:
                                    idx += 1
                                else:
                                    idx = 0
                            elif leftchanged and leftpressed:
                                if idx > 0:
                                    idx -= 1
                                else:
                                    idx = len(ctrldef['pool']) - 1
                            value = str(ctrldef['pool'][idx])
                        elif ctrltype == 'verbs':
                            if rightchanged and rightpressed:
                                value = str(ctrldef['pool'][1])
                            elif leftchanged and leftpressed:
                                value = str(ctrldef['pool'][0])
                elif hardwaretype == 'illuminatedbutton':
                    btn = GPIO.input(pins['BTN'])
                    state = btn
                    if ctrlstate != state:
                        if ctrltype == 'button':
                            value = state
                        elif ctrltype == 'toggle':
                            if state:
                                value = not ctrlvalue
                elif hardwaretype == 'illuminatedtoggle':
                    sw = GPIO.input(pins['SW'])
                    state = sw
                    if ctrlstate != state:
                        if ctrltype == 'toggle':
                            if state:
                                value = not ctrlvalue
                elif hardwaretype == 'bargraphpotentiometer':
                    pot = ADC.read(pins['POT'])
                    #Interpretation varies by state
                    if ctrltype == 'toggle':
                        if pot < 0.3:
                            state = 0
                        elif pot > 0.7:
                            state = 1
                        else:
                            state = ctrlstate #if not decisively left or right, stay the same
                        if state != ctrlstate:
                            value = state
                    elif ctrltype == 'selector':
                        state = translateCalibratedValue(pot, controlsetup['calibration'][ctrltype])
                        value = int(state)
                elif hardwaretype == 'potentiometer':
                    pot = ADC.read(pins['POT'])
                    if ctrltype == 'toggle':
                        if pot < 0.3:
                            state = 0
                        elif pot > 0.7:
                            state = 1
                        else:
                            state = ctrlstate #if not decisively left or right, stay the same
                        if state != ctrlstate:
                            value = state
                    elif ctrltype == 'selector':
                        state = translateCalibratedValue(pot, controlsetup['calibration'][ctrltype])
                        value = int(state)
                    elif ctrltype == 'colour':
                        state = translateCalibratedValue(pot, controlsetup['calibration'][ctrltype])
                        value = str(state)
                    elif ctrltype == 'words':
                        state = translateCalibratedValue(pot, controlsetup['calibration'][ctrltype])
                        value = str(ctrldef['pool'][int(state)])
                    elif ctrltype == 'verbs':
                        state = translateCalibratedValue(pot, controlsetup['calibration']['words'])
                        value = str(ctrldef['pool'][int(state)])
                #more cases to go here
                if value != ctrlvalue:
                    processControlValueAssignment(value, ctrlid)
                    print("Publishing control " + ctrlid + " which is " + hardwaretype + " / " + ctrltype)
                    print ("value = " + str(value))
                    client.publish("clients/" + ipaddress + "/" + ctrlid + "/value", value)
                    ctrldef['value'] = value
                ctrldef['state'] = state
                        
                    
#Setup displays
displayDigits('    ')
barGraph(0)

#Setup MQTT
client.on_message = on_message
client.connect(server)
subsbase = "clients/" + ipaddress + "/"
client.subscribe(subsbase + "configure")
client.subscribe(subsbase + "instructions")
client.subscribe("server/ready")

for controlid in [x['id'] for x in config['interface']['controls']]:
    client.subscribe(subsbase + str(controlid) + '/name')
    client.subscribe(subsbase + str(controlid) + '/enabled')
    
#Main loop
while(client.loop() == 0):
    pollControls()
    displayTimer()
    

import sys
sys.path.append('./bigsevseg')
import Adafruit_MCP230xx as ExpIO
import time
print "imports done"
sevenSeg = ExpIO.Adafruit_MCP230XX(0x20, 16)
print "init done"

#    A
#    _
#F  |_| B
#E  |_| C
#
#    D
#
#Centre: G

#seg = dict(A = 7, B = 9, C = 10, D = 11, E = 12, F = 13, G = 14)

seg = dict(A = 14, B = 10, C = 13, D = 12, E = 7, F = 11, G = 9)

digit_1 = [     'B', 'C'                    ]
digit_2 = ['A', 'B',      'D', 'E'          ]
digit_3 = ['A', 'B', 'C', 'D',           'G']
digit_4 = [     'B', 'C',           'F', 'G']
digit_5 = ['A',      'C', 'D',      'F'     ]
digit_6 = ['A',      'C', 'D', 'E', 'F', 'G']
digit_7 = ['A', 'B', 'C'                    ]
digit_8 = ['A', 'B', 'C', 'D', 'E', 'F', 'G']
digit_9 = ['A', 'B', 'C', 'D',      'F', 'G']
digit_0 = ['A', 'B', 'C', 'D', 'E', 'F'     ]

digits = [digit_1, digit_2, digit_3, digit_4, digit_5, digit_6, digit_7, digit_8, digit_9, digit_0]

for i in seg:
    print seg[i]
    sevenSeg.config(seg[i], ExpIO.Adafruit_MCP230XX.OUTPUT)

print "All pins set to output"

def clearSevenSeg():
    for i in seg:
        sevenSeg.output(seg[i], 0)

def digitSevenSeg(digit):
    for s in digit:
        sevenSeg.output(seg[s], 1)

while True:
    print "blink"
    for i in digits:
        clearSevenSeg()
        digitSevenSeg(i)
        time.sleep(0.5)

# Importing all libraries
import re
import subprocess
import time
import sys
import Adafruit_DHT
import RPi.GPIO as GPIO
import smbus


# Defing the global variables
PRESENCE = False
FLAME_GPIO_PIN = 27
FLAME_STATE = False
FLAME = 0
TEMP_HUMIDITY_PIN = 4
TEMP_STATE = True
TEMP = 0
HUMIDITY_STATE = True
HUMIDITY = 0
PIR_GPIO_PIN = 17
PIR_STATE = True
PIR = 0
SMOKE_GPIO_PIN = 18
SMOKE_STATE = True
SMOKE = 0

# Setting up the light intensity sensor
POWER_DOWN = 0x00
POWER_ON   = 0x01 
RESET      = 0x07

CONTINUOUS_LOW_RES_MODE = 0x13
CONTINUOUS_HIGH_RES_MODE_1 = 0x10
CONTINUOUS_HIGH_RES_MODE_2 = 0x11
ONE_TIME_HIGH_RES_MODE_1 = 0x20
ONE_TIME_HIGH_RES_MODE_2 = 0x21
ONE_TIME_LOW_RES_MODE = 0x23

bus = smbus.SMBus(0)

def convertToNumber(data):
    result=(data[1] + (256 * data[0])) / 1.2
    return (result)
def readLight(addr=DEVICE):
    data = bus.read_i2c_block_data(addr,ONE_TIME_HIGH_RES_MODE_1)
    return convertToNumber(data)




# Setting up the GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(FLAME_GPIO_PIN, GPIO.IN)
GPIO.setup(PIR_GPIO_PIN, GPIO.IN)
GPIO.setup(SMOKE_GPIO_PIN, GPIO.IN)

STATE_TABLE = {
    'FLAME' : True,
    'TEMP': False,
    'HUMIDITY' : False,
    'PIR' : False,
    'SMOKE' : True
}

# Defing the functions

def getTempAndHumidity(pin):
    ''' This function updates the values of temperature and humidity depending
        of the states of humidity and temperature.
        :param: pin int
            The data pin number of the DHT11
        :return: This function does not return any value, it only updates
            if necessary the TEMP and HUMIDITY values
    '''
    global PRESENCE, TEMP, HUMIDITY, STATE_TABLE
    if PRESENCE and STATE_TABLE['HUMIDITY']:
        HUMIDITY, _ = Adafruit_DHT.read_retry(11, 4)
        print(' > HUMIDITY - {}'.format(HUMIDITY))
    if PRESENCE and STATE_TABLE['TEMP']:
        _, TEMP = Adafruit_DHT.read_retry(11, 4)
        print(' > TEMP - {}'.format(TEMP))

def getFlame(pin):
    ''' This function updates the presence of the flame
        :param: pin int
            The GPIO (BCM type) data pin of the flame sensor
        :return: Rhis functions does not returns anythink, but depending on the 
            FLAME_STATE it updeates or not the FLAME state
    '''
    global PRESENCE, STATE_TABLE, FLAME
    if STATE_TABLE['FLAME']:
        FLAME = GPIO.input(pin)
        print(' > FLAME - {}'.format(FLAME))

def getPIR(pin):
    global PRESENCE, STATE_TABLE, PIR
    if not PRESENCE and STATE_TABLE['PIR']:
        PIR = GPIO.input(pin)
        print(' > Movement - {}'.format(PIR))

def getSmoke(pin):
    global PRESENCE, STATE_TABLE, SMOKE
    if STATE_TABLE['SMOKE']:
        SMOKE = GPIO.input(pin)
        print(' > SMOKE - {}'.format(SMOKE))

def extractMAC(data):
    ''' This function takes the output from the call of the command
            sudo arp-scan -l
        and returns a list of MAC adresses that are connected right now to the WiFi
        :param: data bytes
            The output of the command
        :return: MAC_list list
            The list of all MACs that are connected to the WiFI adress
    '''
    data = data.decode()
    data = data.split('\n')
    data = [d for d in data if '\t' in d]
    MAC_list = [d.split('\t')[1] for d in data]
    MAC_list = [str(MAC) for MAC in MAC_list]
    return MAC_list

# Defing the list of MAC of adresses allowed to acces the house
ALLOWED_MACS = {
    'Vasika':'04:d3:b0:fc:23:53',
    "Vasika's Phone" : '00:ec:0a:c4:9b:15'
}
# Startup of the system
print(" > START UP")

while True:
    presence = 0
    p = subprocess.Popen(['sudo', 'arp-scan', '-l'], stdout=subprocess.PIPE)
    output, err = p.communicate()
    mac_list = extractMAC(output)
    for user in ALLOWED_MACS:
        if ALLOWED_MACS[user] in mac_list:
            print(" > {} in the house!!!".format(user))
            presence+=1
    if presence == 0:
        print(" > No one in the house!!!")
        PRESENCE = False
    else:
        PRESENCE = True
    getTempAndHumidity(TEMP_HUMIDITY_PIN)
    getFlame(FLAME_GPIO_PIN)
    #getPIR(PIR_GPIO_PIN)
    getSmoke(SMOKE_GPIO_PIN)
    lightLevel=readLight()
    print("LIGHT LEVEL - {}".format(lightLevel))
    time.sleep(2)
    

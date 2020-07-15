# Importing all libraries
import re
import subprocess
import time
import sys
import Adafruit_DHT
import RPi.GPIO as GPIO
from multiprocessing import Process

# Defing the global variables
# PRESENCE states if a person ALLOWED_USERS in in the house
PRESENCE = False
# Global variabiles related Flame sensor 
FLAME_GPIO_PIN = 27
FLAME = 0
# Global variables related to DHT11 (Humidity and Temperature) sensor
TEMP_HUMIDITY_PIN = 4
TEMP = 0
HUMIDITY = 0
# Global variables related to MQ2 (Smoke) sensor
SMOKE_GPIO_PIN = 18
SMOKE = 0
# Global variables related to lamps (first and second floor)
LIGHT_FLOOR1_GPIO_PIN = 23
LIGHT_FLOOR2_GPIO_PIN = 22
# Global variables related to Light sensor
LIGHT_GPIO_PIN = 21
DAY = 0
# Global variables related to Signalisation mechanism
SIGNALISATION_GPIO_PIN = 20
# Global varaibles related to Inundation detection
INUNDATION_GPIO_PIN = 24
INUNDATION = 0

# Setting up the GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(FLAME_GPIO_PIN, GPIO.IN)
GPIO.setup(SMOKE_GPIO_PIN, GPIO.IN)
GPIO.setup(LIGHT_GPIO_PIN, GPIO.IN)
GPIO.setup(INUNDATION_GPIO_PIN, GPIO.IN)
GPIO.setup(TEMP_HUMIDITY_PIN, GPIO.IN)
GPIO.setup(LIGHT_FLOOR1_GPIO_PIN, GPIO.OUT)
GPIO.setup(LIGHT_FLOOR2_GPIO_PIN, GPIO.OUT)
GPIO.setup(SIGNALISATION_GPIO_PIN, GPIO.OUT)

# Defining the state table
STATE_TABLE = {
    'FLAME' : True,
    'TEMP': True,
    'HUMIDITY' : True,
    'SMOKE' : True,
    'STATE_LIGHT_FLOOR1':True,
    'STATE_LIGHT_FLOOR2':True,
    'LIGHT_STATE' : True,
    'SIGNALISATION' : True,
    '_INUNDATION' : False,
    '_FIRE' : False
}

# Defing the functions
def getTempAndHumidity(pin):
    ''' This function updates the values of temperature and humidity depending
        of the states of humidity and temperature uding DHT11 sensor.
        :param: pin int
            The data pin number of the DHT11 (BOARD mode)
        :return: This function does not return any value, it only updates
            if necessary the TEMP and HUMIDITY values
    '''
    global TEMP, HUMIDITY, STATE_TABLE
    if STATE_TABLE['HUMIDITY']:
        HUMIDITY, _ = Adafruit_DHT.read_retry(11, 4)
    else:
        HUMIDITY = None
    if STATE_TABLE['TEMP']:
        _, TEMP = Adafruit_DHT.read_retry(11, 4)
    else:
        TEMP = None

def getFlame(pin):
    ''' This function updates the presence of the flame depending of the
        FLAME STATE
        :param: pin int
            The GPIO (BCM mode) data pin of the flame sensor on the RPi used
        :return: This functions does not returns anythink, but depending on the 
            FLAME_STATE it updates or not the FLAME state
    '''
    global STATE_TABLE, FLAME
    if STATE_TABLE['FLAME']:
        FLAME = GPIO.input(pin)
    else:
        TEMP = None

def getSmoke(pin):
    '''This function updates the presence of the smoke using MQ2 sensor depending
        of the SMOKE STATE
        :param: pin int
            The GPIO (BCM mode) data pin of the MQ2 sensor on the RPi used
        :return:This functions does not returns anythink, but depending on the 
            SMOKE STATE it updates or not the SMOKE state
    '''
    global STATE_TABLE, SMOKE
    if STATE_TABLE['SMOKE']:
        SMOKE = GPIO.input(pin)
    else:
        SMOKE = None

def getLight(pin):
    ''' This function updates the presence of the light outside of housem
        (if there is daytime or not) using the lightsensor depending on LIGHT STATE
        :param: pin int
            The GPIO (BCM mode) data pin of the light sensor on the RPi used
        :return: This function dose not return anythnk, but depending on the LIGHT STATE
        it updates or not the DAY STATE
    '''
    global PRESENCE, STATE_TABLE, DAY
    if STATE_TABLE['LIGHT_STATE']:
        DAY = not GPIO.input(pin)

def setLight():
    ''' This function set the ligths on of off on the first and second floor
        depending of STATE_LIGHT_FLOOR1 and STATE_LIGHT_FLOOR2, PRESENCE and DAY
        global variables
        :param: None
            This function does not use any arguments, it only uses the global
            variable mentionated above.
        :return: This function does not return any value, it only sets the 
            light on the first and second floor.
    '''
    global PRESENCE, STATE_TABLE, LIGHT_FLOOR1_GPIO_PIN, LIGHT_FLOOR2_GPIO_PIN
    if PRESENCE and STATE_TABLE['STATE_LIGHT_FLOOR1'] and DAY:
        GPIO.output(LIGHT_FLOOR1_GPIO_PIN, 0)
    else:
        GPIO.output(LIGHT_FLOOR1_GPIO_PIN, STATE_TABLE['STATE_LIGHT_FLOOR1'])
    if PRESENCE and STATE_TABLE['STATE_LIGHT_FLOOR2'] and DAY:
        GPIO.output(LIGHT_FLOOR2_GPIO_PIN, 0)
    else:
        GPIO.output(LIGHT_FLOOR2_GPIO_PIN, STATE_TABLE['STATE_LIGHT_FLOOR2'])

def activate_signal(pin):
    ''' This function only activates the passive buzzer one time depending on the
        SIGNALISATION state
        :param: pin int
            The GPIO (BCM mode) pin of the passive buzzer on the RPi used
        :return: This function does not return any value, it only activates on time 
            the passive buzzer
    '''
    global STATE_TABLE
    if STATE_TABLE['SIGNALISATION']:
        GPIO.output(pin, 1)
        time.sleep(0.2)
        GPIO.output(pin, 0)
        time.sleep(0.2)

def getInundation(pin):
    ''' This functions detects whatever in the house is inundated or not, and if it
        is, it activate the signalisation 5 times.
        :param: pin int
            The GPIO (BCM mode) pin of the water level sensor on the RPi used
        :return: This function does not return any value, it only updates the
            INUNDATION state and activates 5 times the signalisation
    '''
    global STATE_TABLE
    STATE_TABLE['_INUNDATION'] = GPIO.input(pin)
    if STATE_TABLE['_INUNDATION']:
        print(' > Inundation')
        for i in range(5):
            activate_signal(SIGNALISATION_GPIO_PIN)

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
    "Vasika's Phone" : '00:ec:0a:c4:9b:15',
    "Tudorel" : '78:02:f8:3a:bb:e8',
    "Vladut" : 'd0:7f:a0:b3:e8:b1',
    "Mark" : 'dc:ef:ca:5c:5f:7e',
}
# Startup of the system
print(" > START UP")

# Entering in the endless loop
while True:
    # Defining empty list for storing the allowed 
    # people in the house house at a time
    persons_on = []
    # Scaning the WiFi network for the MAC adresses
    p = subprocess.Popen(['sudo', 'arp-scan', '-l'], stdout=subprocess.PIPE)
    output, err = p.communicate()
    # Getting the MAC adresses of all users connected to the house WiFI
    mac_list = extractMAC(output)
    # Searching for the allowed users in the mac_list and printing them
    for user in ALLOWED_MACS:
        if ALLOWED_MACS[user] in mac_list:
            print(" > {} in the house!!!".format(user))
            persons_on.append(user)
    # Cheking if there are someone allowed in the house and setting the PRESENCE
    # variable
    if len(persons_on) == 0:
        print(" > No one in the house!!!")
        PRESENCE = False
    else:
        PRESENCE = True
    # Getting the temperature and humidity
    getTempAndHumidity(TEMP_HUMIDITY_PIN)
    # Getting the presence of the flame
    getFlame(FLAME_GPIO_PIN)
    # Getting the presence of the smoke
    getSmoke(SMOKE_GPIO_PIN)
    # Setting the light
    setLight()
    # Getting the presence of light outside of the house
    getLight(LIGHT_GPIO_PIN)
    # Checking the presence of the fire in the house and activating the alarm
    if FLAME and SMOKE:
        print(' > FIRE DETECTED')
        STATE_TABLE['_FIRE'] = 1
        for i in range(10):
            activate_signal(SIGNALISATION_GPIO_PIN)
    else:
        STATE_TABLE['_FIRE'] = 0
    # Geting the presence of the inundation in the house
    getInundation(INUNDATION_GPIO_PIN)
    to_send = {
        'PERSONS_ON' : persons_on,
        'FLAME' : FLAME,
        'HUMIDITY' : HUMIDITY,
        'TEMP' : TEMP,
        'SMOKE' : SMOKE,
        'STATE_LIGHT_FLOOR1' : STATE_TABLE['STATE_LIGHT_FLOOR1'],
        'STATE_LIGHT_FLOOR2' : STATE_TABLE['STATE_LIGHT_FLOOR2'],
        'DAY' : DAY,
        'FIRE' : STATE_TABLE['_FIRE'],
        'INUNDATION' : STATE_TABLE['_INUNDATION']
    }
    print('*'*20)
    for key in to_send:
        print("{} - {}".format(key, to_send[key]))
    

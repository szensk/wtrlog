import sys
import sqlite3
import time
import random
import board
import busio
import adafruit_bme280
import asyncio
from kasa import SmartPlug

def createTables(c):
    with open("wlog.sql", "r") as f:
        content = f.read()
        c.executescript(content)

i2c = busio.I2C(board.SCL, board.SDA)
bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c)

opts = [opt for opt in sys.argv[1:] if opt.startswith("-")]
testMode = "-t" in opts

# open sqlite db
dbconn = sqlite3.connect('wtr.db')
dbc = dbconn.cursor()
createTables(dbc)

# connect to kasa devices
plug = SmartPlug("kasa1.lan")
asyncio.run(plug.update())

LAST_HOUR = 60 * 60

print("Connected to: " + plug.alias)
if testMode:
    print("Running in test mode")

def getIntegerTime():
    return int(time.time())


def recordReadings(temperature, humidity, pressure):
    ts = getIntegerTime()
    dbc.execute('INSERT INTO Reading VALUES (?, ?, ?, ?, ?)',
                (ts, temperature, humidity, pressure, plug.alias))


def recordTransition(state, alias, stamp):
    dbc.execute('INSERT INTO Switch VALUES (?, ?, ?)', (stamp, state, alias))


def getAverageHumidity(timeRange):
    cur = dbconn.cursor()
    ts = getIntegerTime() - timeRange
    cur.execute(
        'SELECT AVG(Humidity) FROM Reading WHERE Time > ? AND Source = ?', (ts, plug.alias))
    average = cur.fetchall()
    print(average)
    return average[0][0]


def canTransition(timeRange):
    cur = dbconn.cursor()
    ts = getIntegerTime() - timeRange
    cur.execute(
        'SELECT Time, State, Device FROM Switch WHERE Time > ? AND Device = ?', (ts, plug.alias))
    transitions = cur.fetchall()
    return len(transitions) == 0


def transitionPlug(turnOn):
    print("Turning plug " + ("on" if turnOn else "off"))
    if testMode:
        return

    if not canTransition(LAST_HOUR):
        print("Unable to transition")
        return

    asyncio.run(plug.turn_on() if turnOn else plug.turn_off())
    asyncio.run(plug.update())
    recordTransition(turnOn, plug.alias, getIntegerTime())

def fakeAverageHumitiy(time):
    fake = random.random() * 100
    print("Humidity: " + str(fake))
    return fake

def main(threshold, averageFunc):
    while True:
        plugIsOn = plug.is_on
        temperature = bme280.temperature
        humidity = bme280.humidity
        pressure = bme280.pressure

        #print("T: %0.1fC | H: %0.1f%% | P: %0.1fhPA" %
        #      (temperature, humidity, pressure))
        recordReadings(temperature, humidity, pressure)

        avg = averageFunc(LAST_HOUR)
        if (plugIsOn and avg > threshold):
            transitionPlug(False)
        elif (not plugIsOn and avg <= threshold):
            transitionPlug(True)

        dbconn.commit()
        asyncio.run(plug.update())
        time.sleep(10)

main(25, fakeAverageHumitiy)
#!/usr/bin/env python3
import sys
import sqlite3
import time
import random
import board
import busio
import adafruit_bme280
import asyncio
from kasa import SmartPlug

PLUG_HOST = "kasa1.lan"
DB_NAME = "wtr.db"
LAST_HOUR = 60 * 60
SLEEP_SECONDS = 60


def createTables(c):
    with open("wtrd.sql", "r") as f:
        content = f.read()
        c.executescript(content)


# bme 280 setup
i2c = busio.I2C(board.SCL, board.SDA)
bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c)

args = [arg for arg in sys.argv[1:] if not arg.startswith("-")]
opts = [opt for opt in sys.argv[1:] if opt.startswith("-")]
testMode = "-t" in opts

# setup sqlite database
dbconn = sqlite3.connect(DB_NAME)
dbc = dbconn.cursor()
createTables(dbc)

# connect to kasa devices, initial update to receive state information
plug = SmartPlug(PLUG_HOST)
asyncio.run(plug.update())

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


def getReadingCount(timeRange):
    cur = dbconn.cursor()
    ts = getIntegerTime() - timeRange
    cur.execute(
        'SELECT COUNT(*) FROM Reading WHERE Time > ? AND Source = ?', (ts, plug.alias))
    average = cur.fetchall()
    return average[0][0]


def getAverageHumidity(timeRange):
    cur = dbconn.cursor()
    ts = getIntegerTime() - timeRange
    cur.execute(
        'SELECT AVG(Humidity) FROM Reading WHERE Time > ? AND Source = ?', (ts, plug.alias))
    average = cur.fetchall()
    return average[0][0]


# Prevent turning on or off the switch if it already turned on or off in the last timeInSeconds seconds
def canTransition(timeInSeconds):
    cur = dbconn.cursor()
    ts = getIntegerTime() - timeInSeconds
    cur.execute(
        'SELECT Time, State, Device FROM Switch WHERE Time > ? AND Device = ?', (ts, plug.alias))
    transitions = cur.fetchall()
    readings = getReadingCount(timeInSeconds)
    return len(transitions) == 0 and readings > (LAST_HOUR/SLEEP_SECONDS/2)


def transitionPlug(turnOn):
    print("Turning plug " + ("on" if turnOn else "off"))
    if testMode:
        return

    if not canTransition(LAST_HOUR):
        print("Unable to transition: too soon.")
        return

    try:
        asyncio.run(plug.turn_on() if turnOn else plug.turn_off())
        asyncio.run(plug.update())
        recordTransition(turnOn, plug.alias, getIntegerTime())
    except:
        print("Unable to transition: error.")


def main(threshold, averageFunc):
    while True:
        try:
            plugIsOn = plug.is_on
            temperature = bme280.temperature
            humidity = bme280.humidity
            pressure = bme280.pressure

            recordReadings(temperature, humidity, pressure)

            avg = averageFunc(LAST_HOUR)
            if (plugIsOn and avg < threshold):
                transitionPlug(False)
            elif (not plugIsOn and avg >= threshold):
                transitionPlug(True)

            dbconn.commit()
            asyncio.run(plug.update())
        except:
            print("Unhandled error")
        finally:
            time.sleep(SLEEP_SECONDS)


humidityPoint = 50
if len(args) > 0:
    humidityPoint = int(args[0])

main(humidityPoint, getAverageHumidity)

#!/bin/python

# imports
import serial
import subprocess

# variables
DEBUG=1
gpsFreshness= 5 # 0 is freshest, greater number indicates staleness
lastAudio="lostGPS" # Can either be lostGPS or acquiredGPS for audio notifications 

# init serial port
serial = serial.Serial('/dev/ttyUSB0',4800, timeout = 2)

# connect to gps and print the output

def gpsRead():
	global gpsFreshness
	global lastAudio
	# read line from serial output
	sout= serial.readline()
	# split the line by comma 
	sOutSplit = sout.split(',')
	
	# check if it contains data we care about
	if sOutSplit[0] == '$GPGGA':
		# Here we have what we are looking for
		lat = sOutSplit[2]
		latDir = sOutSplit[3]
		lon = sOutSplit[4]
		lonDir = sOutSplit[5]
		fix = sOutSplit[6]
		numSat = sOutSplit[7]
		elev = sOutSplit[9]
		if DEBUG:
			print "lat: " + str(lat)
			print "latDir: " + str(latDir)
			print "lon: " + str(lon)
			print "lonDir: " + str(lonDir)
			print "fix: " + str(fix) 
			print "numSat: " + str(numSat)
			print "elev: " + str(elev)
			print ""
		# If there is no fix, up the staleness
		if fix == "1":
			gpsFreshness = 0
		else:
			gpsFreshness += 1 
		# playback an audi clip if the gps was lost or acquired
		if gpsFreshness > 5 and lastAudio == "acquiredGPS":
			subprocess.call("mplayer location_lost.ogg",shell=True)
			lastAudio = "lostGPS"
		elif gpsFreshness == 0 and lastAudio == "lostGPS":
			subprocess.call("mplayer location_recovered.ogg",shell=True)
			lastAudio = "acquiredGPS"
		print "freshness: " + str(gpsFreshness)

def gpsReadRaw():
	print serial.readline()
		
# Main 
while 1:
	gpsRead()
	#gpsReadRaw()

# check if we have a lock and play audio notification

#  


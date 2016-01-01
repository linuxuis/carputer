#!/bin/python

# imports
import serial
import subprocess
from datetime import datetime
import sys
import atexit
import os

# variables
DEBUG=1
gpsFreshness= 5 # 0 is freshest, greater number indicates staleness
lastAudio="lostGPS" # Can either be lostGPS or acquiredGPS for audio notifications 

'''
Class to store the gps data into 
'''
class gpsData:
	time = 0
	lat = 0
	latDir = 0
	lon = 0
	lonDir = 0 
	fix = 0
	numSat = 0
	elev = 0
	

# init serial port
serial = serial.Serial('/dev/ttyUSB0',4800, timeout = 2)

# connect to gps and print the output

'''
function to read the serial output of the GPS module and parse the GPS data 
gpsData: class to store the GPS information 
gpxFile: File object for writing the gps data to in a gpx format 
'''
def gpsRead(gpsData, gpxFile):
	global gpsFreshness
	global lastAudio
	# read line from serial output
	sout= serial.readline()
	# split the line by comma 
	sOutSplit = sout.split(',')
	
	# check if it contains data we care about
	if sOutSplit[0] == '$GPGGA':
		# Here we have what we are looking for
		gpsData.time=getUTCtime()
		gpsData.latDir = sOutSplit[3]
		gpsData.lonDir = sOutSplit[5]
		gpsData.lat = nmeaToDecimal(sOutSplit[2],gpsData.latDir)
		gpsData.lon = nmeaToDecimal(sOutSplit[4],gpsData.lonDir)
		gpsData.fix = sOutSplit[6]
		gpsData.numSat = sOutSplit[7]
		gpsData.elev = sOutSplit[9]
		if DEBUG:
			print "time: " + str(gpsData.time)
			print "lat: " + str(gpsData.lat)
			print "latDir: " + str(gpsData.latDir)
			print "lon: " + str(gpsData.lon)
			print "lonDir: " + str(gpsData.lonDir)
			print "fix: " + str(gpsData.fix) 
			print "numSat: " + str(gpsData.numSat)
			print "elev: " + str(gpsData.elev)
			print ""
		# If there is a fix, reset staleness 
		if gpsData.fix == "1":
			gpsFreshness = 0
			# Write the data to file as well if we have a new fix 
			writeGPX(gpsData,gpxFile)
		# Otherwise up it
		else:
			gpsFreshness += 1 
		# playback an audio clip if the gps was lost or acquired
		if gpsFreshness > 5 and lastAudio == "acquiredGPS":
			subprocess.call("mplayer location_lost.ogg > /dev/null 2>&1",shell=True)
			lastAudio = "lostGPS"
		elif gpsFreshness == 0 and lastAudio == "lostGPS":
			subprocess.call("mplayer location_recovered.ogg > /dev/null 2>&1",shell=True)
			lastAudio = "acquiredGPS"
		print "freshness: " + str(gpsFreshness)
'''
function to read and print the entire output from the GPS module 
'''
def gpsReadRaw():
	print serial.readline()

'''
function to print the GPS data to a GPS file 
gpsData: the class with the gps data
gpxFile: file object to save the gpx track to 
'''
def writeGPX(gpsData,gpxFile):
	# First check if we even have a fix.. If not, then do nothing
	if gpsData.fix == 0:
		# We have no fix here
		if DEBUG:
			print "No GPS fix! Skipping writing trackpoint to file!"
		return
	else:
		# Here we have a valid fix, so write the waypoint to the file
		gpxFile.write('\t\t<trkpt lat="' + str(gpsData.lat) + '" lon="' + str(gpsData.lon) + '">\n\t\t\t<ele>' + str(gpsData.elev) + '</ele>\n\t\t\t<time>' + str(gpsData.time) + '</time>\n\t\t</trkpt>\n')
	 

'''
Get the UTC time to save for GPX output formatted as: 2007-10-14T10:09:57Z
Return: the time in gpx file formatted time 
'''
def getUTCtime():
	now = datetime.utcnow()
	gpxTime = str(now).split(' ')[0] + "T" + str(now).split(' ')[1].split('.')[0] + "Z"
	return gpxTime 

'''
function to convert nmea to decimal degrees
nmea: nmea coordinate to be converted I.E. (31.376895)
direction: direction of coordinate I.E. (N E S or W)
returns the decimal coordinate 
'''
def nmeaToDecimal(nmea, direction):
	# Convert the nmea to decimal (d)dd + mm.mmmm / 60 where nmea = dddmm.mmmm
	# Obtained from http://www.heystephenwood.com/2014/05/converting-nmea-latitude-and-longitude.html
	dec = int(str(nmea).split('.')[0][:-2]) + float(str(nmea)[-7:])/60
	# We still need to determine where this is to make the decimal coordinate positive or negative
	if direction == 'N':
		return dec
	elif direction == 'E':
		return dec
	elif direction == 'S':
		return -dec
	elif direction == 'W':
		return -dec
	else:
		# Here we have an incorrect direction
		print "Incorrect Direction given!!"
		sys.exit()

'''
function to close the GPX File 
'''
def closeGPXfile():
	global gpxFile
	gpxFile.write('\t</trkseg></trk>\n</gpx>')
	gpxFile.close()
	if DEBUG:
		print 'Closed the gpx file!'
	

'''
function to add the proper headers etc to the file. 
gpxFile: the file object used for writing 
'''
def initGpxFile(gpxFile):
	gpxFile.write('<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>\n')
	gpxFile.write('<gpx version="1.1" creator="linuxuis carputer GPX recorder - https://github.com/linuxuis/carputer">\n')
	gpxFile.write('\t<trk><trkseg>\n')
	
# Main 
gps = gpsData()

# Create a filename to store the gpx track as based on current time ('2015-12-31_18:04:36.gpx')
filename=str(datetime.now()).replace(' ','_').split('.')[0] + '.gpx'

# create command to run video recording 
command="ffmpeg -f alsa -i hw:2 -s 1920x1080 -f v4l2 -vcodec h264 -i /dev/video0 -copyinkf -vcodec copy -strict -2 " + str(filename).split('.')[0] + ".mp4 " + "2> /dev/null &"

# Begin recording video and run in background process (will terminate when script is terminated)
os.system(command)

# Open file for writing 
gpxFile = open(filename, "w")
# Write the header etc to the gpxFile
initGpxFile(gpxFile)


# Register function to run at exit of code 
atexit.register(closeGPXfile)

while 1:
	# read GPS data and update the gps class - also writes to the file 
	gpsRead(gps, gpxFile)
	#gpsReadRaw()




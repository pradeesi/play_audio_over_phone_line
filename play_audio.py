##------------------------------------------
##--- Author: Pradeep Singh
##--- Blog: https://iotbytes.wordpress.com/play-audio-file-on-phone-line-with-raspberry-pi/
##--- Date: 24th June 2018
##--- Version: 1.0
##--- Python Ver: 2.7
##--- Description: This python code will pick an incomming call and play an audio msg on the Phone line.
##------------------------------------------


import serial
import time
import threading
import atexit
import sys
import re
import wave


analog_modem = serial.Serial()
analog_modem.port = "/dev/ttyACM0"
analog_modem.baudrate = 57600 #9600
analog_modem.bytesize = serial.EIGHTBITS #number of bits per bytes
analog_modem.parity = serial.PARITY_NONE #set parity check: no parity
analog_modem.stopbits = serial.STOPBITS_ONE #number of stop bits
analog_modem.timeout = 3            #non-block read
analog_modem.xonxoff = False     #disable software flow control
analog_modem.rtscts = False     #disable hardware (RTS/CTS) flow control
analog_modem.dsrdtr = False      #disable hardware (DSR/DTR) flow control
analog_modem.writeTimeout = 3     #timeout for write


# Used in global event listener
disable_modem_event_listener = True
RINGS_BEFORE_AUTO_ANSWER = 2


#=================================================================
# Initialize Modem
#=================================================================
def init_modem_settings():
	# Opean Serial Port
	try:
		analog_modem.open()
	except:
		print "Error: Unable to open the Serial Port."
		sys.exit()


	# Initialize
	try:
		analog_modem.flushInput()
		analog_modem.flushOutput()

		# Test Modem connection, using basic AT command.
		if not exec_AT_cmd("AT"):
			print "Error: Unable to access the Modem"

		# reset to factory default.
		if not exec_AT_cmd("ATZ3"):
			print "Error: Unable reset to factory default"			
			
		# Display result codes in verbose form 	
		if not exec_AT_cmd("ATV1"):
			print "Error: Unable set response in verbose form"	

		# Enable Command Echo Mode.
		if not exec_AT_cmd("ATE1"):
			print "Error: Failed to enable Command Echo Mode"		

		# Enable formatted caller report.
		if not exec_AT_cmd("AT+VCID=1"):
			print "Error: Failed to enable formatted caller report."

		# Enable formatted caller report.
		#if not exec_AT_cmd("AT+FCLASS=8"):
		#	print "Error: Failed to enable formatted caller report."


		analog_modem.flushInput()
		analog_modem.flushOutput()

	except:
		print "Error: unable to Initialize the Modem"
		sys.exit()
#=================================================================



#=================================================================
# Execute AT Commands on the Modem
#=================================================================
def exec_AT_cmd(modem_AT_cmd):
	try:
		global disable_modem_event_listener
		disable_modem_event_listener = True

		cmd = modem_AT_cmd + "\r"
		analog_modem.write(cmd.encode())

		modem_response = analog_modem.readline()
		modem_response = modem_response + analog_modem.readline()

		print modem_response

		disable_modem_event_listener = False

		if ((modem_AT_cmd == "AT+VTX") or (modem_AT_cmd == "AT+VRX")) and ("CONNECT" in modem_response):
			# modem in TAD mode
			return True
		elif "OK" in modem_response:
			# Successful command execution
			return True
		else:
			# Failed command execution
			return False

	except:
		disable_modem_event_listener = False
		print "Error: unable to write AT command to the modem..."
		return()
#=================================================================



#=================================================================
# Recover Serial Port
#=================================================================
def recover_from_error():
	try:
		exec_AT_cmd("ATH")
	except:
		pass

	analog_modem.close()
	init_modem_settings()

	try:
		analog_modem.close()
	except:
		pass

	try:
		init_modem_settings()
	except:
		pass

	try:
		exec_AT_cmd("ATH")
	except:
		pass

#=================================================================



#=================================================================
# Play wav file
#=================================================================
def play_audio():
	print "Play Audio Msg - Start"

	# Enter Voice Mode
	if not exec_AT_cmd("AT+FCLASS=8"):
		print "Error: Failed to put modem into voice mode."
		return

	# Compression Method and Sampling Rate Specifications
	# Compression Method: 8-bit linear / Sampling Rate: 8000MHz
	if not exec_AT_cmd("AT+VSM=128,8000"):
		print "Error: Failed to set compression method and sampling rate specifications."
		return

	# Put modem into TAD Mode
	if not exec_AT_cmd("AT+VLS=1"):
		print "Error: Unable put modem into TAD mode."
		return

	# Put modem into TAD Mode
	if not exec_AT_cmd("AT+VTX"):
		print "Error: Unable put modem into TAD mode."
		return

	time.sleep(1)

	# Play Audio File

	global disable_modem_event_listener
	disable_modem_event_listener = True

	wf = wave.open('sample.wav','rb')
	chunk = 1024

	data = wf.readframes(chunk)
	while data != '':
		analog_modem.write(data)
		data = wf.readframes(chunk)
		# You may need to change this sleep interval to smooth-out the audio
		time.sleep(.12)
	wf.close()

	#analog_modem.flushInput()
	#analog_modem.flushOutput()

	cmd = "<DLE><ETX>" + "\r"
	analog_modem.write(cmd.encode())

	# 2 Min Time Out
	timeout = time.time() + 60*2 
	while 1:
		modem_data = analog_modem.readline()
		if "OK" in modem_data:
			break
		if time.time() > timeout:
			break

	disable_modem_event_listener = False

	cmd = "ATH" + "\r"
	analog_modem.write(cmd.encode())

	print "Play Audio Msg - END"
	return
#=================================================================



#=================================================================
# Modem Data Listener
#=================================================================
def read_data():
	global disable_modem_event_listener
	ring_data = ""

	while 1:
		if not disable_modem_event_listener:
			modem_data = analog_modem.readline()
			if modem_data != "":
				print modem_data

				if "b" in modem_data.strip(chr(16)):
					print "b in modem data"
					print "b count:"
					print ((modem_data.strip(chr(16))).count("b"))
					print "total length:"
					print len(modem_data.strip(chr(16)))
					print modem_data
					
					if ((modem_data.strip(chr(16))).count("b")) == len(modem_data.strip(chr(16))):
						print "all Bs in mode data"
						#Terminate the call
						if not exec_AT_cmd("ATH"):
							print "Error: Busy Tone - Failed to terminate the call"
							print "Trying to revoer the serial port"
							recover_from_error()
						else:
							print "Busy Tone: Call Terminated"

				if "s" == modem_data.strip(chr(16)):
					#Terminate the call
					if not exec_AT_cmd("ATH"):
						print "Error: Silence - Failed to terminate the call"
						print "Trying to revoer the serial port"
						recover_from_error()
					else:
						print "Silence: Call Terminated"


				if ("RING" in modem_data) or ("DATE" in modem_data) or ("TIME" in modem_data) or ("NMBR" in modem_data):
					if "RING" in modem_data.strip(chr(16)):
						ring_data = ring_data + modem_data
						ring_count = ring_data.count("RING")
						if ring_count == 1:
							pass
							print modem_data
						elif ring_count == RINGS_BEFORE_AUTO_ANSWER:
							ring_data = ""
							play_audio()							
#=================================================================



#=================================================================
# Close the Serial Port
#=================================================================
def close_modem_port():
	try:
		exec_AT_cmd("ATH")
	except:
		pass

	try:
		if analog_modem.isOpen():
			analog_modem.close()
			print ("Serial Port closed...")
	except:
		print "Error: Unable to close the Serial Port."
		sys.exit()
#=================================================================


init_modem_settings()

#Start a new thread to listen to modem data 
data_listener_thread = threading.Thread(target=read_data)
data_listener_thread.start()


# Close the Modem Port when the program terminates
atexit.register(close_modem_port)


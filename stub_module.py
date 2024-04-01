#!/usr/local/bin/python
# Project: Turbolift: An application server for voice powered computing
# Component: Stub module
# Description:
# The stub_module provides a starting point for writing and experimenting with new
# Turbolift module development.  It connects to port 8559 (diagnostic_port), and
# you can easily add your own events within the event_loop() function.
# This code is intended to act as a starting point only.  It is _not_
# required for the operation of the ALICE application, and is for
# entertainment & experimentation purposes only!

# Current Version: 2.0
# Author: (C) Copyright 2001-2005 Rupert Scammell <rupe@sbcglobal.net>
# Date: 2005-03-18
# License: GNU General Public License

"""
This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""

import sys, os, socket, string, time

# --- Define some useful functions ---

# debug output function.  Print msg to console, and to a log file.
# This is a simplified version of the debug() used within other ALICE modules.
def debug(msg):
    msg = '[' + str(time.ctime(time.time())) + '] ' + 'stub_module' + ': ' + msg + '\n'
    print string.strip(msg)
    log_fd.write(msg)
    log_fd.flush()

# Initialize a network connection, and return a socket object when connected.
def network_init():
    connect_success = 0
    debug('network_init: Attempting to establish connection.')
    while (connect_success == 0):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.connect((eds_host, eds_port))
            connect_success = 1
            debug('network_init: Connection established.')
            return s
        except socket.error:
            debug('network_init: Connect unsuccessful.  Waiting 5 seconds before retry.')
            time.sleep(5)
            connect_success = 0

# Send data to a socket.  Call network_init() if an error occurs.
# Input: sockid, the subscript of a socket object located in sock_obj_list.
# data, data to send to the socket.
# Output: None.
def send_to_socket(data):
    global s
    send_success = 0
    while send_success == 0:
	try:
            data = data + '\n'
	    s.send(data)
	    send_success = 1
	except socket.error:
	    debug('send_to_socket: WARNING: Couldn\'t send command to server.  Reinitializing network link.')
	    s.close()
	    s = network_init()

# Things we do at initialization time.
def init_stuff():
    debug('init_stuff: ALICE stub_module started.  Have fun :)')
    send_to_socket('lcd_module: cls')
    send_to_socket('lcd_module: hide_cursor')
    send_to_socket('lcd_module: cursor 0 0')
    send_to_socket('lcd_module: out \'  Welcome to ALICE\'')
    send_to_socket('lcd_module: cursor 0 2')
    send_to_socket('lcd_module: out \'    Have fun :-)\'')

# Event loop.  Define new events in here!

def event_loop():
    while 1:
        global s

        # Watch for data coming in on the socket.
        data_in = s.recv(1024)
        mydata = string.strip(data_in)
        
        log_message = 'event_loop: incoming data (' + mydata + ')'
        debug(log_message)
        
        # If it's a blank string, this generally means the connection needs resetting.
        if (data_in == ''):
            s = network_init()

        if (mydata != ''):
            # Events defined in here.

            # A quit event.
            if (mydata == 'quit'):
                debug('event_loop: Exiting the stub module.  Goodbye!')
                send_to_socket('lcd_module: cls')
                send_to_socket('lcd_module: wrap_off')
                send_to_socket('lcd_module: out \'|--Exiting module--|\'')
                send_to_socket('lcd_module: cursor 0 1')
                send_to_socket('lcd_module: out \'|/                /|\'')
                send_to_socket('lcd_module: cursor 0 2')
                send_to_socket('lcd_module: out \'|/                /|\'')
                send_to_socket('lcd_module: cursor 0 3')
                send_to_socket('lcd_module: out \'|-----Goodbye!-----|\'')
                sys.exit(1)

            # An event to print hello, world!
            if (mydata == 'say_hello'):
                debug('  ___________________ ')
                debug(' |-------------------|')
                debug(' |** hello, world! **|')
                debug(' |                   |')
                debug(' |-------------------|')
                debug('  ------------------- ')

            # A more complex event.  Pulse a bar graph
            # back and forth on the bottom line a couple of time.
            if (mydata == 'pulse_graph'):
                debug('event_loop: Pulsing graph... Oooooo....')
                base_command = 'lcd_module: hbar 0 255 '
                start_column = 8
                end_column = 10
                length = (end_column - start_column) * 8
                row = 3

                for i in range(9):
                    while (length > 0):
                        bar_event = base_command + str(start_column)\
                                    + ' ' + str(end_column)\
                                    + ' ' + str(length)\
                                    + ' ' + str(row)
                        send_to_socket(bar_event)
                        time.sleep(0.01)
                        length = length - 1

                    start_column = start_column - 1
                    end_column = end_column + 1
                    
                    length = (end_column - start_column) * 5
                    
                
# --- Main Program ---

# Global variables.
# Our log file (for debug() )
log_fd = open('Logs/stub_module.log','a')

# EDS host and port values (for network_init() )
eds_host = '127.0.0.1'
eds_port = 8559

# Make a socket object.
s = network_init()

# Do initialization bits and pieces.
init_stuff()

# Go into the event loop
event_loop()


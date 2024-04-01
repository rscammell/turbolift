#!/usr/local/bin/python
# Project: Turbolift: An application server for voice powered computing
# Component: Loader Module
# Description:
# The loader module displays an initial LCD startup screen, and is responsible for starting
# other consumer modules.
#
# Current Version: 2.0
# Author: (C) Copyright 2001-2005 Rupert Scammell <rupe@sbcglobal.net>
# Date: 2002-05-26
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

import sys, os, socket, string, time, re, ConfigParser, thread

# Set configurations via ConfigParser for the module.
# Options list is a list of options to return.  Each item in the list is a tuple in the form:
# (section, option, coerce_flag), where section represents the config file section, option is
# the option in the section to return, and coerce_flag is one of i,f,b,s where:
# i = integer
# b = boolean
# f = float
# s = string
# The function returns a hash table that has as its top level keys section names, which have nested
# hash tables as their values.  These nested hash tables have section option names as keys, and the
# respective section option values as values.

def set_configs(config_file, options):

    # Intialize a hash table that'll contain extracted options.
    config_core = {}
    
    # Initialize ConfigParser object that will be used to get
    # basic config. data for this module.
    module_config = ConfigParser.ConfigParser()

    # Read config for this module.
    module_config.read(config_file)

    for i in range(len(options)):
        c_section = options[i][0]
        c_option = options[i][1]
        c_coerce = options[i][2]
        # Check if the section name already exists.  If not, create it
        # at the top level of the hash table.
        if (config_core.has_key(c_section) == 0):
            config_core[c_section] = {}
        if (config_core.has_key(c_section) == 1):
            # Check if the option name already exists.  If it does,
            # print a warning message, but change the value anyway.
            if (config_core[c_section].has_key(c_option) == 1):
                log_message = "set_configs: Warning.  Duplicate " + c_section + ":" + c_option + " found.  Using new value."
                debug(log_message)
            # Extract data from config into hash table, doing appropriate coercions based on c_coerce flag.
            if (c_coerce == 'i'):
                config_core[c_section][c_option] = module_config.getint(c_section, c_option)
            if (c_coerce == 's'):
                config_core[c_section][c_option] = module_config.get(c_section, c_option)
            if (c_coerce == 'b'):
                config_core[c_section][c_option] = module_config.getboolean(c_section, c_option)
            if (c_coerce == 'f'):
                config_core[c_section][c_option] = module_config.getfloat(c_section, c_option)
    # Return a hash table containing the information.
    return config_core

# debug output function.
def debug(msg):
    msg = '[' + str(time.ctime(time.time())) + '] ' + 'loader_module' + ': ' + msg + '\n'
    if (config_data['loader_module']['debug_flag'] == 1):
        print string.strip(msg)
    if (config_data['loader_module']['log_messages'] == 1):
        log_fd.write(msg)
        log_fd.flush()
        
# Client-side network initialization.  Attempts to connect to
# host config_data['lcd_module']['eds_host'],
# port config_data['lcd_module']['eds_port].
# If connect is successful, returns a socket object.
# If unsuccessful, waits five seconds before retrying.

def network_init():
    connect_success = 0
    debug('network_init: Attempting to establish connection.')
    while (connect_success == 0):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.connect((config_data['loader_module']['eds_host'],config_data['loader_module']['eds_port']))
            connect_success = 1
            debug('network_init: Connection established.')
            return s
        except socket.error:
            debug('network_init: Connect unsuccessful.  Waiting 5 seconds before retry.')
            time.sleep(5)
            connect_success = 0

# Shutdown the server cleanly if a terminate command is received
# No input, no output.

def do_shutdown():
    debug('do_shutdown: Terminating module.')
    s.close()
    sys.exit(1)

# Send data to a socket.  Call network_init() if an error occurs.
# Input: sockid, the subscript of a socket object located in sock_obj_list.
# data, data to send to the socket.
# Output: None.

def send_to_socket(data):
    global s
    send_success = 0
    while send_success == 0:
	try:
	    s.send(data)
	    debug('send_to_socket: data sent to server.')
	    send_success = 1
	except socket.error:
	    debug('send_to_socket: WARNING: Couldn\'t send command to server.  Reinitializing network link.')
	    do_network_reinit()

def do_network_reinit():
    debug('do_network_reinit: Lost connection to EDS.  Attempting to re-obtain connection.')
    global s
    s.close()
    s = network_init()

def event_loop():
    global data_list
                                                      
    while 1:
        try:
            in_data = s.recv(1024)
            
            # Sometimes, multiple items of data will arrive together, CR separated.
            # In this case, we execute a string.split() on the returned data, and append
            # each individual item in order to the data_list, using port_list[b] as the port
            # value for each item, since they all came from the same place..

            data_sublist = string.split(in_data, '\n')

            # Executing string.strip() on a string causes the remainder of the string
            # to be returned as the last element in the list.  Almost invariably, the
            # string will be 'completely split', that is, there will be no remainder.
            # This causes string.split() to return an empty string as the last element.
            # Since we're appending each item in the list to data_list, and data_list
            # sees an empty string as being indicative of a network error, we strip it
            # before going any further.

            if (len(data_sublist) > 1):
                dslen = len(data_sublist)
                log_message = 'event_loop: data_sublist length is ' + str(dslen)
                debug(log_message)
                log_message = 'event_loop: pretrim data_sublist is: ' + str(data_sublist)
                debug(log_message)
                del data_sublist[dslen-1]
                log_message = 'event_loop: post-trim data_sublist is ' + str(data_sublist)
                debug(log_message)

            # Append each of the separated data items into data_list
            for i in range(len(data_sublist)):
                data_list.append(data_sublist[i])
                log_message = 'event_loop: separated data: ' + data_sublist[i]
                debug(log_message)

            # If the data_sublist object has a single item that's an empty string, then
            # we need to re-intialize the network connection.
            if (len(data_list) == 1 and data_list[0] == ''):
                do_network_reinit()
                data_list = []
                
            # Call process_cmd on each item in data_list until the list is empty.
            while data_list != []:
                debug(str(data_list))
                process_cmd(data_list.pop(0))
            
        except socket.error:
            debug('event_loop: A network error occured.')
            do_network_reinit()
            data_list = []

def process_cmd(data):

    start_mod = re.compile('(start_module) (.*)')
    if (data != ''):
            log_message = 'process_cmd: data: ' + data
            debug(log_message)

    # Terminate the module.
                                                      
    if (data == 'quit'):
            debug('process_cmd: closing connection.')
            do_shutdown()
                                                      
    if (data != 'quit'):
        if (data == 'display_startup_banner'):
            display_startup_banner()

        if (data == 'stop_startup_banner'):
            stop_startup_banner()

        if (start_mod.search(data) != None):
            mstart = (string.strip(start_mod.search(data).group(2)),)
            thread.start_new_thread(start_module,mstart)


# Display a startup banner, using events from our part of the
# config file.

def display_startup_banner():
    debug('displaying startup banner')
    banner_list = [config_data['loader_module']['lcd_line_0'],\
                  config_data['loader_module']['lcd_line_1'],\
                  config_data['loader_module']['lcd_line_2'],\
                  config_data['loader_module']['lcd_line_3']]

    send_to_socket('lcd_module: hide_cursor\n')
    send_to_socket('lcd_module: cursor 0 0\n')
    send_to_socket('lcd_module: cls\n')
    
    for i in range(len(banner_list)):
        if (string.strip(banner_list[i]) != ''):
            cursor_com = 'lcd_module: cursor 0 ' + str(i)+ '\n'
            send_to_socket(cursor_com)
            line_event = banner_list[i] + '\n'
            send_to_socket(line_event)

# Stop displaying the startup banner.  Clear the screen.
def stop_startup_banner():
    debug('stopping startup banner')
    send_to_socket('lcd_module: marq_off\n')
    send_to_socket('lcd_module: stop_display_clock\n')
    send_to_socket('lcd_module: cls\n')

# Start a module in a new thread.
def start_module(module_name):
    stop_startup_banner()
    log_message = 'Starting ' + module_name
    debug(log_message)
    top_lcd_line = 'lcd_module: out \'   Starting Module\'\n'
    middle_lcd_line = 'lcd_module: out \'' + module_name + '\'\n'
    send_to_socket(top_lcd_line)
    send_to_socket('lcd_module: cursor 0 2\n')
    send_to_socket(middle_lcd_line)
    time.sleep(3)
    real_module_name = module_name + '.py'
    start_cmd = 'python ' + real_module_name
    if (os.path.isfile(real_module_name)):
        try:
            os.system(start_cmd)
        except:
            log_message = 'WARNING: Unable to start module ' + module_name
            debug(log_message)

    if (os.path.isfile(real_module_name) == 0):
        log_message = 'WARNING: module ' + module_name + ' was not found.'
        debug(log_message)

    # When the module eventually gets closed, re-display the startup banner.
    stop_startup_banner()
    send_to_socket('lcd_module: cls\n')
    top_lcd_line = 'lcd_module: out \'   Stopping Module\'\n'
    middle_lcd_line = 'lcd_module: out \'' + module_name + '\'\n'
    send_to_socket(top_lcd_line)
    send_to_socket('lcd_module: cursor 0 2\n')
    send_to_socket(middle_lcd_line)
    time.sleep(3)
    display_startup_banner()

# -- MAIN PROGRAM --

# Initialization.
print 'init: Starting Loader module.'
print 'init: Beginning initialization.'

# Options to retrieve from config file:
config_options = [('loader_module', 'debug_flag', 'b'), \
                  ('loader_module', 'log_messages', 'b'), \
                  ('loader_module', 'eds_port', 'i'), \
                  ('loader_module', 'eds_host', 's'), \
                  ('loader_module', 'log_file', 's'), \
                  ('loader_module', 'lcd_line_0', 's'), \
                  ('loader_module', 'lcd_line_1', 's'), \
                  ('loader_module', 'lcd_line_2', 's'), \
                  ('loader_module', 'lcd_line_3', 's')]

# Get configuration information
config_fn = config_fn = 'Config/alice.config'
log_message = 'init: Using config file ' + config_fn
print log_message

config_data = set_configs(config_fn, config_options)

# Open a log file, if this feature has been enabled.
print 'init: Opening log file.'
if (config_data['loader_module']['log_messages'] == 1):
    try:
        log_fd = open(config_data['loader_module']['log_file'], 'a')
    except IOError:
        log_message = 'init: WARNING: Unable to open log file at ' + config_data['loader_module']['log_file']
        print log_message
        print 'init: WARNING: Logging will occur to console only.'
        config_data['loader_module']['log_messages']  = 0

# Globally defined list of data items we need to process, used in event_loop()
data_list = []
                                                             
# Initialize the network connection, and return a global socket object.
debug('init: Connecting to event distribution server.')
s = network_init()

# Display our startup screen
time.sleep(5)
display_startup_banner()

# Enter the main event loop.
debug('init: Loader module initialization completed successfully.')
event_loop()
                                                             

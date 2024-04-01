#!/usr/local/bin/python
# Project: Turbolift: An application server for voice powered computing
# Component: LCD Client module
# Description:
# The LCD Client module receives commands and data from the Event Distribution Server, which
# it parses, then uses to display appropriate output on an LCD display, specifically, a CrystalFontz
# 634 20x4 LCD (http://www.crystalfontz.com), which is typically connected via a serial port.
#
# Current Version: 2.0
# Author: (C) Copyright 2001-2005 Rupert Scammell <rupe@sbcglobal.net>
# Date: 2005-03-12
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

import sys, socket, string, time, re, ConfigParser, pyCFontz

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
    msg = '[' + str(time.ctime(time.time())) + '] ' + 'lcd_module' + ': ' + msg + '\n'
    if (config_data['lcd_module']['debug_flag'] == 1):
        print string.strip(msg)
    if (config_data['lcd_module']['log_messages'] == 1):
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
            s.connect((config_data['lcd_module']['eds_host'],config_data['lcd_module']['eds_port']))
            connect_success = 1
            debug('network_init: Connection established.')
            return s
        except socket.error:
            debug('network_init: Connect unsuccessful.  Waiting 5 seconds before retry.')
            time.sleep(5)
            connect_success = 0

# Establish a connection with the LCD hardware.
# Input to the function consists of two device names,
# a primary (device), and a secondary (second_device),
# that will be used in case the first device is unavailable.
# Output is an LCD object, as defined in the pyCFontz module.

def lcd_init(device, second_device):
    try:
        lcd = pyCFontz.CFontz(device)
        lcd.cls()
        log_message = 'lcd_init: Attempting connection to LCD hardware on ' + device
        debug(log_message)
        debug('lcd_init: LCD hardware initialization successful.')
        return lcd
    except:
        log_message = 'lcd_init: LCD hardware initialization failed on device ' + device + ' . Using ' + second_device
        debug(log_message)
        try:
            lcd = pyCFontz.CFontz(second_device)
            lcd.cls()
            debug('lcd_init: LCD initialization successful on second device.')
            return lcd
        except:
            log_message = 'lcd_init: LCD initialization failed on ' + second_device + 'Ending program.'
            sys.exit(1)

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

def show_clock(dline=0):
    lcd.hide_cursor()
    while (clock_can_display == 1):
        lcd.cursor(0, int(dline))
        lcd.out(str(time.ctime(time.time()))[:-4])
        time.sleep(1)

# process_cmd parses data received via event_loop(), and does the
# actual work of controlling the LCD screen, through API calls to
# the pyCFontz module.
# Input consists of commands to be parsed.
# No explicit return data is provided, however output to the LCD screen,
# and debug() entries which potentially provide output to the console and/or
# a file based log, occur.

def process_cmd(data):

    global clock_can_display
    
    # Regular expressions used by if clauses below for
    # parsing and extracting data:
    
    o_parse = re.compile("(out )'(.*)'[^']*$")
    cloc_parse = re.compile("(cursor )([0-9]+) ([0-9]+)")
    sc_parse = re.compile("(set_contrast )([0-9]+)")
    set_marq = re.compile("(set_marq )'(.*)'[^']*$")
    marq_on = re.compile("(marq_on )([0-9]+) ([0-9]+) ([0-9]+)")
    cline_parse = re.compile("(cline )([0-9]+) '(.*)'[^']*$")
    hbar_parse = re.compile("(hbar )([0-9]+) ([0-9]+) ([0-9]+) ([0-9]+) ([0-9]+) ([0-9]+)")
    clock_parse = re.compile("(start_display_clock) ([0-9]*)")                                                
    # Special regex for parsing ping events:
    ping_parse = re.compile("(ping )\[(.+)\]$")
    
    data = string.strip(data)

    if (data != ''):
            log_message = 'process_cmd: data: ' + data
            debug(log_message)

    # Terminate the module.
                                                      
    if (data == 'quit'):
            debug('process_cmd: closing connection.')
            do_shutdown()
                                                      
    if (data != 'quit'):

            # Send a CRLF
            if (data == 'crlf'):
                    lcd.crlf()

            # Clear the LCD screen
            if (data == 'cls'):
                    lcd.cls()

            # Print out text to the LCD
            if (o_parse.search(data) != None):
                    lcd.out(o_parse.search(data).group(2))

            # Hide the contents of the display
            if (data == 'hide_disp'):
                    lcd.hide_disp()

            # Restore the contents of the display
            if (data == 'restore_disp'):
                    lcd.restore_disp()

            # Hide LCD cursor
            if (data == 'hide_cursor'):
                    lcd.hide_cursor()

            # Use underline style cursor
            if (data == 'uline_cursor'):
                    lcd.uline_cursor()

            # Use block style cursor
            if (data == 'block_cursor'):
                    lcd.block_cursor()

            # Use inverted block cursor
            if (data == 'invert_block_cursor'):
                    lcd.invert_block_cursor()

            # Backspace
            if (data == 'bs' or data == 'backspace'):
                    lcd.backspace()

            # Linefeed
            if (data == 'lf'):
                    lcd.lf()

            # Destructive delete.
            if (data == 'del' or data == 'delete'):
                    lcd.delete()

            # Carriage return
            if (data == 'cr'):
                    lcd.cr()

            # Set cursor position on LCD to cols, row
            if (cloc_parse.search(data) != None):
                    cols = int(cloc_parse.search(data).group(2))
                    row = int(cloc_parse.search(data).group(3))
                    lcd.cursor(cols, row)

            # Turn on the backlight
            if (data == 'backlight_on'):
                    lcd.backlight_on()

            # Turn off the backlight
            if (data == 'backlight_off'):
                    lcd.backlight_off()

            # Set LCD contrast level to a value.
            if (sc_parse.search(data) != None):
                    sc_level = int(sc_parse.search(data).group(2))
                    lcd.set_contrast(sc_level)

            # Incrementally increase contrast
            if (data == 'contrastup'):
                    lcd.contrastup()

            # Incrementally decrease contrast
            if (data == 'contrastdown'):
                    lcd.contrastdown()

            # Turn up backlight level
            if (data == 'backlight_up'):
                    lcd.backlightup()

            # Turn down backlight level
            if (data == 'backlight_down'):
                    lcd.backlight_down()

            # Scroll a created marquee
            if (data == 'scroll_on'):
                    lcd.scroll_on()

            # Stop scrolling a created marquee
            if (data == 'scroll_off'):
                    lcd.scroll_off()

            # Set string in the marquee buffer.
            if (set_marq.search(data) != None):
                    debug('process_cmd: set_marq called.')
                    mdata = str(set_marq.search(data).group(2))
                    lcd.set_marq(mdata)

            if (marq_on.search(data) != None):
                    debug('process_cmd: marq_on called.')
                    mdata = marq_on.search(data)
                    line_val = int(mdata.group(2))
                    step_val = int(mdata.group(3))
                    speed_val = int(mdata.group(4))
                    lcd.marq_on(line_val, step_val, speed_val)

            # Stop the marquee.
            if (data == 'marq_off'):
                lcd.marq_off()

            # New events from here down.
            # Turn on line wrap for lines being written to the LCD.
            if (data == 'wrap_on'):
                    lcd.wrap_on()

            # Turn off line wrap for lines being written to the LCD
            if (data == 'wrap_off'):
                    lcd.wrap_off()

            # Reboot the firmware (very rarely needed)
            if (data == 'reboot'):
                    lcd.reboot()

            # Move cursor up relative to current position
            if (data == 'up'):
                    lcd.up()

            # Move cursor down relative to current position
            if (data == 'down'):
                    lcd.down()

            # Move cursor left of current position
            if (data == 'left'):
                    lcd.left()

            # Move cursor right of current position
            if (data == 'right'):
                    lcd.right()


            # Write a line of centered text to the specified line.
            if (cline_parse.search(data) != None):
                    clinedata = cline_parse.search(data)
                    linenum = int(clinedata.group(2))
                    linetext = clinedata.group(3)
                    lcd.cline(linenum, linetext)
                    log_message = 'process_cmd: centered text (' + linetext + ') written to line ' + str(linenum)
                    debug(log_message)

            # Display a bar graph.
            if (hbar_parse.search(data) != None):
                    hbardata = hbar_parse.search(data)
                    graph_index = int(hbardata.group(2))
                    style = int(hbardata.group(3))
                    start_col = int(hbardata.group(4))
                    end_col = int(hbardata.group(5))
                    length = int(hbardata.group(6))
                    row = int(hbardata.group(7))
                    lcd.hbar(graph_index, style, start_col, end_col, length, row)

            # Display the system date.
            if (data == 'display_sysdate'):
                debug('process_cmd: displaying system date')
                lcd.out(str(time.ctime(time.time())))

            # Display a digital clock on the LCD, updated once per second.                                          
            if (clock_parse.search(data) != None):
                debug('process_cmd: displaying clock.')
                if (clock_parse.search(data).group(2) != None):
                    dline = int(clock_parse.search(data).group(2))
                    debug(str(dline))
                else:
                    dline = 0                                  
                clock_can_display = 1                                      
                try:
                    import thread
                    thread.start_new_thread(show_clock, (dline,))
                except ImportError:
                    debug('WARNING: Unable to create thread for clock.')

            # Stop displaying any previously started digital clock.
            if (data == 'stop_display_clock'):
                debug("process_cmd: stopping clock display.")                                      
                clock_can_display = 0                                      
                lcd.cls()
                                                      
            # Display seconds since the epoch (1970-01-01)
            if (data == 'display_epoch'):
                debug('process_cmd: displaying epoch second value')
                lcd.out(str(time.time()))                                     
                                                      
            # Send back a pong response, along with our module's name,
            # in response to any ping events.                                          
            ping_parse_r = ping_parse.search(data)
            if (ping_parse_r != None):
                debug('process_cmd: got ping request.')
                ping_response = ping_parse_r.group(2) + ': pong [lcd_module]\n'
                send_to_socket(ping_response)
                                                      
                
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
            

# -- MAIN PROGRAM --

# Initialization.
print 'init: Starting LCD display module.'
print 'init: Beginning initialization.'

# Options to retrieve from config file:
config_options = [('lcd_module', 'debug_flag', 'b'), \
                  ('lcd_module', 'log_messages', 'b'), \
                  ('lcd_module', 'eds_port', 'i'), \
                  ('lcd_module', 'eds_host', 's'), \
                  ('lcd_module', 'log_file', 's'), \
                  ('lcd_module', 'lcd_device', 's'), \
                  ('lcd_module', 'second_lcd_device', 's')]

# Get configuration information
config_fn = config_fn = 'Config/alice.config'
log_message = 'init: Using config file ' + config_fn
print log_message

config_data = set_configs(config_fn, config_options)

# Open a log file, if this feature has been enabled.
print 'init: Opening log file.'
if (config_data['lcd_module']['log_messages'] == 1):
    try:
        log_fd = open(config_data['lcd_module']['log_file'], 'a')
    except IOError:
        log_message = 'init: WARNING: Unable to open log file at ' + config_data['lcd_module']['log_file']
        print log_message
        print 'init: WARNING: Logging will occur to console only.'
        config_data['lcd_module']['log_messages']  = 0

# Initialize the LCD device, and return a global LCD object.
lcd = lcd_init(config_data['lcd_module']['lcd_device'], config_data['lcd_module']['second_lcd_device'])

# Globally defined list of data items we need to process, used in event_loop()
data_list = []
                                                             
# Initialize the network connection, and return a global socket object.
debug('init: Connecting to event distribution server.')
s = network_init()

# Set the clock display flag to 1, initially.
clock_can_display = 1

# Enter the main event loop.
debug('init: LCD module initialization completed successfully.')
event_loop()
                                                             

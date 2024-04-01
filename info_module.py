#!/usr/local/bin/python
# Project: Turbolift: An application server for voice powered computing
# Component: Information module
# Description:
# The information module is intended as a general purpose 'catch all' module
# that's capable of providing responses to informational requests by the user.
# Requests might consist of asking the current time, day of the week, for the
# weather, news headlines, etc.
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

import sys, os, socket, string, time, re, ConfigParser, fileinput, urllib
import formatter,StringIO,htmllib

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
    msg = '[' + str(time.ctime(time.time())) + '] ' + 'info_module' + ': ' + msg + '\n'
    if (config_data['info_module']['debug_flag'] == 1):
        print string.strip(msg)
    if (config_data['info_module']['log_messages'] == 1):
        log_fd.write(msg)
        log_fd.flush()

# Client-side network initialization.  Attempts to connect to
# host config_data['info_module']['eds_host'],
# port config_data['info_module']['eds_port].
# If connect is successful, returns a socket object.
# If unsuccessful, waits five seconds before retrying.

def network_init():
    connect_success = 0
    debug('network_init: Attempting to establish connection.')
    while (connect_success == 0):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.connect((config_data['info_module']['eds_host'],config_data['info_module']['eds_port']))
            connect_success = 1
            debug('network_init: Connection established.')
            return s
        except socket.error:
            debug('network_init: Connect unsuccessful.  Waiting 5 seconds before retry.')
            time.sleep(5)
            connect_success = 0

# Input: a data string received on a socket.
# Output: a list of events to be executed.

def separate_data(in_data):
    data_list = []
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

    return data_list

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
	    s.close()
	    s = network_init()

def do_network_reinit():
    debug('do_network_reinit: Lost connection to EDS.  Attempting to re-obtain connection.')
    global s
    s.close()
    s = network_init()

    
def process_cmd(data):
    # Regular expressions for processing events.
    read_channel = re.compile('read_channel (.*)')
    set_reminder = re.compile('set_reminder (.*)')
    # Special regex for parsing ping events.
    ping_parse = re.compile("(ping )\[(.+)\]$")

    if (data == 'read_time'):
        debug('process_cmd: reading the time.')
        time_string = time.strftime("%A, %B %d, %I %M %p, %Y", time.localtime(time.time())) + "\n"
        send_string = "speechio_module: speech_out: " + time_string
        send_to_socket(send_string)


    if (read_channel.search(data) != None):
        debug('process_cmd: trying to read data from channel..')
        channel_name = read_channel.search(data).group(1)
        intro_msg = 'speechio_module: speech_out: Please wait.  Getting information from ' + channel_name + '\n'
        send_to_socket(intro_msg)
        time.sleep(3)

        # Build the config file variable name dynamically based on channel name,
        # and try to grab the data source for the channel.
        channel_config_name = "channel_" + string.strip(channel_name)
        log_text = 'process_cmd: channel config name is ' + channel_config_name
        debug(log_text)
        options_list = [('info_module', channel_config_name, 's'), ('info_module', 'cache_dir', 's')]
        channel_info = set_configs(config_fn, options_list)
        try:
            channel_data_source = channel_info['info_module'][channel_config_name]
            log_text = 'process_cmd: channel data source is ' + channel_data_source
            debug(log_text)
        except:
            debug('process_cmd: WARNING: unable to extract data source for channel.')
            send_to_socket('speechio_module: speech_out: I\'m sorry.  I was unable to find a data source for this channel.\n')
            return

        # Channel data sources are URLs.  However, if a source name is 'latest', we use the rules below
        # to construct an URL on a channel-specific basis.
        # Add your own rules here. 
        if (channel_data_source == 'latest'):
            
            # Salon Premium (http://www.salon.com)
            if (channel_name == 'salon'):
                the_time = time.localtime(time.time())
                yearval = time.strftime('%Y', the_time)
                monthval = time.strftime('%m', the_time)
                dayval = time.strftime('%d', the_time)

                channel_data_source = 'http://www.salon.com/premium/downloads/Salon_' + yearval + monthval + dayval + '.html'
                log_message = 'process_cmd: canonical data source is ' + channel_data_source
                debug(log_message)

        # Now grab the data from the data source URL.
        channel_file, h = urllib.urlretrieve(channel_data_source)
        text = open(channel_file, 'r').read()
        send_to_socket('speechio_module: speech_out: Channel data has been retrieved.  Please stand by.\n')
        html_parser = MyParser()
        html_parser.feed(text)
        html_parser.close()
        text = string.replace(html_parser.gettext(), '\xa0', ' ')
        debug(text)
        text_lines = string.split(text, '\n')
        print text_lines

        # Post process retrieved text in order to make speech flow clearer.
        tt_from = '[]{}^*()<>/\\+=_#|~-@'
        tt_to = ' ' * len(tt_from)
        trans_table = string.maketrans(tt_from, tt_to)
        text_start = 0
        for i in range(len(text_lines)):
             current_line = string.strip(text_lines[i])
             current_line = string.translate(current_line, trans_table)
             if (len(current_line) > 70):
                 text_start = 1
             if (current_line != '' and text_start == 1):
                 log_message = 'process_cmd: channel line: ' + current_line
                 debug(log_message)
                 speak_line = 'speechio_module: speech_out: ' + current_line + '\n'
                 send_to_socket(speak_line)
                 time.sleep(0.3)

    # Stub code for reminder function.
    if (set_reminder.search(data) != None):
        reminder_data = set_reminder.search(data).group(1)

    # Exit the module.
    if (data == 'quit'):
        do_shutdown()

    # Return a pong response to a ping request.
    ping_parse_r = ping_parse.search(data)
    if (ping_parse_r != None):
        debug('process_cmd: got ping request.')
        ping_response = ping_parse_r.group(2) + ': pong [info_module]\n'
        send_to_socket(ping_response)

def do_shutdown():
    global s
    debug('do_shutdown: Disconnecting from EDS.')
    s.close()
    debug('do_shutdown: info_module terminated.')
    sys.exit(1)
    
def event_handler():
    global data_list
                                                      
    while 1:
        try:
            in_data = s.recv(1024)
            
            # Sometimes, multiple items of data will arrive together, CR separated.
            # In this case, we execute a string.split() on the returned data, and append
            # each individual item in order to the data_list, using port_list[b] as the port
            # value for each item, since they all came from the same place..

            data_sublist = separate_data(in_data)

            # If the data_sublist object has a single item that's an empty string, then
            # we need to re-intialize the network connection.
            if (len(data_sublist) == 1 and data_sublist[0] == ''):
                do_network_reinit()
                data_sublist = []
                
            # Call process_cmd on each item in data_list until the list is empty.
            while data_sublist != []:
                debug(str(data_sublist))
                process_cmd(data_sublist.pop(0))
            
        except socket.error:
            debug('event_loop: A network error occured.')
            do_network_reinit()
            data_sublist = []


# Strip all HTML formatting.
class MyParser(htmllib.HTMLParser):
    def __init__(self):
        self.bodytext = StringIO.StringIO()
        writer = formatter.DumbWriter(self.bodytext)
        htmllib.HTMLParser.__init__(self,
            formatter.AbstractFormatter(writer))

    def gettext(self):
        image_tag = re.compile('(\(image\))')
        link_tag = re.compile('(\[[0-9]+\])(.*)')
        pretext = self.bodytext.getvalue()
        if (link_tag.search(pretext) != None):
            pretext = re.sub('(\[[0-9]+\])', '', pretext)
            
        if (image_tag.search(pretext) != None):
            pretext = re.sub('(\(image\))', '', pretext)

        return pretext
    
def process_html(file):
    try:
        text = open(file, "r").read()
    finally:
        urlcleanup()
    return text

# --- Initialization ---

print 'init: Information module starting up. (ALICE v1.00b).'
print 'init: Beginning initialization.'

# Options to retrieve from config file:
config_options = [('info_module', 'debug_flag', 'b'), \
                  ('info_module', 'log_messages', 'b'), \
                  ('info_module', 'log_file', 's'), \
                  ('info_module', 'eds_port', 'i'), \
                  ('info_module', 'eds_host', 's')]

# Config file to use:
config_fn = 'Config/alice.config'
log_message = 'init: Using config file ' + config_fn
print log_message

# Get configuration information
config_data = set_configs(config_fn, config_options)

# Open a log file, if this feature has been enabled.
print 'init: Opening log file.'
if (config_data['info_module']['log_messages'] == 1):
    try:
        log_fd = open(config_data['info_module']['log_file'], 'a')
    except IOError:
        log_message = 'init: WARNING: Unable to open log file at ' + config_data['info_module']['log_file']
        print log_message
        print 'init: WARNING: Logging will occur to console only.'
        config_data['info_module']['log_messages']  = 0

# debug() log function usable below this point.

# Start networking and return a socket object.
debug('init: Connecting to event distribution server.')
s = network_init()

debug('init: Initialization completed successfully.')

# Start the event handler
event_handler()

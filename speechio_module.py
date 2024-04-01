#!/usr/local/bin/python
# Project: Turbolift: An application server for voice powered computing
# Component: Speech Input/Output Client module
# Description:
# The Speech Input/Output Client module is responsible for handling text-format speech input
# obtained from the CMU Sphinx Speech Recognition System (http://fife.speech.cs.cmu.edu/speech).
# In the future, it will also provide speech output services.
#
# Current Version: 1.00b
# Author: (C) Copyright 2001-2002 Rupert Scammell <rupe@arrow.yak.net>
# Date: 2002-02-22
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

import os, sys, socket, string, time, re, ConfigParser, pickle, speechrule, select, fileinput

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
    msg = '[' + str(time.ctime(time.time())) + '] ' + 'speechio_module' + ': ' + msg + '\n'
    if (config_data['speechio_module']['debug_flag'] == 1):
        print string.strip(msg)
    if (config_data['speechio_module']['log_messages'] == 1):
        log_fd.write(msg)
        log_fd.flush()

# Load and parse speech/command binding file.  When we recognize speech,
# we'll use this table to determine which command to pass back to the EDS.
# Input: Bind filename (from config_data)
# Output: Hash table nested within config_data (config_data['bind']), with speech text
# as keys, and command bindings as values.

def parse_bindings(bfile):
    global config_data
    # Regex to parse bfile lines.  Groups are:
    # 1: speech text
    # 2: bound command
    bfile_format = re.compile("(.*);(.*)")

    # Initialize a nested hash table.
    config_data['bind'] = {}

    # Read and parse the file data.
    try:
        for line in fileinput.input([bfile]):
            if (bfile_format.search(line) != None):
                sptext = string.strip(bfile_format.search(line).group(1))
                bound_cmd = string.strip(bfile_format.search(line).group(2))
                config_data['bind'][sptext] = bound_cmd
                log_message = 'parse_bindings: speech text: ' + sptext + ' bound to command: ' + bound_cmd
                debug(log_message)
    except IOError:
        debug('parse_bindings: WARNING: Binding attempt failed.  No bindings loaded.  Check your configuration file.')

# Generate a correctly formatted Scheme language statement
# to pass to the Festival server, in order to generate speech output.
# Input: Speech string to be passed off to Festival
# Output: Scheme statement string, with speech text encapsulated within it.
# Scheme statement takes the form (SayText "speech_string")\n , where speech_string
# is the original input string.
def gen_scheme_string(speech_str):
    scheme_str = '(SayText "' + string.strip(speech_str) + '")\n'
    return scheme_str

# Client-side network initialization.  Attempts to connect to
# the host and port provided as input.  When successful, returns
# a socket object.
# If connect is successful, returns a socket object.
# If unsuccessful, waits five seconds before retrying.
def network_init(host, port):
    connect_success = 0
    debug('network_init: Attempting to establish connection.')
    while (connect_success == 0):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.connect((host,port))
            connect_success = 1
            debug('Connecting to ' + str(host) + ':' + str(port))
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
def send_to_socket(sockid, data):
    global sock_obj_list
    send_success = 0

    while send_success == 0:
        try:
            sock_obj_list[sockid].send(data)
            debug('send_to_socket: data sent to server.')
            send_success = 1
        except socket.error:
            debug('send_to_socket: WARNING: Couldn\'t send command to server.  Reinitializing network link.')
            sock_obj_list[sockid].close()
            sock_obj_list[sockid] = network_init(host_list[sockid], port_list[sockid])


# Do data separation task.  Take in a CR separated list of items, and return a list of tokens.
def do_data_sep(in_data):
    # Empty tokenization list -
    tok_data_list = []
    
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
        tok_data_list.append(data_sublist[i])
        log_message = 'event_loop: separated data: ' + data_sublist[i]
        debug(log_message)
    return tok_data_list

# Shut down the module.  Iteratively close sockets existent
# within sock_obj_list, and call sys.exit(1) to accomplish
# final termination.
# Inputs: none
# Outputs: none (terminates this module).

def do_shutdown():
    global sock_obj_list
    debug('do_shutdown: closing sockets in sock_obj_list.')
    for i in range(len(sock_obj_list)):
        sock_obj_list[i].close()
    debug('do_shutdown: speech I/O module terminated.')
    sys.exit(1)

# -- INITIALIZATION --

print 'init: Speech I/O module starting up. (ALICE v1.00b)'
print 'init: Beginning initialization.'

# Location of config file
config_fn = "Config/alice.config"

# Options to retrieve from config file:
config_options = [('speechio_module', 'debug_flag', 'b'), \
                  ('speechio_module', 'log_messages', 'b'), \
                  ('speechio_module', 'eds_port', 'i'), \
                  ('speechio_module', 'eds_host', 's'), \
                  ('speechio_module', 'sphinx_host', 's'), \
                  ('speechio_module', 'sphinx_port', 'i'), \
                  ('speechio_module', 'festival_host', 's'), \
                  ('speechio_module', 'festival_port', 'i'), \
                  ('speechio_module', 'log_file', 's'), \
                  ('speechio_module', 'speech_data_file', 's'), \
                  ('speechio_module', 'vocab_file', 's'), \
                  ('speechio_module', 'cs_bindfile', 's'), \
                  ('speechio_module', 'learn_threshold', 'i')]


# Get configuration information
config_data = set_configs(config_fn, config_options)
log_message = 'init: Using config file ' + config_fn
print log_message

# Open a log file, if this feature has been enabled.
print 'init: Opening log file.'
if (config_data['speechio_module']['log_messages'] == 1):
    try:
        log_fd = open(config_data['speechio_module']['log_file'], 'a')
    except IOError:
        log_message = 'init: WARNING: Unable to open log file at ' + config_data['speechio_module']['log_file']
        print log_message
        print 'init: WARNING: Logging will occur to console only.'
        config_data['speechio_module']['log_messages']  = 0

# Create an empty file descriptor list
fileno_list = []

# Create an empty list of socket objects.
sock_obj_list = []

# Create a polling object, which we'll register sockets with.
poll_obj = select.poll()

# Create a port list
port_list = [config_data['speechio_module']['eds_port'], \
            config_data['speechio_module']['sphinx_port'], \
            config_data['speechio_module']['festival_port']]

# Create a host list
host_list = [config_data['speechio_module']['eds_host'], \
            config_data['speechio_module']['sphinx_host'], \
            config_data['speechio_module']['festival_host']]

# Number of connections to make
num_sockets = len(port_list)

# Create socket objects for each port in host_list and port_list, using the
# generalized network_init() call above.  This returns a socket object, when
# successful, which we then append to sock_obj_list, our list of sockets.
for i in range(num_sockets):
    log_message = 'Connecting to ' + str(host_list[i]) + ":" + str(port_list[i])
    debug(log_message)
    s = network_init(host_list[i], port_list[i])
    sock_obj_list.append(s)

    # Append the file descriptor to fileno_list
    fileno_list.append(sock_obj_list[i].fileno())

    # Register the socket with the polling object.
    # The if condition inserted below is a quick and dirty way of dealing with
    # useless output returned by the Festival server, that was accidentally
    # getting added by speechrule to the try_list.
    # It does this by keeping the socket for Festival 'in place' in sock_obj_list,
    # but doesn't register it with the poll object.
    # All other socket objects (currently EDS and the Sphinx servers) do get registered,
    # though.
    if (i != 2):
        poll_obj.register(sock_obj_list[i], 3)

# Load the speech text / command bindings into the config_data['bind'] hash table.
parse_bindings(config_data['speechio_module']['cs_bindfile'])

# For diagnostic tests, we sometimes want to have speech input text arrive from the EDS socket connection.
# Since data from this channel arrives with a module name attached, we use the following regex to strip
# that info away, so only the plaintext speech remains.
# Group 1: speech text
eds_speech_strip = re.compile('speech_in: (.*)')

# Speech output (i.e. text we must synthesize) arrives via the EDS socket connection also,
# and gets sent to the Festival server, which does the actual work of synthesizing the text.
# We use this regex to detect speech text requiring synthesis.
# Group 1: speech text to say.
eds_speech_out = re.compile('speech_out: (.*)')

# Send raw Scheme statements to Festival.
# Group 1: Scheme command text.
raw_scheme_cmd = re.compile('scheme_cmd: (.*)')

# Ping request.
ping_parse = re.compile("(ping )\[(.+)\]$")

# Define the acknowledgement message that'll be sent in response to any
# data from the Sphinx server.
ackmsg = "ACK\n"

# Define a variable that contains the last modification time of the speech data table,
# in epoch seconds.  Use a bogus value initally, so a resync will be forced on the first
# run through the event loop.
time_since_mod = -1

# -- MAIN EVENT LOOP --
# Code below is adapted from the event loop in the Event Distribution Server,
# with slight modifications for client-side operation.

while 1:
    
    # Start with an empty list that'll contain data from
    # our sockets that have events.
    data_list = []

    # Poll for data on each of the sockets.
    debug('event_loop: Waiting for incoming events.')
    event_list = poll_obj.poll()

    log_message = 'event_loop: event_list: ' + str(event_list)
    debug(log_message)

    # Number of socket objects returned.
    event_count = len(event_list)
    log_message = 'event_loop: event_count: ' + str(event_count)
    debug(log_message)

    # Update the number of current sockets in sock_obj_list, in order
    # to ensure that the for loop below operates within the full list.    
    num_sockets = len(sock_obj_list)
    log_message = 'event_loop: ' + str(num_sockets) + ' sockets detected.'
    debug(log_message)

    # Match the file descriptor values returned by .poll() into event_list with
    # the socket that has that file descriptor value in sock_obj_list.
    # Once we know the socket, call .accept() on it, then read 1024 bytes of data from
    # it.  Then print the list of retrieved data.  Each item in the list is a two item
    # tuple in the form (port_number, retrieved_data).    
    for i in range(event_count):
        current_fd = event_list[i][0]
        log_message = 'event_loop: Operating on fd ' + str(current_fd)
        debug(log_message)
        debug(str(port_list))
        debug(str(fileno_list))
        debug(str(sock_obj_list))
        for b in range(num_sockets):
            
            if (current_fd == fileno_list[b]):

                if (event_list[i][1] == 25):
                    debug('event_loop: Preparing for clean-up.')
                    data_list.append([port_list[b], ''])

                if (event_list[i][1] == select.POLLIN):
                    debug('event_loop: Incoming data on socket.')

                    if (sock_obj_list[b] != None):
                        debug('event_loop: calling recv(1024) on socket object.')

                        # Read data from the socket.
                        # There's no guarantee of there actually being data to read on the socket,
                        # so we set the socket to be non-blocking before calling recv() on it.
                        # If there's actual data, the recv() completes successfully, and we continue on.
                        # If there's no data, a socket.error gets thrown here, which we catch,
                        # and print an informative error message.
                        # In both cases, s.setblocking(1) gets called on the socket afterwards, so it'll
                        # block on future calls.                        
                        try:
                            sock_obj_list[b].setblocking(0)
                            time.sleep(0.1)
                            data_list.append([port_list[b], sock_obj_list[b].recv(1024)])
                            sock_obj_list[b].setblocking(1)
                                
                            # If the socket we're receiving data from is the Sphinx server,
                            # we need to send back an ACK\n in order to acknowledge reception.
                            # Otherwise subsequent speech won't be sent.
                            if (port_list[b] == config_data['speechio_module']['sphinx_port']):
                                debug('event_loop: sending ackmsg to Sphinx server.')
                                sock_obj_list[b].send(ackmsg)
                                    
                        except socket.error:
                            debug('event_loop: No data to read on this socket yet.')
                            sock_obj_list[b].setblocking(1)
                    
    # Print the list of received data.
    log_message = 'event_loop: raw data received: ' + str(data_list)
    debug(log_message)
    for i in range(len(data_list)):
        log_message = 'event_loop: post-processing data item ' + str(i) + ' , contents: ' + str(data_list[i][1])
        debug(log_message)
        d_intermediate = do_data_sep(data_list[i][1])
        log_message = 'event_loop: tokenized data is: ' + str(d_intermediate)
        debug(log_message)
        log_message = 'event_loop: first item in list is - ' + str(d_intermediate[0])
        debug(log_message)
        data_list[i][1] = d_intermediate[0]
        debug(str(data_list))
        
  
    # Now iterate through each item in data_list, and use the speechrules module to
    # interpret what we received:
    for i in range(len(data_list)):
        
        # First, check to see if we even have workable data.  If it's an empty string, do cleanup.
        if (data_list[i][1] == ''):
            debug('event_loop: Connection went away.  Doing cleanup.')
            log_message = 'event_loop: data_list contents: ' + str(data_list)
            debug(log_message)
            log_message = 'event_loop: port_list contents: ' + str(port_list)
            debug(log_message)

            # Iterate through the list of sockets, looking for a match.
            for j in range(num_sockets):
                debug(str(j))
                if (data_list[i][0] == port_list[j]):

                    # Unregister the socket from the polling object.
                    debug('event_loop: Unregistering socket')
                    poll_obj.unregister(sock_obj_list[j])

                    # Close the socket.
                    debug('event_loop: Closing socket.')
                    sock_obj_list[j].close()

                    # Recreate a new socket object.
                    debug('event_loop: Recreating socket.')
                    sock_obj_list[j] = network_init(host_list[j], port_list[j])

                    # Set the updated fileno of the socket object back in fileno_list
                    debug('event_loop: Updating fileno value in fileno_list')
                    fileno_list[j] = sock_obj_list[j].fileno()
                    
                    # Remove item from data_list
                    debug('event_loop: Removing empty item from data_list')
                    del data_list[i]

                    # Re register the new socket object.
                    # We use the same logic as when the sockets were intially created here.
                    # If the port value in the list corresponds to that of the Festival
                    # server, we don't register it with the poll object, since we never
                    # care what the output it sends back is.
                    if (port_list[j] != config_data['speechio_module']['festival_port']):
                        debug('event_loop: Registering new socket object')
                        poll_obj.register(sock_obj_list[j], 3)

                    # If the socket that was cleaned up is our Sphinx (speech rec)
                    # socket, we need to send a CR when we connect.
                    if (port_list[j] == config_data['speechio_module']['sphinx_port']):
                        debug('event_loop: Sending cleanup CR to sphinx socket.')
                        send_to_socket(j, 'ACK\n')
                        
                    debug('event_loop: Cleanup done.')

                    # Break out and go onto the next event.
                    break

        # This is where the actual processing of the data we've received occurs.
        # First check to see if there's anything to actually process (i.e. data_list isn't empty)
        if (data_list != []):
            debug('event_loop: Processing speech data.')

            # -- Handle and process speech input and/or output appropriately --:

            # event_handled gets set to 1, below, if the data matches one of the regex strings.
            # If we get to the bottom with event_handled still at 0, assume that the incoming string
            # is speech text to be processed via the speechrule module.
            event_handled = 0

            # soundcheck is an event that allows the user to confirm that speech input and output
            # is in fact functional.
            if (data_list[i][1] == 'soundcheck'):
                debug('event_loop: soundcheck event received.')
                scheme_str = gen_scheme_string('Yes, I am listening to you.')
                send_to_socket(2, scheme_str)
                event_handled = 1

            # quit causes this module to terminate.
            if (data_list[i][1] == 'quit'):
                do_shutdown()
                
            # If we get speech input text from the EDS,
            # then use the if clause below to strip the module name, leaving plain speechtext only.  If it's coming from
            # the Sphinx socket, it'll arrive as plaintext as is, so we have no need of this.
            eds_speech_strip_r = eds_speech_strip.search(data_list[i][1])
            if (eds_speech_strip_r != None):
                debug('event_loop: Speech text input from EDS (diagnostic).')
                data_list[i][1] = string.strip(eds_speech_strip_r.group(1))
                log_message = 'event_loop: output speechtext: ' + data_list[i][1]
                debug(log_message)
                event_handled = 1

            # If the data we're handling is speech output, use gen_scheme_string on it to generate a valid Scheme
            # statement, then pass it off to Festival.
            eds_speech_out_r = eds_speech_out.search(data_list[i][1])
            if (eds_speech_out_r != None):
                speech_out = eds_speech_out_r.group(1)
                scheme_str = gen_scheme_string(speech_out)
                log_message = 'event_loop: got speech text: ' + speech_out + ' for synthesis.'
                debug(log_message)
                
                # Send to Festival server:
                send_to_socket(2, scheme_str)
                event_handled = 1

            # If the data is a raw Scheme command, pass it onto to Festival server without any further munging.
            raw_scheme_cmd_r = raw_scheme_cmd.search(data_list[i][1])
            if (raw_scheme_cmd_r != None):
                debug('event_loop: Raw data for Festival server received.')
                raw_cmd = raw_scheme_cmd_r.group(1) + '\n'
                # Send to Festival server:
                send_to_socket(2, raw_cmd)
                event_handled = 1
            
            # Send back a pong response, along with our module's name,
            # in response to any ping events.                                          
            ping_parse_r = ping_parse.search(data_list[i][1])
            if (ping_parse_r != None):
                debug('process_cmd: got ping request.')
                ping_response = ping_parse_r.group(2) + ': pong [speechio_module]\n'
                send_to_socket(0, ping_response)
                event_handled = 1
                
            # If the data is speech text requiring recognition, process it appropriately.
            if (event_handled == 0 or eds_speech_strip_r != None):
                
                # This part works, but need to make speechrule calls less redundant:
                # Do speechrule intialization.

                # If the speech bindings file exists and has changed, resync against the vocab file.
                current_last_mod = os.path.getmtime(config_data['speechio_module']['vocab_file'])
                debug(str(current_last_mod))
                debug(str(time_since_mod))

                # If the modification time of the speech binding file has changed, rebuild the
                # speech data file (and migrate over all old bindings that exist in the current
                # speech data file to the new one.
                if (os.path.isfile(config_data['speechio_module']['vocab_file']) and \
                   (time_since_mod != current_last_mod)):
                    speechrule.process_init(config_data['speechio_module']['speech_data_file'],\
                                           config_data['speechio_module']['vocab_file'], 'Rebuild')
                    time_since_mod = current_last_mod
                    current_last_mod = 0

                # If there's no file, cause speechrule to create a new table of speech data.
                # If the modification times are the same (i.e the binding file hasn't changed),
                # we just use the existing speech data file, and don't do a resync here, which is
                # faster.
                if (os.path.isfile(config_data['speechio_module']['speech_data_file']) == 0 or \
                   current_last_mod == time_since_mod and \
                   current_last_mod != 0):
                    speechrule.process_init(config_data['speechio_module']['speech_data_file'],\
                                           config_data['speechio_module']['vocab_file'], 'Default')
                
                # Parse the original speechtext against the speech data file, and return a translated string.
                utt_dif = speechrule.event_loop(config_data['speechio_module']['speech_data_file'],\
						config_data['speechio_module']['vocab_file'],\
						data_list[i][1])
                if (utt_dif == None):
                    debug('event_loop: No regular expression match located.  Adding to try_list.')

                else:
                    debug('event_loop: regular expression match found.')
                    # Original utterance string:
                    utt = string.strip(data_list[i][1])
                    log_message = 'event_loop: Translated phrase: ' + utt_dif
                    debug(log_message)
                    utt_regex = string.strip(utt_dif)
                    temp_regex_ob = re.compile(utt_regex)
                    temp_so = temp_regex_ob.search(utt)

                    # This seems as good a place to mention it as any...
                    # All of the dithering about with subgroup counts in
                    # the utterance regex and event string templates below is
                    # in order to try and be as smart as possible about which events
                    # get sent to the EDS.
                    #
                    # There are cases in which the user is going to have an
                    # utterance regex that may have multiple grouped entries that
                    # need to be matched, but none of the data from any of the
                    # groups actually needs to get passed along in the event.
                    #
                    # In this case, we disregard our usual rule of thumb, which
                    # stipulates that the number of subgroups in an utterance
                    # must match the number of data substitution points within
                    # an event template, and let the static event get sent to
                    # the EDS as it is.
                    #
                    
                    # Get the base event string template.
                    sp_bound_cmd = config_data['bind'][utt_regex]

                    # Determine number of required substitution points in
                    # event string template.
                    sp_bound_cmd_groups = re.findall('\([0-9]+\)', sp_bound_cmd)
                    len_sp_bound_cmd_groups = len(sp_bound_cmd_groups)
                    log_message = 'event_loop: ' + str(len_sp_bound_cmd_groups) \
                                  + ' required substitution points found in event string template: ' \
                                  + sp_bound_cmd
                    debug(log_message)
                        
                    if (temp_so != None):
                        log_message = 'event_loop: positive match on string ' + utt + ' and regex ' + utt_regex
                        debug(log_message)
                        utt_subgroups = temp_so.groups()
                        len_utt_subgroups = len(utt_subgroups)
                    else:
                        
                        if (len_sp_bound_cmd_groups == 0):
                            debug('event_loop: event string is static.  No further processing required.')
                            # In this case, the event string has no required substitution
                            # points, so we just send the event along anyway.
                            # Setting the len of len_utt_subgroups to 0 here passes the
                            # test below, bypassing dynamic event building, but sending
                            # the command unchanged afterwards.
                            len_utt_subgroups = 0
                            
                        if (len_sp_bound_cmd_groups > 0):

                            # This is where we fall into trouble.  The event matched does
                            # have some required dynamic data, however, our utterance string
                            # doesn't match the regular expression, indicating that we can't
                            # provide what's needed.  So we throw up our hands, set len_utt_subgroups
                            # to a failure value (-1), and force the user to repeat themselves.
                            log_message = 'event_loop: WARNING: negative match on string ' + utt + ' and regex ' + utt_regex
                            debug(log_message)
                            debug('event_loop: WARNING: speechrule and speechio_module regex inconsistency.')
                            debug('event_loop: WARNING: Not sending this event to EDS.')
                            len_utt_subgroups = -1

                    # Assuming that we aren't in a failure state by now (len_utt_subgroups = -1),
                    # proceed on and build dynamic events from the template (if needed), and send
                    # the final dynamic or static event output to the EDS.
                    if (len_utt_subgroups != -1):
                        # Since a positive match was generated, we can use the returned phrase as a key
                        # reference to config_data['bind'] in order to retrieve the appropriate working command.
                        try:

                            log_message = 'event_loop: bound command for ' + utt + ' is ' + sp_bound_cmd
                            debug(log_message)

                            # This is where the dynamic event build occurs.  Static events have no
                            # need of this logic, and catch up with us below.
                            if (len_utt_subgroups > 0):
                                debug('event_loop: Building EDS event from dynamic speech information.')

                                # Now iterate through the base event template string, replacing the subgroup
                                # symbols with actual data taken from the input utterance.
                                for i in range(len_utt_subgroups):
                                    replace_substring = '(' + str(i+1) + ')'
                                    log_message = 'event_loop: sp_bound_cmd value: ' + sp_bound_cmd
                                    debug(log_message)
                                    sp_bound_cmd = string.replace(sp_bound_cmd, replace_substring, str(utt_subgroups[i]))
                                debug('event_loop: EDS event build complete.')
                                log_message = 'event_loop: Final sp_bound_cmd value: ' + sp_bound_cmd
                                debug(log_message)

                            # Tack on a CR to the sp_bound_cmd so that it'll get properly handled when sent via a socket to the EDS.
                            sp_bound_cmd = sp_bound_cmd + '\n'

                            # Send to the EDS (unless there's an inconsistency).
                            send_to_socket(0, sp_bound_cmd)

                        except KeyError:
                            log_message = 'event_loop: speech, ' + utt + ', was found in dictionary, but does not have a bound command. '
                            debug(log_message)
                

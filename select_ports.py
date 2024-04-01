#!/usr/local/bin/python
# Project: Turbolift: An application server for voice powered computing
# Component: Event distribution server module
# Description:
# The Event distribution server is the figurative heart of the Turbolift software package.
# It listens on several different ports for incoming data, and routes the data to the
# appropriate end-point.  For instance, when the MP3 player needs to do LCD output,
# it'll send a request to this module, which will route the request to LCD module, that
# will then display the required information.
#
# Current Version: 2.0
# Author: (C) Copyright 2001-2005 Rupert Scammell <rupe@arrow.yak.net>
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


import sys, socket, select, string, time, re, ConfigParser

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

def set_configs(module_config, options):

    # Intialize a hash table that'll contain extracted options.
    config_core = {}
    
    for i in range(len(options)):
        c_section = options[i][0]
        c_option = options[i][1]
        c_coerce = options[i][2]
        # Check if the section name already exists.  If not, create it
        # at the top level of the hash table.
        if (config_core.has_key(c_section) == 0):
            log_message = 'set_configs: creating new section ' + c_section
            print log_message
            config_core[c_section] = {}
        if (config_core.has_key(c_section) == 1):
            # Check if the option name already exists.  If it does,
            # print a warning message, but change the value anyway.
            if (config_core[c_section].has_key(c_option) == 1):
                log_message = "set_configs: Warning.  Duplicate " + c_section + ":" + c_option + " found.  Using new value."
                
                # We'd generally use the debug() call below instead of print, but since this is the
                # config file option loader, there's probably not much chance that the info we need
                # to use this function is available.
                print log_message
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

# Take in a config file name, and return a usable config file object.

def init_configs(config_file):
    # Initialize ConfigParser object that will be used to get
    # basic config. data for this module.
    module_config = ConfigParser.ConfigParser()

    # Read config for this module.
    module_config.read(config_file)

    # Return the config file object.
    return module_config

# Grab all options for a particular section in a specified config file.
# Inputs: module_config - Existent configuration file object (created via init_configs())
# section - section name within the config file which contains the option names to grab.
# Outputs: A list containing the option names from the section specified.

def grab_section_optlist(module_config, section):
    avail_opts = module_config.options(section)
    return avail_opts
    
# Log output function.
# Take a log message, prepend a timestamp and generating module name, and
# write to console, log file, or both, depending on configuration file
# options.
# Input: log message text
# Output: None.

def debug(msg):
    msg = '[' + str(time.ctime(time.time())) + '] ' + 'eds' + ': ' + msg + '\n'
    if (config_data['eds']['debug_flag'] == 1):
        print string.strip(msg)
    if (config_data['eds']['log_messages'] == 1):
        log_fd.write(msg)
        log_fd.flush()

# Route incoming data, based on the service definition provided by the client.
# Incoming data takes the form of a string: 'service_name: data for service' (no quotes)
# Input data to function:
# indata = incoming data (see above for format)
# returns: Nothing.  This function sends the input data to the appropriate output socket.

def route_data(indata):
    data_sep = re.compile("([^ ]*): (.*)")
    if (data_sep.search(indata) != None):
        # If the input data matches the general format described in the comment
        # above this function, break it out into a service name, which'll determine
        # how it's routed, and extract the actual data to be routed.
        # Oh, and strip any \r\n stuff that's arrived in transit.
        
        s_name = string.strip(data_sep.search(indata).group(1))
        s_data = string.strip(data_sep.search(indata).group(2))

        # This is a neat little side effect of using a hash table as the canonical
        # source for config information.  Our port assignment variable names in the
        # config file double as our service names, so we simply reference the
        # port name here by key.
        try:
            route_port = config_data[modreg_sec][s_name]
        except KeyError:
            log_message = 'route_data: WARNING: No service by name of ' + s_name + ' registered!'
            debug(log_message)
            return
        
        # Now that we know the destination port, we look through port_list for the
        # SECOND instance of the port.  The first instance is just the listening
        # socket, and the second is the actual connected port object.  If we don't
        # find it, report an error to the log.

        # We use the check flag, seen_first_instance, initially set to 0, to
        # flag whether the first instance has been seen.  If the second instance
        # instance is seen (what we're after), we increment it again, so its
        # exit value is nominally 2.  If 0 or 1, we print an error message via debug()

        seen_first_instance = 0


        for i in range(len(port_list)):
            if (route_port == port_list[i]):
                seen_first_instance = seen_first_instance + 1
            if (seen_first_instance == 2):
                port_index = i
                break

        if (seen_first_instance == 0):
            log_message = 'route_data: CRITICAL: No listening or connected sockets found for service ' + s_name + ' Very bad.'
            debug(log_message)
            
        if (seen_first_instance == 1):
            log_message = 'route_data: WARNING: Only found listener socket for service: ' + s_name
            debug(log_message)

        if (seen_first_instance == 2):
            log_message = 'route_data: Found ' + s_name + ' service instance.'
            debug(log_message)

            try:
                # We don't want this blocking.  Turn it off while we do the send, then turn it back on,
                # before another read or poll is attempted.
                sock_obj_list[i][0].setblocking(0)
                
                # Add a CR to the data before it gets sent.  Without this, the receiving socket
                # will in all likelihood not see the sent data.
                s_data = s_data + '\n'

                # Send the data to the correct socket, and print a status message.
                sock_obj_list[i][0].send(s_data)
                log_message = 'route_data: data send (' + s_data + ') successful.'
                debug(log_message)

                # Make the socket blocking again.
                sock_obj_list[i][0].setblocking(1)
                
            except:
                log_message = 'route_data: WARNING:' + 'The attempt to send data (' + s_data + ') failed.'
                debug(log_message)
                sock_obj_list[i][0].setblocking(1)
                


# -- MAIN PROGRAM --

# -- Do initialization --

# Print startup message.
print 'init: Welcome to Turbolift. Starting up...'
print 'init: Beginning initialization.'

# Config file to use.
config_file_loc = "Config/alice.config"
log_message = 'init: Using configuration file ' + config_file_loc
print log_message

# Create globally available config file object:
config_obj = init_configs(config_file_loc)
print 'init: Configuration object created.'

# Build list of static options to retrieve from config file:
config_options = [('eds', 'debug_flag', 'b'),\
                  ('eds', 'log_messages', 'b'),\
                  ('eds', 'log_file', 's')]

# Location of module registration information section
modreg_sec = 'module_reg'
print 'init: Starting module registration.'

# Get list of registered modules
rmodule_list = grab_section_optlist(config_obj, modreg_sec)
len_rmodule_list = len(rmodule_list)
log_message = 'init: ' + str(len_rmodule_list) + ' modules found.'
print log_message

# Build a list that can be passed to set_configs().  A concatenation
# of the static items already in the list, and the registered modules.
for i in range(len_rmodule_list):
    rmodule_list[i] = (modreg_sec, rmodule_list[i], 'i')

    # Append the dynamically generated config file info to the list.
    config_options.append(rmodule_list[i])

# In one pass, build the config_data hash table.
config_data = set_configs(config_obj, config_options)

# Create a blank list that holds our list of listener ports for modules to connect to.
port_list = []

# Now, using the module name keys in rmodule_list, append the port values
# to port_list, our list of ports.
for i in range(len_rmodule_list):
    c_portval = config_data[modreg_sec][rmodule_list[i][1]]
    log_message = 'init: registering module ' + rmodule_list[i][1] + ' on port ' + str(c_portval)
    print log_message
    port_list.append(c_portval)

print 'init: Module registration completed successfully.'
  
# Try to open a log file, if this feature has been enabled.

if (config_data['eds']['log_messages'] == 1):
    try:
        log_fd = open(config_data['eds']['log_file'], 'a')

    except IOError:
        log_message = 'init: WARNING: Unable to open log file at ' + config_data['eds']['log_file']
        print log_message
        print 'init: WARNING: Logging will occur to console only.'
        config_data['eds']['log_messages']  = 0
        
# Create polling object.  Poll doesn't work on all operating systems (Windows is the main culprit)
# We use an alternate technique if this call throws an AttributeError.
# alt_poll_flag is a check variable.  If set to 0, we assume that select.poll() style methods
# such as select.register() can be used safely.  If set to 1 (by way of an AttributeError),
# we assume that these methods are NOT safe, and use the poll_emulate module instead.
try:
    # Uncomment the line below to test the select.select() compatibility code.
    # raise AttributeError
    poll_obj = select.poll()
    alt_poll_flag = 0
    
except AttributeError:
    debug('init: select.poll() not implemented on this operating system.')
    try:
        import poll_emulate
        # Set alt_poll_flag to 1 so we'll use select.select compatible routines further
        # on in the program.
        alt_poll_flag = 1

        # Set up the three event lists that select.select() needs to operate.
        # input_event - list of input events
        # output_event - list of output events
        # ex_event - list of exceptional events (errors, presumably)
        input_event = []
        output_event = []
        ex_event = []
        
    except ImportError:
        debug('init: CRITICAL: You must install the Module/poll_emulate.py module in your Python module directory.  Stopping.')
        sys.exit(1)
    
# List of associated file descriptor numbers.  These match up
# by subscript with the values in port_list, above.
fileno_list = []

# List of socket objects.
sock_obj_list = []

# Number of sockets to create:
num_sockets = len(port_list)

# Print a startup message.
debug('init: Starting up EDS server.')

# Create socket objects for each port in port_list, append to sock_obj_list in
# the form of a tuple (socket object, socket type), where socket type is 0 for
# listening sockets, and 1 for connected sockets.

for i in range(num_sockets):
    log_message = 'init: Starting service on port ' + str(port_list[i])
    debug(log_message)
    try:
        sock_obj_list.append((socket.socket(socket.AF_INET, socket.SOCK_STREAM), 0))
        sock_obj_list[i][0].setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock_obj_list[i][0].bind(('',port_list[i]))
        sock_obj_list[i][0].listen(1)
        try:
            # Add the file descriptor to fileno_list.
            fileno_list.append(sock_obj_list[i][0].fileno())

            # Register the fd with poll_obj.
            if (alt_poll_flag == 0):
                poll_obj.register(sock_obj_list[i][0], 3)

            if (alt_poll_flag == 1):
                input_event, output_event, ex_event = poll_emulate.register(input_event, output_event, ex_event, sock_obj_list[i][0])

                # Debug code -- show contents of event lists used in select.select()
                # Commented out here, because it's a bit too verbose.
                #log_message = 'input_event: ' + str(input_event)
                #debug(log_message)
                #log_message = 'output_event: ' + str(output_event)
                #debug(log_message)
                #log_message = 'ex_event: ' + str(ex_event)
                #debug(log_message)
        except:
            log_message = 'init: WARNING: Unable to complete initialization of service on port ' + str(port_list[i])
            debug(log_message)
        
    except socket.error:
        log_message = 'init: WARNING: Unable to start service on port ' + str(port_list[i])
        debug(log_message)

# Check to make sure that some modules actually got started successfully.
# Die with an error if not.

if (len(fileno_list) == 0):
    debug('init: CRITICAL: 0 modules successfully registered. Terminating application.')
    sys.exit(1)

# Poll for data on each of the registered socket objects.

#log_message = 'fileno_list: ' + str(fileno_list)
#debug(log_message)
debug('init: Initialization completed successfully.')

# --- Start of event loop --- #

while 1:
    # Start with an empty list that'll contain data from
    # our sockets that have events.
    data_list = []

    # Poll for data on each of the sockets. 
    debug('event_loop: Waiting for incoming events.')
    if (alt_poll_flag == 0):
        event_list = poll_obj.poll()

    # Use an alternate method if we've already concluded that poll() isn't supported.
    if (alt_poll_flag == 1):
        debug('event_loop: Polling via select.select() method')
        event_list_temp = select.select(input_event, output_event, ex_event)
        log_message = 'event_loop: select.select() format event list: ' + str(event_list_temp)
        debug(log_message)
        debug('event_loop: Doing conversion of event list to select.poll() standard.')
        event_list = poll_emulate.convert_select_elist(event_list_temp)
                
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
        for b in range(num_sockets):
            
            if (current_fd == fileno_list[b]):
                # If the event we caught is actually incoming data, accept the connection,
                # and add the connect socket to conn_obj_list.

                if (event_list[i][1] != select.POLLIN):
                    sys.exit(1)
                
                if (event_list[i][1] == select.POLLIN):
	            # Accept the connection on the socket, and name the connection socket temporarily.
                    debug('event_loop: Incoming data on socket.')
                    
                    if (sock_obj_list[b][1] == 0):
                        debug('event_loop: Accepting new connection on socket.')

                        # Return the connected socket object from the accept() call,
                        # Append the new connected socket to the end of sock_obj_list, tagging it as a connected
                        # socket in the second subscript of the tuple. 
                        sock_obj_list.append((sock_obj_list[b][0].accept()[0], 1))
                        
                        # Debug code to display the contents of sock_obj_list.
                        # Turn on if you need this sort of verbosity while debugging.
                        #log_message = 'sock_obj_list: ' + str(sock_obj_list)
                        #debug(log_message)

                        # Append the port number of the connected socket (same as listening socket) to port_list.
                        port_list.append(port_list[b])
                        
                        # Update number of sockets.
                        num_sockets = len(sock_obj_list)
                        log_message = 'event_loop: Now there are ' + str(num_sockets) + ' sockets.'
                        debug(log_message)
                        
                        # Append the file descriptor number to the list of filenos:
                        fileno_list.append(sock_obj_list[num_sockets-1][0].fileno())
                        log_message = 'event_loop: fileno_list: ' + str(fileno_list)
                        debug(log_message)
                        
                        # Register the socket with the polling object, so that future events on it get caught.
                        # If we're using select.select(), do this in a different fashion, via use of the
                        # poll_emulate.register() command, just like we did for the listener socket above.
                        if (alt_poll_flag == 0):
                            poll_obj.register(sock_obj_list[num_sockets-1][0], 3)
                            
                        if (alt_poll_flag == 1):
                            input_event, output_event, ex_event = poll_emulate.register(input_event, output_event, ex_event, sock_obj_list[num_sockets-1][0])
                            
                            # Debug code.  Show contents of select's event lists.  Commented out
                            # for log clarity.
                            #log_message = 'input_event: ' + str(input_event)
                            #debug(log_message)
                            #log_message = 'output_event: ' + str(output_event)
                            #debug(log_message)
                            #log_message = 'ex_event: ' + str(ex_event)
                            #debug(log_message)
                            
                        # Read data from the new socket.
                        # There's no guarantee of there actually being data to read on the socket,
                        # so we set the socket to be non-blocking before calling recv() on it.
                        # If there's actual data, the recv() completes successfully, and we continue on.
                        # If there's no data, a SocketError gets thrown here, which we catch,
                        # and print an informative error message.
                        # In both cases, s.setblocking(1) gets called on the socket afterwards, so it'll
                        # block on future calls.

                        try:
                            sock_obj_list[num_sockets-1][0].setblocking(0)
                            data_list.append([port_list[b], sock_obj_list[num_sockets-1][0].recv(1024)])
                            sock_obj_list[num_sockets-1][0].setblocking(1)
                        except:
                            debug('event_loop: No data to read on this socket yet.')
                            sock_obj_list[num_sockets-1][0].setblocking(1)

                    if (sock_obj_list[b][1] == 1):
                        debug('event_loop: Data found on existing connection.')

                        if (sock_obj_list[b][0] != None):
                            debug('event_loop: Calling recv(1024) on socket object.')

                            # The code below is a bit pedantic and paranoid.
                            # Since we're getting a select.POLLIN event on an already connected socket,
                            # there should always be actual data to read.  If for some reason there's
                            # not, however, we follow the same procedure outlined in the comment,
                            # "Read data from the new socket", above.
                            
                            try:
                                sock_obj_list[b][0].setblocking(0)
                                in_data = sock_obj_list[b][0].recv(1024)

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
                                for i in range(len(data_sublist)):
                                    data_list.append([port_list[b], data_sublist[i]])
                                    log_message = 'event_loop: separated data: ' + data_sublist[i]
                                    debug(log_message)
                             
                                sock_obj_list[b][0].setblocking(1)
                            except socket.error:
                                debug('event_loop: No data to read on this socket yet.')
                                sock_obj_list[b][0].setblocking(1)
                            

                        if (data_list[i][1] == ''):
                            debug('event_loop: Connection went away. Cleaning up.')
                            # Connection went away.  Need to do cleanup.
                            # Unregister the connection socket from the polling object.
                            # If we're not using select.poll() (i.e. alt_poll_flag == 1), do
                            # an alternate routine via poll_emulate.unregister().
                            if (alt_poll_flag == 0):
                                poll_obj.unregister(sock_obj_list[b][0])
                                debug('event_loop: Socket unregistered from poll_obj...')
                            if (alt_poll_flag == 1):
                                input_event, output_event, ex_event = poll_emulate.unregister(input_event, output_event, ex_event, sock_obj_list[b][0])
                                debug('event_loop: Socket unregistered from select.select() event lists.')
                                
                            # Remove file descriptor number from fileno_list.
                            del fileno_list[b]
                            debug('event_loop: Socket removed from fileno_list.')
                            log_message = "fileno_list: " + str(fileno_list)
                            debug(log_message)
                            
                            # Remove connection from sock_obj_list, our list of sockets.
                            del sock_obj_list[b]
                            debug('event_loop: Socket removed from sock_obj_list.')
                            # Debug code:
                            #log_message = 'sock_obj_list: ' + str(sock_obj_list)
                            #debug(log_message)

                            # Remove port entry for the connection from port_list
                            del port_list[b]
                            log_message = 'event_loop: port_list: ' + str(port_list)
                            debug('event_loop: Port removed from port_list.')
                            debug(log_message)

                            # Remove empty string data from data_list
                            del data_list[i]

                            # The contents of fileno_list b changed, so there's a chance
                            # that the current 'b' subscript value for the list may no
                            # longer be valid, thereby causing an IndexError.  We reset b
                            # to 0, which results in a rescan of the list starting at the
                            # first fileno_list value.  Slightly more work, since it's
                            # potentially rescanning already examined file descriptors for
                            # a match, but it's more robust.
                            debug('event_loop: Rescanning fileno_list.')
                            log_message = 'event_loop: current b value: ' + str(b)
                            log_message2 = 'event_loop: fileno_list len: ' + str(len(fileno_list))
                            debug(log_message)
                            debug(log_message2)

                            # Recalculate number of sockets, and print a log message.
                            num_sockets = len(sock_obj_list)
                            log_message = 'event_loop: Now there are ' + str(num_sockets) + ' sockets.'
                            debug(log_message)

                            # All done here.  Executing a break brings us back into the larger for loop
                            # that this code is nested in, and we begin looking at the next event in the
                            # event_list.
                            break
                        
                            
    # Print the data received from all events.
    log_message = 'data: ' + str(data_list)
    debug(log_message)
    for i in range(len(data_list)):
        route_data(data_list[i][1])

    
    

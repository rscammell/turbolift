#!/usr/local/bin/python
# Project: Turbolift: An application server for voice powered computing 
# Component: MP3 player Client module
# Description:
# The MP3 player Client module allows the user to select and play MP3 format audio
# files.  Information about MP3 player status is displayed on an LCD screen,
# specifically, a CrystalFontz 634.  See lcd_module.py for more information.
#
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

import sys, os, socket, string, time, re, ConfigParser, whrandom, fileinput, mp3infor, thread

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
    msg = '[' + str(time.ctime(time.time())) + '] ' + 'mp3_module' + ': ' + msg + '\n'
    if (config_data['mp3_module']['debug_flag'] == 1):
        print string.strip(msg)
    if (config_data['mp3_module']['log_messages'] == 1):
        log_fd.write(msg)
        log_fd.flush()

# Client-side network initialization.  Attempts to connect to
# host config_data['mp3_module']['eds_host'],
# port config_data['mp3_module']['eds_port].
# If connect is successful, returns a socket object.
# If unsuccessful, waits five seconds before retrying.

def network_init():
    connect_success = 0
    debug('network_init: Attempting to establish connection.')
    while (connect_success == 0):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.connect((config_data['mp3_module']['eds_host'],config_data['mp3_module']['eds_port']))
            connect_success = 1
            debug('network_init: Connection established.')
            return s
        except socket.error:
            debug('network_init: Connect unsuccessful.  Waiting 5 seconds before retry.')
            time.sleep(5)
            connect_success = 0

# Load the initial playlist into a list in memory.
 
def load_playlist(pfile):
    global playlist_len
    log_message = 'load_playlist: Trying to load playlist from ' + pfile
    debug(log_message)
    try:
        p_h = open(pfile,"r")
        for line in p_h.readlines():
            songname = string.strip(line)
            a.append(songname)
        playlist_len = len(a)
        pll = str(playlist_len)
        log_message = 'load_playlist: ' + pll + ' songs loaded to playlist.'
        debug(log_message)
    except IOError:
        debug('load_playlist: WARNING: I/O Error when attempting to load playlist.  No songs loaded.')
        
    return a

# Generate a random track value to play
def gen_random_track():

    # Set this check var to 1 if we generate a random
    # track that's the last value in the playlist.  This'll
    # cause the tplay_mp3() routine to cycle us back up to the top
    # of the playlist when the song completes.
    do_return = 0

    songid = whrandom.randint(0,len(a))

    if (songid < playlist_len-1):
        block_start = songid
        block_end = block_start + 1

    if (songid == playlist_len-1):
        block_start = playlist_len - 1
        block_end=playlist_len - 1
        do_return = 1
    return songid, block_start, block_end, do_return

# RP / RS , 2001-05
# MP3 play function.  Input consists of songid, a subscript in the
# loaded playlist, which points to the actual song pathname itself.
# The function calls os.system() to start the MP3 player with the appropriate song,
# and directs stdout and stderr to /dev/null for the process.
# The function does not have a return.  It is intended to be run in the context of a thread,
# and exits when oktoplay, a globally defined bool, is set to 0 within the main event loop.

def tplay_mp3(songid):
	global oktoplay
	global randomplay
	global cursor_pos
        global block_start
        global block_end
        global song_playing
        
	killsound()
        # If this flag is set, go to the top of the playlist.
        do_return = 0

        # Check variable used if we're in random mode to generate a random track val before playing a song.
        first_time = 1
	while 1:

                # If we're in random play mode, we need to generate a random track number
                # when we first enter the while loop.  After the first time, we just get a
                # new one each time we finish playing a song.
        
                if (first_time == 1 and randomplay == 1):
                    songid, block_start, block_end, do_return = gen_random_track()
                    cursor_pos = songid
                    
                    # Write the MP3 info to the LCD.  When we're in sequential mode, the inital draw
                    # happens within the event handler, before we enter the play function.
                    draw_screen(cursor_pos, block_start, block_end)

                    # Scroll the marquee.
                    marq_sets = "marq_on " + "0 " + "6 " + "50"	
                    lcdcom(marq_sets)
                    
                    first_time = 0
                    
		song = str(a[songid])
		command = config_data['mp3_module']['mp3_player_app'] + " \"" + string.strip(song) + "\"" + " 2&>1 /dev/null"
                song_playing = 1
                os.system(command)
                song_playing = 0
                
		if (oktoplay == 0):
			return

		#Set handler check flag.
                handled = 0
                
		if (randomplay == 1):
			songid, block_start, block_end, do_return = gen_random_track()
                            
		# Bring block_start / end back in line with the new songid.

		if (randomplay == 0 and songid < playlist_len-1 and do_return == 0):
			songid = songid + 1
			block_start = block_start + 1
			block_end = block_end + 1
			handled = 1

		if (do_return == 1 and handled == 0):
                    do_return = 0
		    songid = 0
		    block_start = 0
		    block_end = 1
		    handled = 1

		if (songid == playlist_len-1 and randomplay == 0 and handled == 0):
		    block_start = playlist_len-1
		    block_end = playlist_len-1
                    do_return = 1
                    handled = 1
                    
		cursor_pos = songid
		draw_screen(cursor_pos, block_start, block_end)
                # Scroll the marquee.
                marq_sets = "marq_on " + "0 " + "6 " + "50"	
                lcdcom(marq_sets)

# The following function kills sound from the MP3 player.
# It's really embarrassing how we have to do this, but Python
# has no good method for terminating threads otherwise.

def killsound():
	global oktoplay
	oktoplay = 0
        
	os.system("killall -9 alsaplayer 2&>1 /dev/null")
	time.sleep(0.1)	
	oktoplay = 1

# Set the volume via the mixer app.  We generally expect that the
# first system argument passed to the mixer application will denote
# the desired volume, so change the concatenation of the string command
# if this is inappropriate for what you're doing.
# Input - integer volume value
# Returns: integer volume value

def volume(vol):
    volcom = config_data['mp3_module']['mixer_app'] + str(vol)
    os.system(volcom)
    log_message = 'volume: set to ' + str(vol)
    debug(log_message)
    return vol

# Take LCD display commands, and prepend the appropriate module name to the
# start of the string.  Then send the string to the EDS for processing.
# Input: LCD display command string
# Returns: None.

def lcdcom(lcd_command):
    global s
    lcd_command = config_data['mp3_module']['lcdout_mod'] + ': ' + string.strip(lcd_command) + '\n'
    log_message = 'lcdcom: data to be sent: ' + string.strip(lcd_command)
    debug(log_message)
    send_to_socket(lcd_command)
            
# Startup initialization of the LCD screen.
# - Clear screen, return cursor to 0 0
# - Hide cursor
# Inputs: none
# Returns: none

def draw_init():
    lcdcom("marq_off")
    lcdcom("cls")
    lcdcom("hide_cursor")
    draw_screen(cursor_pos, block_start, block_end)
    
# Do the actual work of drawing the interface screen, given the starting and ending
# points within the playlist.
def draw_screen(cursor_pos, block_start, block_end):
        global randomplay, rflag, current_songname, song_info, song_playing
        current_songname = ""
        next_songname = ""
        # Hash table of ID3 data for the currently selected song.
        song_info = {}
        # Hash table of ID3 data for the next song in the playlist.
        song_info2 = {}
        # Flags that get set to 1 if valid song name / artist info exists within ID3 data.
        got_id3_songinfo = 0
        got_id3_artistinfo = 0
        
        # Try to use info in the ID3 tag.
        # If we throw a NoTagError condition, 
        # we just fall back to using filename
        # information only.

        # Currently selected song.  Try to be smart about
        # ID3 tag info handling.  If we encounter existent (but blank)
        # ID3 information, try and use the smart_divide regex in order
        # to get the info.  If this fails, just --- mark the field.
        try:
            tag_handle = mp3infor.open_mp3(a[block_start])
            # Build a dictionary of the information.
            song_info = tag_handle()
            # Strip \x00 chars from ID3 information.
            if (song_info.has_key('songname')):
                song_info['songname'] = string.replace(song_info['songname'], '\x00', '')
            if (song_info.has_key('artist')):
                song_info['artist'] = string.replace(song_info['artist'], '\x00', '')
	    if (song_info.has_key('length')):
		song_info['length'] = string.replace(song_info['length'], 'L', '')
                
            if (string.strip(song_info['songname']) != ''):
                current_songname = song_info['songname']
                # Song info available, don't use smart_divide regex
                # information if artist info isn't located below,
                # and we throw a NoTagError
                got_id3_songinfo = 1
            if (string.strip(song_info['artist']) != ''):
                got_id3_artistinfo = 1
            if (string.strip(song_info['songname']) == '' or song_info.has_key('songname') == 0):
                raise NoTagError
            if (string.strip(song_info['artist']) == '' or song_info.has_key('artist') == 0):
                raise NoTagError
            
        except:	
            ret = path_strip.search(a[block_start])
            if (got_id3_songinfo == 0):
                if (ret != None):
                    current_songname = str(ret.group(2))
                if (ret == None):
                    current_songname = a[block_start]
            smart_divide_r = smart_divide.search(current_songname)
            if (smart_divide_r != None):
                debug('draw_screen: Able to do smart artist/song name division on current_songname.')
                if (got_id3_artistinfo == 0):
                    song_info['artist'] = smart_divide_r.group(1)
                if (got_id3_songinfo == 0):
                    song_info['songname'] = smart_divide_r.group(2)
                log_message = 'draw_screen: artist: ' + song_info['artist'] \
                + ' songname: ' + song_info['songname']
                debug(log_message)
                current_songname = song_info['songname']

        current_songname = string.strip(current_songname)

        # Strip any .mp3 extensions.
        if (current_songname[-4:] == '.mp3'):
            current_songname = current_songname[:-4]

        # Next song in the list.  Reuse got_id3_* tags used above.
        got_id3_songinfo = 0
        got_id3_artistinfo = 0
        
        try:
            tag_handle = mp3infor.open_mp3(a[block_end])
            # Build a dictionary of the information.
            song_info2 = tag_handle()

            # Strip \x00 chars from ID3 information.
            if (song_info2.has_key('songname')):
                song_info2['songname'] = string.replace(song_info2['songname'], '\x00', '')
            if (song_info.has_key('artist')):
                song_info2['artist'] = string.replace(song_info2['artist'], '\x00', '')
            
            if (string.strip(song_info2['songname']) != ''):
                next_songname = song_info2['songname']
                got_id3_songinfo = 1
            if (songinfo2['artist'] != ''):
                got_id3_artistinfo = 1
            if (string.strip(song_info2['songname']) == '' or song_info2.has_key('songname') == 0):
                raise NoTagError
            if (string.strip(song_info2['artist']) == '' or song_info2.has_key('artist') == 0):
                raise NoTagError

        except:
            if (got_id3_songinfo == 0):
                ret = path_strip.search(a[block_end])
                if (ret != None):
                    next_songname = str(ret.group(2))
                if (ret == None):
                    next_songname = a[block_end]
            smart_divide_r = smart_divide.search(next_songname)
            if (smart_divide_r != None):
                debug('draw_screen: Able to do smart artist/song name division on next_songname.')
                if (got_id3_artistinfo == 0):
                    song_info2['artist'] = smart_divide_r.group(1)
                if (got_id3_songinfo == 0):
                    song_info2['songname'] = smart_divide_r.group(2)
                log_message = 'draw_screen: artist: ' + song_info2['artist'] \
                + ' songname: ' + song_info2['songname']
                debug(log_message)
                next_songname = song_info2['songname']
                
        next_songname = string.strip(next_songname)
        if (cursor_pos == playlist_len - 1):
            next_songname = ' -end of playlist- '
        # Strip any .mp3 extensions.
        if (next_songname[-4:] == '.mp3'):
            next_songname = next_songname[:-4]

        # Preserve the current songname so the event loop can use
        # it to pass to the speechio_module if the user requests
        # that the song name be spoken.
        cur_fn = current_songname

        if (len(current_songname) > 40):
                current_songname = current_songname[:37] + " >"
        if (len(next_songname) > 20):
                next_songname = next_songname[:18] + " >"

        lcdcom("cls")
        lcdcom("cursor 0 0")
        # Hack around firmware weirdness that
        # wasn't clearing the marq string when
        # new one was set, resulting in 
        # garbage characters.
        lcdcom("set_marq '                      '")
        lcdcom("marq_off")

        # Set song name as a scrolling marquee.
        # The CrystalFontz 632/4 permits us to 
        # create a composite buffer consisting of
        # 20 characters of line text, and 20 characters
        # of marq text, which both get scrolled.
        stat_marq = "out '" + current_songname[:20] + "'"
        lcdcom(stat_marq)
        marq_pre = "set_marq '" + current_songname[20:] + "'"
        lcdcom(marq_pre)

        try:
            lcdcom("cursor 0 1")
            # Handle cases where we have partial ID3 tag information.
            if (song_info.has_key('length') == 1 and song_info.has_key('artist') == 1):
                debug('draw_screen: Artist name & song length located.')
                more_info = song_info['length'] + ' / ' + song_info['artist']
            if (song_info.has_key('length') == 1 and song_info.has_key('artist') == 0):
                debug('draw_screen: Song length located only.')
                more_info = song_info['length'] + ' / ' + '---'
            if (song_info.has_key('length') == 0 and song_info.has_key('artist') == 1):
                debug('draw_screen: Song artist located only.')
                more_info = '--- / ' + song_info['artist']
            if (song_info.has_key('length') == 0 and song_info.has_key('artist') == 0):
                raise KeyError
            # Trim to 20 characters, so we fit on a line.
            more_info = more_info[:20]
            disp_info = "out '" + more_info + "'"
            lcdcom(disp_info)

        except KeyError:
            # Display a blank line of artist / time info if this doesn't exist.
            lcdcom("cursor 0 1")
            disp_blank_info = "out '     --- / ---'"
            lcdcom(disp_blank_info)

        lcdcom("cursor 0 2")
        next_song = "out '" + next_songname + "'"
        lcdcom(next_song)


        # Draw the bottom status line onto the LCD, which takes the format
        # current_song/total_songs v: volume_value play_mode {seq/rnd}
        
        lcdcom("cursor 0 3")
        # The bottom status line is a little different if we're muted...
        if (is_muted == 0):
            statline = str(cursor_pos+1) + "/" + str(len(a))+ "s v: " + str(c_vol) + " " + str(rflag)
        if (is_muted == 1):
            statline = statline = str(cursor_pos+1) + "/" + str(len(a))+ "s -muted- " + str(rflag)
        drawstat = "out '" + statline + "'"
        lcdcom(drawstat)

        # Finally, if there's a song playing, we need to start the marquee scroll again.
        if (song_playing == 1):
            marq_sets = "marq_on " + "0 " + "6 " + "50"	
            lcdcom(marq_sets)

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
	    draw_init()

# Convert words into numbers.  Take in a word number string, and return
# an int containing the numeric conversion.

def word_to_num(wnlist):
    debug('word_to_num: Doing word/number value conversion.')
    
    # Value lookup.
    wnlookup = {}
    wnlookup['ONE'] = '1'
    wnlookup['ON'] = '1'
    wnlookup['WHAT'] = '1'
    wnlookup['WHEN'] = '1'
    wnlookup['RUN'] = '1'
    wnlookup['WHEN'] = '1'
    wnlookup['TWO'] = '2'
    wnlookup['TO'] = '2'
    wnlookup['TOO'] = '2'
    wnlookup['YOU'] = '2'
    wnlookup['TUESDAY'] = '2'
    wnlookup['THREE'] = '3'
    wnlookup['THE'] = '3'
    wnlookup['WHEEL'] = '3'
    wnlookup['BE'] = '3'
    wnlookup['WE'] = '3'
    wnlookup['READ'] = '3'
    wnlookup['THIRTY'] = '3'
    wnlookup['FOUR'] = '4'
    wnlookup['OR'] = '4'
    wnlookup['FOR'] = '4'
    wnlookup['MORE'] = '4'
    wnlookup['FOURTH'] = '4'
    wnlookup['FOG'] = '4'
    wnlookup['LOWER'] = '4'
    wnlookup['WORK'] = '4'
    wnlookup['CORTE'] = '4'
    wnlookup['FIVE'] = '5'
    wnlookup['BY'] = '5'
    wnlookup['MY'] = '5'
    wnlookup['WHY'] = '5'
    wnlookup['FIND'] = '5'
    wnlookup['TRY'] = '5'
    wnlookup['ARE'] = '5'
    wnlookup['I'] = '5'
    wnlookup['SIX'] = '6'
    wnlookup['SET'] = '6'
    wnlookup['SIXTY'] = '6'
    wnlookup['SEVEN'] = '7'
    wnlookup['SEVENTY'] = '7'
    wnlookup['SECOND'] = '7'
    wnlookup['EIGHT'] = '8'
    wnlookup['RIGHT'] = '8'
    wnlookup['A'] = '8'
    wnlookup['NINE'] = '9'
    wnlookup['NIGHT'] = '9'
    wnlookup['NAH'] = '9'
    wnlookup['NINETY'] = '9'
    wnlookup['ZERO'] = '0'
    wnlookup['YEAR'] = '0'
    

    # Value string.
    wnbuf = ''
    for i in range(len(wnlist)):
        try:
            wnbuf = wnbuf + wnlookup[wnlist[i]]
            log_message = 'word_to_num: ' + wnbuf
            debug(log_message)
        except KeyError:
            return -1
    return int(wnbuf)

def do_shutdown():
    global s
    
    # Stop playing sound
    debug('do_shutdown: Stopping sound.')
    killsound()

    # Disconnect from EDS
    debug('do_shutdown: Disconnecting from EDS.')
    s.close()
    
    # Announce shutdown.
    lcdcom("marq_off")
    lcdcom("unset_marq")
    lcdcom("cls")
    lcdcom("cursor 4 0")
    lcdcom("out 'MP3 module'")
    lcdcom("cursor 5 2")
    lcdcom("out 'shutdown'")
    time.sleep(3)
    lcdcom("cls")

    # Write the log.
    debug('do_shutdown: mp3_module terminated.')

    # Exit the program.
    sys.exit(1)
        
def event_handler():
    
    global cursor_pos
    global block_start
    global block_end
    global c_vol
    global oktoplay
    global randomplay
    global rflag
    global s
    global move_inc
    global current_songname
    global song_info
    global playlist_len
    global a
    global is_muted

    # Define regexes to match dynamically generated event strings.
    go_to_song = re.compile('go_to_song (.+)')
    set_volume = re.compile('set_volume (.+)')
    load_playlist_com = re.compile('load_playlist (.+)')
    
    
    # Special regex for parsing ping events.
    ping_parse = re.compile("(ping )\[(.+)\]$")
    
    while 1:

            q = s.recv(1024)
            c = string.strip(q)
            
            debug ('event_loop: got incoming data.')
            
            if (c == ''):
                # Connection needs to be reset.
                debug('event_loop: resetting connection.')
                s = network_init()
                draw_init()

            # c contains the event string that tells us what action to take.
            # We still accept the old single character commands, along with the more
            # formal event strings that speechio_module will generate, since the
            # single character strings are useful for controlling the module manually
            # via a telnet session to the server.
            
            if (c != ''):
                    
                    # Random mode.
                    if (c == 'random_mode'):
                            if (randomplay == 0):
                                    randomplay = 1
                                    rflag = 'r'
                                    draw_screen(cursor_pos, block_start, block_end)
				    send_to_socket('speechio_module: speech_out: Random mode is enabled.\n')

                    # Sequential mode.
                    if (c == 'sequential_mode'):
                            if (randomplay == 1):
                                    randomplay = 0
                                    rflag = 's'
                                    draw_screen(cursor_pos, block_start, block_end)
				    send_to_socket('speechio_module: speech_out: Sequential mode is enabled.\n')
                    # Refresh the screen.
                    if (c == 'r'):
                            draw_screen(cursor_pos,block_start,block_end)

                    # Play the currently selected song
                    if (c == '\n' or c == 'p' or c == 'play_current_song'):
                        # Scroll the marquee.
                        marq_sets = "marq_on " + "0 " + "6 " + "50"	
                        lcdcom(marq_sets)
                        mp3list=a[cursor_pos],
                        mp3list=cursor_pos,
                        thread.start_new_thread(tplay_mp3,mp3list)

                    # Terminate this module.
                    if (c == 'q' or c == 'quit'):
                            killsound()
                            do_shutdown()
                            
                    if (c == 'n' or c == 'go_next_song'):
                        # Check to see if we're already at the bottom of the playlist
                        if (block_start != playlist_len - 2):
                            block_start = block_start + 1
                            cursor_pos = block_start
                            block_end = block_start + 1
                            draw_screen(cursor_pos, block_start, block_end)


                    if (c == '=' or c == 'go_prev_song'):
                        # Check to see if we're already at the top of the playlist.
                        if (block_start != 0):
                            block_start = block_start - 1
                            cursor_pos = block_start
                            block_end = block_start - 1
                            draw_screen(cursor_pos, block_start, block_end)
                            
                    if (c == ',' or c == 'down_volume'):
                            # Move the main volume down 10 notches.
                            c_vol = c_vol - 10
                            volume(c_vol)
                            # Redraw screen with updated volume value.
                            draw_screen(cursor_pos, block_start, block_end)

                    if (c == '.' or c == 'up_volume'):
                            # Move the main volume up 10 notches.
                            c_vol = c_vol + 10
                            volume(c_vol)
                            # Redraw screen with updated volume value.
                            draw_screen(cursor_pos, block_start, block_end)

                    if (c == '1' or c == 'go_forward_10'):
                        if ((block_start + 10) > playlist_len - 2):
                            block_start = playlist_len - 2
                        else:
                            block_start = block_start + 10

                        cursor_pos = block_start
                        block_end = cursor_pos + 1
                        draw_screen(cursor_pos, block_start, block_end)

                    if (c == '2' or c == 'go_back_10'):
                        if ((block_start - 10) > 0):
                            block_start = block_start - 10
                        else:
                            block_start = 0

                        cursor_pos = block_start
                        block_end = cursor_pos + 1
                        draw_screen(cursor_pos, block_start, block_end)

                    if (c == 'b' or c == 'go_first_song'):
                            block_start = 0
                            block_end = 1
                            cursor_pos = 0
                            draw_screen(cursor_pos, block_start, block_end)

                    if (c == 'e' or c == 'go_last_song'):
                            block_start = playlist_len - 1
                            cursor_pos = block_start
                            block_end = playlist_len - 1
                            draw_screen(cursor_pos, block_start, block_end)

                    # New events from here on down.

                    # Stop playing.
                    if (c == 'stop_play'):
                        # Stop scrolling marquee
                        lcdcom("marq_off")
                        killsound()

                    # Pass the song name to the speechio_module when asked.
                    if (c == 'say_song_name'):
                        say_text = 'This song is, ' + current_songname
                        # If a trailing 'additional info cue' character exists, strip it.
                        if (say_text[len(say_text)-1] == '>'):
                            say_text = say_text[:-1]
                        prep_cmd = 'speechio_module: speech_out: ' + say_text + '\n'
                        log_message = 'event_loop: Saying song name ' + current_songname
                        debug(log_message)
                        send_to_socket(prep_cmd)

                    # Say the size of the playlist (not bound to speech, yet)
                    if (c == 'say_playlist_size'):
                        say_text = 'There are currently ' + str(playlist_len) + ' songs in this play list.'
                        prep_cmd = 'speechio_module: speech_out: ' + say_text + '\n'
                        debug('event_loop: saying playlist size')
                        send_to_socket(prep_cmd)

                    # Say the track number of the currently selected song.
                    if (c == 'say_song_number'):
                        say_text = 'This is song number ' + str(cursor_pos)
                        prep_cmd = 'speechio_module: speech_out: ' + say_text + '\n'
                        debug('event_loop: saying song track number')
                        send_to_socket(prep_cmd)
            

                    # Remove a song from the playlist.  Doesn't currently remove the song from the
                    # actual playlist file itself, so this removal only lasts until the module is restarted.
                    if (c == 'dnp_song'):
                        say_text = 'Okay.  I\'ve removed this song from the play list.  It won\'t be played again.'
                        prep_cmd = 'speechio_module: speech_out: ' + say_text + '\n'
                        send_to_socket(prep_cmd)
                        debug('event_loop: removing song from playlist')
                        del a[cursor_pos]
                        playlist_len = len(a)
                        draw_screen(cursor_pos, block_start, block_end)

                    # Say the name of the song artist (if we know it).

                    if (c == 'say_song_artist'):
                        try:
                            # Check to see if the ID3 tag is empty first.  This will be the case
                            # if we're able to extract time, but not artist info from an MP3 file.
                            if (song_info['artist'] != "" or song_info['artist'] == None):
                                say_text = 'The artist on this song is ' + song_info['artist']
                            else:
                                # If there's no artist info, raise a KeyError, which causes the
                                # 'artist unknown' info to be synthesized.
                                raise KeyError
                            
                        except KeyError:
                            say_text = 'The artist of this song is not known.'
                        prep_cmd = 'speechio_module: speech_out: ' + say_text + '\n'
                        send_to_socket(prep_cmd)
                        debug('event_loop: saying song artist name')

                    # Mute volume
                    if (c == 'mute_volume'):
                        volume(0)
                        is_muted = 1
                        draw_screen(cursor_pos, block_start, block_end)
                        
                    # Unmute volume
                    if (c == 'unmute_volume'):
                        volume(c_vol)
                        is_muted = 0
                        draw_screen(cursor_pos, block_start, block_end)

                    # Go to a specific song within the playlist.
                    go_to_song_r = go_to_song.search(c)
                    if (go_to_song_r != None):
                        debug('event_loop: dynamic go_to_song event caught.')
                        track_wval = go_to_song_r.group(1)
                        log_message = 'event_loop: text value of track index: ' + track_wval
                        debug(log_message)
                        track_wval_list = string.split(track_wval, ' ')
                        # Convert word song numbers to an integer.
                        track_ival = word_to_num(track_wval_list)
                        if (track_ival == -1):
                            debug('process_cmd: unable to convert track value to int.  Try again.')
                        else:
                            if (track_ival > playlist_len - 1):
                                say_text = 'That song number was not found.  Please try again.'
                                prep_cmd = 'speechio_module: speech_out: ' + say_text + '\n'
                                send_to_socket(prep_cmd)
                            else:
                                if (track_ival == playlist_len - 1):
                                    cursor_pos = track_ival
                                    block_start = track_ival
                                    block_end = track_ival
                                else:
                                    cursor_pos = track_ival
                                    block_start = cursor_pos
                                    block_end = cursor_pos + 1
                                draw_screen(cursor_pos, block_start, block_end)

                    # Send back a 'pong' response, along with the name of this module.
                    ping_parse_r = ping_parse.search(c)
                    if (ping_parse_r != None):
                        debug('process_cmd: got ping request.')
                        ping_response = ping_parse_r.group(2) + ': pong [mp3_module]\n'
                        send_to_socket(ping_response)

                    set_volume_r = set_volume.search(c)
                    if (set_volume_r != None):
                        debug('process_cmd: setting volume level.')
                        volret = set_volume_r.group(1)
                        log_message = 'process_cmd: requested volume is ' + volret
                        debug(log_message)
                        volret_list = string.split(volret,' ')
                        volval = word_to_num(volret_list)
                        if (volval == -1):
                            debug('process_cmd: unable to convert volume to int.  Please try again.')
                        else:
                            c_vol = volval
                            volume(c_vol)
                            draw_screen(cursor_pos, block_start, block_end)

                    # Load a different playlist
                    load_playlist_r = load_playlist_com.search(c)
                    if (load_playlist_r != None):
                        debug('process_cmd: got playlist change request.')
                        playlist_num = load_playlist_r.group(1)
                        # Convert to numerics
                        playlist_num = string.split(playlist_num, ' ')
                        playlist_num = word_to_num(playlist_num)
                        if (playlist_num == -1):
                            debug('process_cmd: unable to translate playlist number.')
                            say_text = 'I didn\'t understand that playlist number.  Please try again.'
                            prep_cmd = 'speechio_module: speech_out: ' + say_text + '\n'
                            send_to_socket(prep_cmd)
                        else:
                            log_message = 'process_cmd: playlist #' + str(playlist_num) + ' requested.'
                            debug(log_message)
                            # Try and load the playlist filename from the config file.
                            playlist_config_name = 'playlist_' + str(playlist_num)
                            playlist_config_title = 'playlist_' + str(playlist_num) + '_title'
                            config_list_info = [('mp3_module', playlist_config_name, 's'),\
                                               ('mp3_module', playlist_config_title, 's')]

                            # Better error checking needed here!
                            try:
                                
                                playlist_config_hash = set_configs(config_fn, config_list_info)
                                playlist_name = playlist_config_hash['mp3_module'][playlist_config_name]
                                playlist_title = playlist_config_hash['mp3_module'][playlist_config_title]
                                killsound()
                                block_start = 0
                                block_end = 1
                                cursor_pos = 0
                                a = []
                                a = load_playlist(playlist_name)
                                draw_init()
                                log_message = 'process_cmd: Loaded ' + playlist_title + ' playlist (' + playlist_name + ')'
                                debug(log_message)
                                say_text = 'speechio_module: speech_out: '  + playlist_title + ' loaded.\n'
                                send_to_socket(say_text)
                            
                            except:
                                debug('process_cmd: WARNING: Error loading or locating requested playlist.')
                                send_to_socket('speechio_module: speech_out: An error occured when trying \
                                to load the playlist you requested.\n')
                            
                            
# --- Initialization ---

print 'init: MP3 player module starting up. (ALICE v1.00b).'
print 'init: Beginning initialization.'

# Options to retrieve from config file:
config_options = [('mp3_module', 'debug_flag', 'b'), \
                  ('mp3_module', 'log_messages', 'b'), \
                  ('mp3_module', 'log_file', 's'), \
                  ('mp3_module', 'eds_port', 'i'), \
                  ('mp3_module', 'eds_host', 's'), \
                  ('mp3_module', 'speech_feedback', 'i'), \
                  ('mp3_module', 'lcdout_mod', 's'), \
                  ('mp3_module', 'init_volume', 'i'),\
                  ('mp3_module', 'mp3_playlist', 's'), \
                  ('mp3_module', 'mp3_player_app', 's'), \
                  ('mp3_module', 'mixer_app', 's')]

# Config file to use:
config_fn = 'Config/alice.config'
log_message = 'init: Using config file ' + config_fn
print log_message

# Get configuration information
config_data = set_configs(config_fn, config_options)


# Open a log file, if this feature has been enabled.
print 'init: Opening log file.'
if (config_data['mp3_module']['log_messages'] == 1):
    try:
        log_fd = open(config_data['mp3_module']['log_file'], 'a')
    except IOError:
        log_message = 'init: WARNING: Unable to open log file at ' + config_data['mp3_module']['log_file']
        print log_message
        print 'init: WARNING: Logging will occur to console only.'
        config_data['mp3_module']['log_messages']  = 0

# debug() log function usable below this point.

# Start networking and return a socket object.
debug('init: Connecting to event distribution server.')
s = network_init()

# Load playlist
a = []
a = load_playlist(config_data['mp3_module']['mp3_playlist'])

# Set initial values on major status vars.
block_start = 0
block_end = 1

# Top of playlist by default.
cursor_pos = 0

# Initially ok to play a song.
oktoplay = 1

# Not initially in random play mode.
randomplay = 0

# No song playing when we start.
song_playing = 0

# Start in sequential mode.
rflag = 's'

# Establish initial volume setting from config file setting.
c_vol = volume(config_data['mp3_module']['init_volume'])

# path_strip removes trailing directory path information from mp3 filenames before
# they're displayed to the LCD.
path_strip = re.compile(r'^(.*)/([^/]+)')

# smart_divide attempts to divide up file names into artist / song name information
# if we don't have ID3 information available to work with, based on the assumption
# that many song filenames take the form artist name - song name
smart_divide = re.compile('(.[^\-]+) [\-]+ (.+)')
move_inc = 10

# Whether we're in a muted state or not:
is_muted = 0

debug('init: Initialization completed successfully.')
# Set an empty value, safe if we're asked to say the song name,
# and aren't actually playing anything... This gets changed by
# the draw_screen() function above.
cur_fn = ''

# Do the initial draw
draw_init()

# Start the event handler
event_handler()

#!/usr/bin/python
# Project: Turbolift: An application server for voice powered computing
# Component: Poll emulation utilities
# Description:
# This utility file contains functions which help manage use of select.select()
# event data, making event handling from this function easier to manage.
# This file must be included in your Python module directory if you're using
# ALICE with an OS that does not implement the .poll() call.  Windows is one
# of these.
#
# Current Version: 2.0
# Author: (C) Copyright Rupert Scammell <rupe@sbcglobal.net> 2001-2005
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


import os, sys, select, socket

# poll_emulate.register()
# Inputs: input event list, output event list, exceptional event list,
# object to add to the event lists (usually a socket)
# Outputs: a list, containing the three sublists that were given as input,
# with the object appended to them.
def register(input_event, output_event, ex_event, object):
    input_event.append(object)
    # We're not really interested in whether an object is available
    # to be written to.  If the socket is open, we assume it's writeable.
    #output_event.append(object)
    ex_event.append(object)
    return [input_event, output_event, ex_event]

# poll_emulate.unregister()
# Inputs: input event list, output event list, exceptional event list,
# object to add to the event lists (usually a socket)
# Outputs: a list, containing the three sublists that were given as input,
# with the object removed from them.
def unregister(input_event, output_event, ex_event, object):
    input_event.remove(object)
    #output_event.remove(object)
    ex_event.remove(object)
    return [input_event, output_event, ex_event]

# poll_emulate.convert_select_elist()
# Inputs: a list, containing 3 list items, typically the output from a
# returned select.select() call.
# Outputs: This function returns a list that converts the input list
# into the equivalent event output that the select.poll() call would have
# provided when the same set of events were seen.  This consists of a list,
# which has as its elements two item tuples in the form (fileno, eventno),
# where fileno represents the file descriptor number of the object on
# which the event was seen, and eventno represents a translation of the
# original list in which the event occured (input, ready for output, error)
# into the appropriate select.POLL* event value, as specified in the
# comment below.

def convert_select_elist(elist):
    # We expect a 3 item list here, which is what select.select() returns.
    # item 0: items with input (map to select.POLLIN)
    # item 1: items with output(map to select.POLLOUT)
    # item 2: items that have exceptional conditions (map to select.POLLERR)

    # The event list item we'll return:
    converted_event_list = []

    # Event mappings.  Order here corresponds to the
    # order of the event lists we receive in elist.
    emap = [select.POLLIN, select.POLLOUT, select.POLLERR]
    
    for i in range(2):
        subs_len = len(elist[i])
        for j in range(subs_len):
            converted_event_list.append((elist[i][j].fileno(), emap[i]))
    return converted_event_list


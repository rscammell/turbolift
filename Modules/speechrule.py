#!/usr/local/bin/python
# Project: Turbolift: An application server for voice powered computing 
# Component: Speech recognition learning module
# Description:
# This component contains the utility functions necessary for
# the use of the speech recognition training algorithm that Turbolift
# incorporates.  See Docs/HACKING for more information.
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

import os, os.path, sys, pickle, fileinput, string, re

# Global variables

# The threshold at which associations between unbound
# speech patterns are mapped to commands.  The
# (perhaps invalid) assumption is made that the user
# will not change their intent midstream, thereby
# invalidating their 'incorrect' attempts to
# produce a certain outcome.

_athresh = 2

# Print debugging symbols?
_debug = 1

# The list of utterance attempts to get to an end goal.
try_list = []

# debug
# input: debugging string
# output: none

def debug(dstr):
    if (_debug == 1):
        print dstr
        
# load_speech_data
# inputs: speech data filename
# output: speech data table

def load_speech_data(filename):
    try:
        f = open(filename,"r")

        data_handle = pickle.Unpickler(f)
        speech_data_table = data_handle.load()
        debug("Speech data file load successful.")
        return speech_data_table

    except:
        debug("Couldn't find file.")


# init_speech_data
# inputs: speech data filename (sd_filename), language
# model filename (lm_name)
# output: new speech data table (dictionary)

def init_speech_data(sd_filename, lm_name):
    speech_data_table = {}
    # Load the key phrases from the Sphinx language model file
    # as keys in the speech_data_table dictionary.
    speech_data_table = load_vocab_keys(lm_name, speech_data_table)

    # Write the created dictionary to a pickle file, which can
    # be retrieved in the future by load_speech_data()
    try:
        sd_handle = open(sd_filename,"w")
        sd_pickle = pickle.Pickler(sd_handle)
        sd_pickle.dump(speech_data_table)
        sd_handle.close()
        debug("Dictionary write successful.")

    except:
        debug("Dictionary write failed!")

    return speech_data_table
        
# load_vocab_keys
# inputs: language model filename, dictionary name
# output: speech data table (dictionary)
# This function builds an initial speech data dictionary,
# consisting of phrases loaded from the vocabulary list
# of a Sphinx speech model.

def load_vocab_keys(lm_filename, std_dict):
    bind_file_sep = re.compile('(.+);(.+)') 
    for line in fileinput.input([lm_filename]):
        proc_line = string.strip(line)
        bind_file_sep_r = bind_file_sep.search(proc_line)
        if (bind_file_sep_r != None and line[0] != "#"):
            proc_line = string.strip(bind_file_sep_r.group(1))
            if (std_dict.has_key(proc_line) == 1):
                dstring = "Key: " + proc_line + " already in dict."
                debug(dstring)
            if (std_dict.has_key(proc_line) == 0):
                dstring = "Adding key: " + proc_line
                debug(dstring)
                std_dict[proc_line] = {}
                # The key 'P' specifies which top level dict key
                # each of these keys are associated with.
                # In all cases here, the mapping is isomorphic
                # but this isn't always the case later (see
                # larger explanation below)
                std_dict[proc_line]['P'] = proc_line
        else:
                pass
    # Finally, add a blank try_list value.
    std_dict['try_list'] = []
    debug("Key addition complete.")
    return std_dict

# assoc_check *** (Deprecated, use iterative_regex_match instead) ***
# input: speech utterance, speech data dictionary
# output: bool, 1: recognized, 0: unrecognized
# Checks to see if an utterance is located in the current
# speech dictionary.

def assoc_check(utt, std_dict):
    if (std_dict.has_key(utt) == 1):
        return 1
    if (std_dict.has_key(utt) == 0):
        return 0

# dict_update
# Flushes old dictionary object from dictionary file,
# and replaces it with an updated copy of the object.

def dict_update(dictionary_file, object):
    os.remove(dictionary_file)
    dfile = open(dictionary_file,"w")
    pickle_file = pickle.Pickler(dfile)
    pickle_file.dump(object)
    dfile.close()


# But I'm A Cheerleader!
# root_finder
# input: top level speech dictionary key
# output: root level P key for given top level key.

def root_finder(top_key):

    current_P = sdt[top_key]['P']
    # In almost all cases, current_P should
    # now point to a top level key in the
    # dictionary whose P value is isomorphic to
    # its top level key name,
    # i.e. current_P == sdt[current_P]['P']

    # Gratuitous iteration counter,
    # for debug purposes if we go into the
    # while below.
    i = 0

    # We'll generally never enter the loop
    # below.  Even with deeply derived utterance
    # keys (ie. top level keys added because a threshold
    # was exceeded, which are themselves derived from
    # a threshold-added top level key), no threshold
    # added key should ever be more than one step away from a 'P'
    # reference that is isomorphic to its top level key.
    # Got that? :-)
    
    while (current_P != sdt[current_P]['P']):
        debug("---")
        dline = "iteration: " + str(i)
        dline2 = "current_P: " + current_P
        dline3 = "top_key: " + top_key
        debug(dline)
        debug(dline1)
        debug(dline2)
        debug(dline3)
        current_P = sdt[current_P]['P']
        i = i + 1
    dline = "root P: " + current_P
    debug(dline)
    return current_P


# Iterate through a list of items, looking for a regex
# match against the input data.
# Inputs: rlist, a list of regular expressions.
# match_data, a text string to be matched.
# Output: The matched regex string.

def iterative_regex_match(rlist, match_data):
    returned_regex = ''
    for i in range(len(rlist)):
        temp_re_object = re.compile(rlist[i])
        if (temp_re_object.search(match_data) != None):
            returned_regex = rlist[i]
            log_message = 'iterative_regex_match: regex matched: ' + rlist[i]
            debug(log_message)
            break
    return returned_regex

            
# event_loop
# The main loop, which processes utterances after the
# speech dictionary (sdt, a global var) has been
# either loaded from a file, or initialized anew.

def event_loop(speech_data_filename, lm_filename, utt):
    global sdt, try_list
    debug("Entering event_loop")
    dline = "utterance: " + utt
    debug(dline)
    # Load the last try_list from the dictionary
    debug("Loading try_list from speech dictionary...")
    try_list = sdt['try_list']
    debug(try_list)
    debug("Loaded.")
    while 1:

        # utt represents the utterance that we were passed.
        # CRs and whitespace get in the way of things, so
        # we strip them here before proceeding.
        
        utt = string.strip(utt)

        if (utt != ''):
            dstring = "Got utterance " + utt
            debug(dstring)
            matched_regex_string = iterative_regex_match(sdt.keys(),utt)
            
            if (matched_regex_string  == ''):
                debug(sdt)
                debug("Did not find regex match in speech table.")
                
                # Make utterance into an actual regular expression.
                # When the utterance eventually gets associated with a target
                # phrase (and promoted to a top level key), it'll have as its
                # 'P' value the P value of the target phrase, so any utterance
                # that eventually matches the regex below (exact match only),
                # will get matched against the P value for purposes of event
                # mapping, etc.
                # This relieves us of any need here to do sophisticated
                # utterance conversion.
                utt = '^'+utt+'$'
                try_list.append(utt)
                debug(try_list)

            if (matched_regex_string != ''):
                debug(sdt)
                debug("Found regex match in speech table.")
                i = 0

                # Iterate through the 'incorrect' entries,
                # and add them as keys in the recognized
                # utterance's dictionary, complete with weights.

                dstring = "try_list len: " + str(len(try_list))
                debug(dstring)
                while (i < len(try_list)):

                    debug("In utterance addition loop.")

                    # Ok, this utterance (try_list[i]) already exists
                    # for this end goal utterance.  Increase the weight by 1.

                    if (sdt[matched_regex_string].has_key(try_list[i]) == 1):
                        dstring = "Key: " + matched_regex_string + " recognized. Increment 1."
                        debug(dstring)
                        sdt[matched_regex_string][try_list[i]] = sdt[matched_regex_string][try_list[i]] + 1

                        # Handle the condition where the incorrect utt.
                        # has been seen >= than the a_thresh threshold.

                        if (sdt[matched_regex_string][try_list[i]] >= _athresh):
                            dstring = "Threshold for " + try_list[i] + " reached.  Adding to top level of speech dictionary."
                            debug(dstring)

                            # Create the utterance at the top level of the
                            # speech dictionary.
                            # Association of utterances with one another
                            # will occur by looking at the first value
                            # of each top level utterance key.
                            # 'Correct' top level entries will be isomorphically
                            # mapped onto one another (e.g. seeing utterance
                            # 'TURN ON MP3 PLAYER' will have as its P
                            # value 'TURN ON MP3 PLAYER', and
                            # 'incorrect' utterances will have as their
                            # P value, the key of the correct utterance.

                            sdt[try_list[i]] = {}

                            # Map to the correct base root.
                            sdt[try_list[i]]['P'] = root_finder(matched_regex_string)

                    # First time this utterance has been seen
                    # for this end goal.  Set up a counter for the new
                    # utterance, with a starting value of 1.

                    else:
                        dstring = "Key: " + try_list[i] + " ! recognized.  Weight is 1."
			debug(dstring)
                        sdt[matched_regex_string][try_list[i]] = 1

                    i = i + 1
                try_list = []

            # Update the dictionary file with the new information.
            try:
                # Copy the try list back to the hash table,
                # in preparation for pickling.
                sdt['try_list'] = try_list
                dict_update(speech_data_filename, sdt)
                debug("Dictionary updated.")

            except:
                debug("Couldn't update dictionary file!")

            # If the utterance was recognized at the top level,
            # return the root utterance associated with it.
            try:
                return root_finder(matched_regex_string)

            # If it's not at the top level, add it to the try_list
            # and return None.
            except KeyError:
                return None
 

def process_init(speech_data_filename, lm_filename, action='Default'):
    global sdt

    # Behave normally if the user tells us to, or an action isn't provided.
    if (action == 'Default'):
        if (os.path.isfile(speech_data_filename) == 1):
            debug("Speech data file exists.  Loading...")
            sdt = load_speech_data(speech_data_filename)
            debug("Loaded to memory.")
        else:
            debug("Didn't find speech data file.  Creating anew...")
            sdt = init_speech_data(speech_data_filename, lm_filename)
            debug("New speech data file loaded to memory.")

    # Add onto the language model if one already exists.
    # General procedure for this is as follows:
    # Load existing language model to a first hash table.
    # Load new language model to a second hash table.
    # Create third hash table that will contain the non overlapping set of hash entries
    # from the first two tables.
    # Return an error if there's not an LM to work with, and load an empty hash table.
    if (action == 'Rebuild'):
        if (os.path.isfile(speech_data_filename) == 1):
            debug("Executing speech data table synchronization...")
            original_sdt = load_speech_data(speech_data_filename)
            debug("Loaded old speech data table into memory.")
            new_sdt_name = speech_data_filename + '.new'
            new_sdt = init_speech_data(new_sdt_name, lm_filename)
            debug("Created new speech data table in memory.")
            # This hash will contain the updated set of speech table values.
            final_sdt = {}
            debug("Integrating data from new data table...")
            # First update stage - prime final_sdt with new keys.
            final_sdt.update(new_sdt)
            debug("Integrating data from old data table...")
            # Second update stage - Adds any derivative keys that may have been generated
            # within the code above, and causes any keys that already exist (from first
            # stage key update) to be updated with their values from original_sdt.
            # Wholly new keys that exist in new_sdt only are left alone.
            final_sdt.update(original_sdt)
            # Write out new speech data file
            dict_update(speech_data_filename, final_sdt)
            debug("Wrote updated speech data file to disk.")
            # Do cleanup.
            try:
                os.remove(new_sdt_name)
            except OSError:
                debug("WARNING: Couldn't successfully cleanup temp file used during integration.")
            sdt = final_sdt 
        else:
            debug("Didn't find speech data file to build on.")
            sdt = {}

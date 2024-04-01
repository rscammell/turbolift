#
# Name: pyCFontz
# Desc: library for controlling CrystalFontz serial LCDs
# Date: 1/01/2001
# Vers: 0.1.0
#
# Copyright (C) 2001 Ben Wilson
#  
#
# This library is free software; you #can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
#
# LCD Module for CrystalFontz LCDs
# http://www.crystalfontz.com
# spec sheets with command references, etc can be found there.
#	
#	http://mpy3.thelocust.org
#	http://mpy3.sourceforge.net
#	Contact: ben@thelocust.org / thelocust@users.sourceforge.net
#
# init it like so:
#	foo = pyCFontz.open_lcd("/dev/ttyS0")
#
# or, whatever port you are using.  scroll down to see all the functions.
# they are named appropriately, and I'm lazy.
#
# when init'ing the thing, note that you can also supply rows, cols, has_backlight,
# contrast_backlight_off, contrast_backlight_on
#
#
# properties:
# 	cols - number of columns
# 	rows - number of rows
#	has_backlight - well?  does it?  0 for no, 1 for yes
#	contrast_backlight_on - when the backlight is on, set the contrast to this.
#	contrast_backlight_off - opposite of above. 
#		(the default contrast_backlight_on and off work well for my CrystalFontz,
#		a 4x20 634)
#

import os, tty, termios, string, array

class CFontz:

	contrast = 64
	backlight = 100
	rows = 4					# rows your lcd has
	cols = 20					# columns your lcd has
	has_backlight = 1			# if your lcd is backlit, 1, else 0
	contrast_backlight_on = 64	# when the backlight is on, or the backlight_on method is called,
							# set the contrast to this level

	contrast_backlight_off = 36 # when the backlight is off, or the backlight_off method is called,
							# set the contrast to this level

	def __init__(self, port_to_open,rows=4, cols=20, has_backlight=1, \
			contrast_backlight_on = 64,contrast_backlight_off=36):	

		# e.g. foo = pyCFontz.open_lcd("/dev/ttyS0")
		# or you can specify the rows, columns,and whether or not it has a
		# backlight when you init the class object in yo' script
		# 

		self.port = open(port_to_open, "w")
		self.fd = self.port.fileno()
		tty.setraw(self.fd,termios.TCSANOW)
		self.rows = rows
		self.cols = cols
		self.has_backlight=has_backlight
		self.contrast_backlight_off=self.contrast_backlight_off
		self.contrast_backlight_on=self.contrast_backlight_on



	def __del__(self):
		self.port.close()


	def open_display(self):
		pass

	def shutdown(self):
		pass



	def cls(self):					# clears the screen
		# clear screen
		self.out('%c' % 12)
		self.port.flush()

	
	def out(self, string_to_write):				# writes out a string to the current 
		# output string						# cursor position
		self.port.write(string_to_write)
		self.port.flush()

	def hide_disp(self):						# hides the display
		self.out('%c' % 2)

	def restore_disp(self):						# restores display
		self.out('%c' % 3)

	def hide_cursor(self):						# hide cursor
		self.out('%c' % 4)

	#### CURSOR RELATED #########################################################################

	def uline_cursor(self):						# sets cursor to the underline style
		self.out('%c' % 5)

	def block_cursor(self):						# sets cursor to block style
		self.out('%c' % 6)

	def invert_block_cursor(self):				# change to block cursor with no underline

		self.out('%c' % 7)

	def backspace(self):						# destructive backspace
		self.out('%c' % 8)

	def lf(self):							# line feed (move down one line), if scroll is on
		self.out('%c' % 10)				# and at the bottom line, the display will scroll up,
										# leaving bottom line blank.

	def delete(self):						# delete in place
		self.out('%c' % 11)

	def clear(self):						# form feed, clear display
		self.out('%c' % 12)

	def cr(self):							# return cursor to leftmost space on row
		self.out('%c' % 13)

	def crlf(self):							# figure it out!
		self.cr()
		self.lf()

	def cursor(self,col,row):				# sets cursor position to col, row
		self.out('%c%c%c' % (17,col,row))

	##### BACKLIGHT CONTROLS ###############################################

	def backlight_on(self):
		# turns backlight to 100, contrast to contrast_backlight_on setting
		if(int(self.has_backlight)):
			self.set_backlight(100)
			self.set_contrast(self.contrast_backlight_on)

	def backlight_off(self):
		# turns backlight to 0, contrast to contrast_backlight_off setting
		if(int(self.has_backlight)):
			self.set_backlight(0)
			self.set_contrast(self.contrast_backlight_off)

	def set_backlight(self,set_level):
		# on the CFontz display, this level is between 
		# 0 and 100 with 25 different brightness levels
		# so, instead the set_level should be between
		# 0 and 24 
		if(int(self.has_backlight)):
			self.out('%c%c' % (14,set_level))
			self.backlight = set_level

	def backlightup(self):
		if(int(self.has_backlight)):
			if(self.backlight <= 96):
				self.set_backlight(self.backlight + 4)

	def backlightdown(self):
		if(int(self.has_backlight)):
			if(self.backlight >= 4):
				self.set_backlight(self.backlight - 4)

	##### CONTRAST CONTROLS ###############################################
	def set_contrast(self,set_level):
		self.out('%c%c' % (15,set_level))
		self.contrast = set_level

	def contrastup(self):
		if(self.contrast <= 96):
			self.set_contrast(self.contrast + 4)

	def contrastdown(self):
		if(self.contrast >= 4):
			self.set_contrast(self.contrast - 4)




	def hbar(self,graph_index,style,start,end,length,row):
		# horizontal bar graph
		self.out('%c%c%c%c%c%c%c' % (18,graph_index,style,start,end,length,row))

	def scroll_on(self):		# sets scroll (ie, if a line feed is done at the bottom row,
		self.out('%c' % 19) # or if wrap is on and a line exceeds the column width
							# the contents of the display will scroll up

	def scroll_off(self):		# sets the scroll off (see scroll_on description)
		self.out('%c' % 20)

	def set_marq(self, str):				# set the marquee (auto-scrolling line) to a certain string)
		for i in range(len(str)):
			self.out('%c%c' % (21,i))
			self.out(str[i])

	def unset_marq(self):					# clear the marquee
		for i in range(21):
			self.out('%c' % 21)
			self.out('')
		
	def marq_on(self, line, step, speed):	# line is the line on which it will be displayed.
		# line = [0 to 3]				# step is how many pixels it moves each step
		# step = [1 to 6]				# speed is how often it makes those steps.
		# speed = [5 to 100]
		self.out('%c%c%c%c' % (22,line,step,speed))

	def marq_off(self):						# stops the marquee
		self.marq_on(255,1,5)

	def wrap_on(self):						# set line wrap on
		self.out('%c' % 23)
			
	def wrap_off(self):						# set line wrap off
		self.out('%c' % 24)

	def set_custom(self, char,d0,d1,d2,d3,d4,d5,d6,d7):			# set custom characters.  char is the character (0-7 to set)
		self.out('%c%c%c%c%c%c%c%c%c%c' % (25,char,d0,d1,d2,d3,d4,d5,d6,d7))

	def show_custom(self, char):		#show the custom character number #char)
		self.out('%c' % (128+char))

	def reboot(self):						# reboot the firmware (rarely needed)
		self.out('%c%c%c%c%c%c%c%c%c%c%c' % (32,32,32,32,32,32,32,32,32,26,26))

	def up(self):							# move cursor up
		self.out('%c%c%c' % (27,91,65))

	def down(self):							# move cursor down
		self.out('%c%c%c' % (27,91,66))

	def right(self):						# move cursor right
		self.out('%c%c%c' % (27,91,67))

	def left(self):							# move cursor left
		self.out('%c%c%c' % (27,91,68))

	def bignum(self, style, col, num):			# display built-in large number. 
		# style = 0 for 3x4, 1 for 4x4
		# column = 0 to 17 for style0, 0 to 16 for style 1
		self.out('%c%c%c%c' % (28,style,col,num+48))

	def line(self, linenum, text):			# display a line of text
		self.cursor(0,linenum)
#		self.out(text)
		self.out(string.ljust(string.strip(text),self.cols))

	def cline(self, linenum, text):			# display a line of centered text
		text = string.center(text,self.cols)
		self.line(linenum, text)

	def blankline(self, linenum):
		self.cursor(0,linenum)
		string = ""
		for i in range(self.cols):
			string = string + " "
		self.out(string)

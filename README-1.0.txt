FFFFF TTTTT  888  M   M  AAA  PPP  PPP  EEEEE RRR        1     000
F       T   8   8 MM MM A   A P  P P  P E     R  R      11    0   0
FFF     T    888  M M M AAAAA PPP  PPP  EEE   RRR        1    0   0
F       T   8   8 M   M A   A P    P    E     R R  v v   1    0   0
F       T    888  M   M A   A P    P    EEEEE R  R  v  11111 . 000
/*****************************************************************************
   ft8mapper - maps stations by their grid data from WSJT-X
    Copyright (C) 2024  TCJC
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.
    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
    See the GNU General Public License for more details.
    <https://www.gnu.org/licenses/>.
******************************************************************************/

ft8mapper provides a very lightweight filtering option for the FT8 protocol.
The WSJT-X software is required for ft8mapper to work. 
It definitely works on MacOS and should work on Windows and Linux,Let us know!

ALL MAPS IN THIS APP COURTESY OF: "OpenStreetMap contributors" !!!

=============
REQUIREMENTS:
=============

- PYTHON3 -- You MUST have python 3.

IMPORTANT NOTE FOR MacOS MONTEREY (12.x or LATER): you MUST run python 3.10 
or later.

*** Please see note below under INSTALL section for a brief explanation of 
Apple's problem cause by shipping incompatible versions of Python with 
their OS release.

The script requires Python 3 that supports Tkinter. The Mac version of 
Python 3 may require an upgrade as the Mac version has a deprecated Tkinter. 
"Brew" may be used to upgrade python, do so at your own risk or run 
deprecated version.

To install tkinter if you don't have the module, enter this at a terminal 
or cmd prompt:

pip3 install tk

-- or --

pip install tk


======
FILES:
======

ft8mapper.py is the script, the other *.png files are the map images.

A file, mapwcfg.bin, will be created after first use to store window 
settings. If your map windows become corrupted, simply delete this 
file it will be re-built.


=============
INSTALL & RUN
=============

Download ft8mapper.zip and unzip its contents into one directory. The 
actual directory does not matter. 

Run the Python script ft8mapper.py. You may need to change the first 
line of the script to point to the path of your Python 3.x interpreter.

You can also run from a command line: python ft8mapper.py

On some systems this may be: python3 ft8mapper.py

Run WJT-X, making sure that on the "Reporting" tab that 
"Accept UDP Requests" is checked.

Make sure UDP server port is set to 2237.

Read the "HOW TO USE" section below for useful info...


================================
RUNNING TKINTER PYTHON ON A MAC:
================================

There is an odd behavior on Macs with certain newer OS versions 
(12.x Monterey and later) and certain versions of Python (3.9.x and earlier).

If you experience blank or flickering in js8mapper then you have a bad 
combination of Python and MacOS.

This is because MacOS ships an old version of Python (3.9 or earlier) that 
seems incompatible with changes in MacOS Monterey 12.x.

To resolve this bug be sure to run at least Pyton3.10 or later. Please 
install this in the location "/usr/local/bin/python3". Then edit the 
first line of the python script to "#!/usr/local/bin/python3" (no quotes). 
There is only 1 script. This ensures that the old version of Python 
stored in "/Library..." is NOT used by ft8mapper.


===========
HOW TO USE:
===========

If you band hop you may enjoy the band buttons at the top of the window 
that will filter the stations by the band. To see all bands click "ALL".

Hover over a station on the map shows the callsign, grid, band, SNR,
the time the station was last heard and the first 30 characters of its
last message it sent. This info appears in the lower left corner similar
to PSKReporter.

Clicking on the dot will open the webbrowser and look up the station
on QRZ or HamCall depending on the radio button selected under the 
Clear and Quit buttons.

The app opens with the World Map (WM), but different regions can be 
selected: NA = North America, SA = South America, EU = Europe, 
AF = Africa, AS = Asia, OC = Oceania

The Call and Grid buttons sort the text data in a right window that
will appear allowing the user to see all the stations. This window
will disappear with a subsequent Call or Grid button click. If you
click on a grid in the "call" or "grid" window, js8mapper will 
flash the grid on the map so you can see where it is located.

The "Msg" button shows the last heard message sent by a station. 

Settings button lets you change the port and IP address if you are using
ft8mapper with JTalert, GridTracker, etc...

Clear button deletes all entries.

Quit button closes the mapper app.

The app will remember window settings (drag it longer, wider) and it will 
remember the scrollbar positions, but you must hit the "Quit" button 
for these options to be saved.

The "Last:" pull-down selection allows you to see stations you've heard
in just the last 15 minutes... selectable all the way up to the last
24 hours. 

When shutting down ft8mapper, it saves the stations heard 
that are 24 hours or less, upon re-opening it will display stations 
less than 24 hours old. If the app is left open it will eventually expire
stations that age over 24 hours.

If your window settings or the stations appear corrupted, simply delete 
the mapwcfg.bin file and/or the stations.bin file in the software directory 
and the app will re-initialize these when opened.

Enjoy


-----------------------------------------------------------

That's all I can think of... there isn't much to it.

Please drop us an email and tell us what you think.

We value your feedback, thanks!

-----------------------------------------------------------




import os
import re
import json
import math
import time
import queue
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from tkinter import messagebox
import tkinter.font as tkFont
import TKinterModernThemes
from functools import partial
import logging
import datetime
import webbrowser
from PIL import Image, ImageTk

from . import maps
from . import _station
from . import events
from . import examples
from . import settings
from . import constants
from . import maidenhead

logger = logging.getLogger('gui')

class GUI(TKinterModernThemes.ThemedTKinterFrame):
    from . import version

    def __init__(self, config, on_config_changed=None, on_exit=None, example_stations=False, rx_grid=None):
        self.config = config
        self.on_config_changed = on_config_changed
        self.on_exit = on_exit
        self.example_stations = example_stations
        self.rx_grid = rx_grid

        # initialize TK window subsystem
        # create tkinter root (required for tk.IntVar construction)
        super().__init__(
            self.version.APPNAME, # title
            'sun-valley', # theme
            'light' if self.config['window']['dark'] == 0 else 'dark', # mode
            usecommandlineargs=False
            )
        icon = tk.PhotoImage(file='ft8mapper.png')
        self.master.iconphoto(True, icon)
        self.wndo = self.master
        self.dark_mode = tk.IntVar(value=int(self.config['window']['dark'])) # 0 = light, 1 = dark
        self.map_scale = tk.IntVar(value=int(self.config['window']['scale'])) # 0 = small, 1 = large
        self.range_rings = tk.IntVar(value=self.config['window']['rangerings']) # 0 = off, 1 = on
        self.list_grid = tk.BooleanVar(value=self.config['window']['list']['grid'])
        self.list_band = tk.BooleanVar(value=self.config['window']['list']['band'])
        self.list_report = tk.BooleanVar(value=self.config['window']['list']['report'])
        self.list_range = tk.BooleanVar(value=self.config['window']['list']['range'])
        self.list_age = tk.BooleanVar(value=self.config['window']['list']['age'])
        self.list_msgs = tk.BooleanVar(value=self.config['window']['list']['msgs'])
        self.list_last_msg = tk.BooleanVar(value=self.config['window']['list']['lastmsg'])

        self.sortby = self.config['window']['sort']          # initialize sortby to callsign mode
        self.bandfilter = self.config['window']['band']      # bandfilter set to any band
        self.sband = constants.any_band           # initial band set to 0 till we figure it out
        self.CURMAP = self.config['window']['curmap']         # start on worldmap
        self.agelimit = min(constants.age_labels.items(), key=lambda t: abs(self.config['window']['agelimit'] - t[1]))[1] # closest greater or equal time limit
        self.plotx = self.config['window']['plot']['x'] # time base
        self.ploty = self.config['window']['plot']['y'] # data source/metric
        self.last_mouse = None # last mouse position when dragging the map
        self.row_division = {} # map column of table to column width in characters
        self.once = False # initial draw map on startup

        # variables for ui widgets
        self.tclick = tk.StringVar()
        self.tclick.set([key for key in constants.age_labels if constants.age_labels[key] == self.agelimit][0])
        self.tclick.trace_add('write', self.on_filter_time_changed)

        self.bclick = tk.StringVar()
        self.bclick.set([k for k, v in constants.band_labels.items() if v == self.bandfilter][0])
        self.bclick.trace_add('write', self.on_filter_band_changed)

        self.plotmetric = tk.StringVar()
        self.plotmetric.set([key for key in constants.plot_metrics if constants.plot_metrics[key] == self.ploty][0])
        self.plotmetric.trace_add('write', self.change_plot)

        self.plottime = tk.StringVar()
        self.plottime.set([key for key in constants.age_labels if constants.age_labels[key] == self.plotx][0])
        self.plottime.trace_add('write', self.change_plot)

        self.mapidx = tk.StringVar()
        self.mapidx.set(self.CURMAP)
        self.mapidx.trace_add('write', self.on_change_map)

        # flags indicating need for update of ui
        self.flag_message = False
        self.flag_band_change = False
        self.flag_receiver_location = False
        self.flag_filter = False
        self.flag_list = False
        self.flag_replot = False
        self.flag_map = False
        self.update_scheduled = False
        self.last_statwin_update = datetime.datetime.now()

        self.canvas = None
        self.mto = {}
        for key, value in self.config['window']['map'].items():
            self.mto[key] = value

        self.rx_station = None
        if self.rx_grid is None and self.config['rx'] == '':
            self.rx_grid = self.config['rx'] # restore last receiver location
        if rx_grid is not None:
            if maidenhead.locator_valid(rx_grid):
                self.rx_grid = rx_grid
            else:
                raise Exception('locator of receiver is invalid!')
            logger.info('setting receiver location to %s.' % self.rx_grid)
            self.rx_station = _station.Station(datetime.datetime.now().timestamp(), constants.RX_CALL, self.rx_grid, 0, 0)
        self.spots = set() # list of spot ids, i.e. plotted stations, on map
        self.station_data = {str(band): {} for _, _ , band, _ in constants.band_list}
        self.message_data = [] # list of station messages (timestamp, call, grid, snr/report)
        self.last_remove_old_data = None
        self.selected_call = None

        # inter-thread communication queue
        self.event_queue = queue.Queue()

        self.clear()
        self.load_stations()
        self.load_messages()
        self.remove_old_data()
        self.create_ui()

        if self.example_stations:
            logger.info('adding example station data')
            self.load_example_data() # for debugging or demonstration only

        self.settings_open = False

    @staticmethod
    def default_config(config):
        config['window']['dark'] = 0 # use light mode as default
        config['window']['position'] = '1288x900+30+30'
        config['window']['sort'] = 'C' # sort by call
        config['window']['scale'] = 0 # use small map
        config['window']['rangerings'] = 0 # no range rings
        config['window']['curmap'] = 'WM' # show world map
        config['window']['band'] = constants.any_band
        config['window']['agelimit'] = 86400 # 1 day
        config['window']['plot'] = {}
        config['window']['plot']['x'] = 1800 # 30 minutes
        config['window']['plot']['y'] = 'M' # plot messages per minute
        config['window']['list'] = {} # visible table columns
        config['window']['list']['grid'] = True
        config['window']['list']['band'] = True
        config['window']['list']['report'] = False
        config['window']['list']['range'] = False
        config['window']['list']['age'] = False
        config['window']['list']['msgs'] = False
        config['window']['list']['lastmsg'] = False
        config['lookup'] = constants.lookup_QRZ
        config['rx'] = '' # unknown receiver location

        # initial slider positions for the maps
        config['window']['map'] = {
            # small map
            'WM0': (0.128, 0.250),
            'NA0': (0.250, 0.245),
            'SA0': (0.200, 0.110),
            'EU0': (0.110, 0.308),
            'AF0': (0.185, 0.489),
            'AS0': (0.324, 0.303),
            'OC0': (0.230, 0.343),
            # large map
            'WM1': (0.128, 0.250),
            'NA1': (0.250, 0.245),
            'SA1': (0.200, 0.110),
            'EU1': (0.110, 0.308),
            'AF1': (0.185, 0.489),
            'AS1': (0.324, 0.303),
            'OC1': (0.230, 0.343)
        }

    def save_config(self):
        if self.on_config_changed is not None:
            logger.debug('saving GUI configuration')
            self.config['window']['position'] = self.wndo.winfo_geometry()
            self.config['window']['curmap'] = self.CURMAP
            self.config['window']['sort'] = self.sortby
            self.config['window']['dark'] = self.dark_mode.get()
            self.config['window']['scale'] = self.map_scale.get()
            self.config['window']['rangerings'] = self.range_rings.get()
            self.config['window']['band'] = self.bandfilter
            self.config['window']['agelimit'] = self.agelimit
            self.config['window']['plot']['x'] = self.plotx
            self.config['window']['plot']['y'] = self.ploty
            self.config['window']['list']['grid'] = self.list_grid.get()
            self.config['window']['list']['band'] = self.list_band.get()
            self.config['window']['list']['report'] = self.list_report.get()
            self.config['window']['list']['range'] = self.list_range.get()
            self.config['window']['list']['age'] = self.list_age.get()
            self.config['window']['list']['msgs'] = self.list_msgs.get()
            self.config['window']['list']['lastmsg'] = self.list_last_msg.get()
            for key, value in self.mto.items():
                self.config['window']['map'][key] = value
            self.config['rx'] = self.rx_station.grid if self.rx_station is not None else ''
            self.on_config_changed()

    def load_stations(self):
        logger.info('loading stations file')
        try:
            stations_filepath = os.path.join(self.config['configdir'], 'stations.json')
            if os.path.isfile(stations_filepath):
                with open(stations_filepath, 'r') as file:
                    self.station_data = json.load(file, object_hook=_station.from_json)
                self.flag_message = True
                logger.info('loaded %d stations from file' % (sum(len(self.station_data[band]) for band in self.station_data)))
        except Exception as e:
            logger.error('could not load stations file!')
            logger.error(e)

    def save_stations(self):
        logger.info('saving stations file')
        try:
            stations_filepath = os.path.join(self.config['configdir'], 'stations.json')
            with open(stations_filepath, 'w') as file:
                json.dump(self.station_data, file, cls=_station.Serializer, indent=1)
        except Exception as e:
            logger.error('could not load stations file!')
            logger.error(e)

    def load_messages(self):
        logger.info('loading messages file')
        try:
            messages_filepath = os.path.join(self.config['configdir'], 'messages.json')
            if os.path.isfile(messages_filepath):
                with open(messages_filepath, 'r') as file:
                    self.message_data = json.load(file, object_hook=_station.from_json)
                self.flag_message = True
            logger.info('loaded %d messages from file' % (len(self.message_data)))
        except Exception as e:
            logger.error('could not load messages file!')
            logger.error(e)

    def save_messages(self):
        logger.info('saving messages file')
        try:
            messages_filepath = os.path.join(self.config['configdir'], 'messages.json')
            with open(messages_filepath, 'w') as file:
                json.dump(self.message_data, file, cls=_station.Serializer, indent=1)
        except Exception as e:
            logger.error('could not load messages file!')
            logger.error(e)

    #
    # delspots - remove the qth's from canvas (clears spots from map, but they stay in mem)
    #
    def delete_spots(self):
        logger.debug('deleting spots from map')
        if self.canvas is not None:
            for id in self.spots:
                self.canvas.delete(id)
            self.spots.clear()

    def clear(self):
        logger.debug('clearing data')
        self.delete_spots() #TODO dangerous, deleting and quitting leads to all persistet data being lost!
        for band in self.station_data:
            self.station_data[band].clear()
        self.message_data.clear()

    #
    # on_clear - clear canvas and the list that maintains qth's (clears everything)
    #
    def on_clear(self):
        self.clear()

    #
    # on_spot_enter - create lower left textbox when you hover over dot
    #
    def on_spot_enter(self, _):
        item = self.canvas.find_withtag('current')
        tags = self.canvas.gettags(item) # get the tags from the canvas item
        self.show_call_details(tags[0])

    def show_call_details(self, call):
        self.details_window.delete('1.0', 'end') # purge content
        if call is None:
            return

        # replace own station with last heard station in same grid
        if call == constants.RX_CALL:
            stations = [self.station_data[str(band)][call] for band in self.station_data for call in self.station_data[band] if self.station_data[band][call].grid == self.rx_grid]
            if len(stations) == 0:
                return
            stations.sort(key=lambda s: s.time, reverse=True)
            call = stations[0].call

        bands = [band for _, _, band, _ in constants.band_list if call in self.station_data[str(band)]] # one station can transmit on multiple bands simultaneously
        if len(bands) == 0:
            return

        now = datetime.datetime.now()
        stations = [self.station_data[str(band)][call] for band in bands]       # grab tip from click
        stations.sort(key=lambda s: s.time, reverse=True) # sort by time last heard

        field = []
        field.append('Call     %s' % stations[0].call)
        field.append('Grid     %s' % stations[0].grid)

        if self.rx_station is not None:
            field.append(' Range   %.0f km' % (maidenhead.locator_distance(self.rx_station.grid, stations[0].grid) / 1000.0))
            field.append(' Bearing %+d deg' % maidenhead.locator_bearing(self.rx_station.grid, stations[0].grid))

        for i in range(len(stations)):
            field.append('Band     %d m' % stations[i].band)
            field.append(' Report  %s' % stations[i].report)
            if self.agelimit > 24 * 60 * 60: # more than 1 day
                field.append(' Date    %s' % stations[i].time.strftime('%y-%m-%d')) #  show date, too
            field.append(' Time    %s' % stations[i].utc())

            age = (now - stations[i].time).total_seconds()
            age_human_readable = ''
            if age > 24 * 60 * 60:
                age_human_readable += '%dd ' % (age // (24 * 60 * 60))
            if age > 60 * 60:
                age_human_readable += '%02dh ' % ((age % (24 * 60 * 60)) // (60 * 60))
            if age > 60:
                age_human_readable += '%02dmin ' % ((age % (60 * 60)) // 60)
            age_human_readable += '%02dsec' % (age % 60)
            field.append('          %s ago' % age_human_readable)

            if len(stations[i].message) > 0:
                field.append(' Message %s' % stations[i].message)

            same_grid = [call for band in self.station_data for call in self.station_data[band] if self.station_data[band][call].grid == stations[0].grid]
            if len(same_grid) > 1:
                field.append('%+d stations in %s' % (len(same_grid)  - 1, stations[0].grid))

        self.details_window.insert(tk.END, '\n'.join(field))
        self.details_window.configure(height=len(field))

    #
    # on_spot_leave - delete labels for callsign qth you were hovering over
    #
    def on_spot_leave(self, _):
        self.show_call_details(self.selected_call)

    def on_settings(self):
        if self.settings_open:
            return # only one settings window at the same time

        logger.info('opening settings dialog')
        self.settings_open = True
        settings_window = settings.Settings(
            self.master,
            self.config,
            mode=self.mode,
            on_settings_changed=self.save_config
            )
        settings_window.master.bind('<Destroy>', self.on_settings_close)

    def on_settings_close(self, _):
        self.settings_open = False
        logger.debug('settings dialog is now closed')

    def on_detail(self, _):
        item = self.canvas.find_withtag('current')
        tags = self.canvas.gettags(item) # get the tags from the canvas item
        call = tags[0]               # grab tip from click
        self.selected_call = call
        self.show_call_details(call)

    def on_lookup(self, _):
        call = self.selected_call

        if call == constants.RX_CALL:
            # center map around rx station (if possible)
            x, y = maps.project(self.CURMAP, self.rx_station.grid)
            xmin, xmax = self.canvas.xview()
            ymin, ymax = self.canvas.yview()
            x = x * (xmax - xmin) / self.canvas.winfo_width()
            y = y * (ymax - ymin) / self.canvas.winfo_height()
            self.canvas.xview_moveto(x - 0.5 * (xmax - xmin))
            self.canvas.yview_moveto(y - 0.5 * (ymax - ymin))
        else:
            logger.debug('looking up %s on %s' % (call, ['qrz.com', 'hamcall.net'][self.config['lookup']]))
            if self.config['lookup'] == constants.lookup_QRZ:           # get from QRZ with radiobutton 1 set
                webbrowser.open('https://www.qrz.com/db/' + call, new=2)
            elif self.config['lookup'] == constants.lookup_HamCall:         # get from HamCall with radiobutton 2 set
                webbrowser.open('https://hamcall.net/call?callsign=' + call, new=2)

    def on_filter_time_changed(self, *_):
        self.agelimit = constants.age_labels[self.tclick.get()]    # convert that to seconds
        self.flag_filter = True
        logger.debug('age limit changed to %d seconds' % self.agelimit)

    def on_filter_band_changed(self, *_):
        self.bandfilter = int(constants.band_labels[self.bclick.get()])                     # set bandfilter
        self.flag_filter = True
        logger.debug('band filter changed to %d m band' % self.bandfilter)

    def on_change_map(self, *_):
        logger.debug('map is changing')
        region = self.mapidx.get()
        self.save_map_position()
        self.change_map(region)
        self.move_map(None)

    def move_map(self, _):
        # apply new maps old settings restoring x,y position
        a, b = self.mto[self.CURMAP + str(self.map_scale.get())]
        logger.debug('moving canvas with map %s to (%f, %f)' % (self.CURMAP, a, b))
        self.canvas.xview_moveto(a)
        self.canvas.yview_moveto(b)

    #
    # change_map - switches region map and redraws buttons, labels, maps, qth's
    #
    def change_map(self, region=None):
        if region is None:
            region = self.CURMAP

        self.CURMAP = region           # now switch maps
        logger.debug('changing map to %s with scale x%d' % (self.CURMAP, 1 + self.map_scale.get()))
        
        # load image for this map
        images = None
        if self.CURMAP == 'WM':
            images = self.bg_w
        elif self.CURMAP == 'NA':
            images = self.bg_na
        elif self.CURMAP == 'SA':
            images = self.bg_sa
        elif self.CURMAP == 'EU':
            images = self.bg_eu
        elif self.CURMAP == 'AF':
            images = self.bg_af
        elif self.CURMAP == 'AS':
            images = self.bg_as
        elif self.CURMAP == 'OC':
            images = self.bg_oc

        key = '%s-%s' % ('dark' if self.dark_mode.get() == 1 else 'light', 'large' if self.map_scale.get() == 1 else 'small')
        image = images[key]
        self.canvas.delete('MAP')
        self.canvas.create_image(image.width() // 2, image.height() // 2, image=image, tag='MAP')
        self.delete_spots()

        # draw range rings (based on grids...)
        if self.range_rings.get() == 1 and self.CURMAP == 'WM' and self.rx_station is not None:
            rx_lat, rx_lon = maidenhead.locator2latlon(self.rx_station.grid)
            line_color = 'black' if self.dark_mode.get() == 0 else 'gray'
            for r in [1000, 2500, 5000, 10000, 15000]: # km
                old_x = None
                old_y = None
                for phi in range(0, 360, 1):
                    dlat = math.cos(math.radians(phi))
                    dlon = math.sin(math.radians(phi))
                    r0 = 1.0
                    d0 = maidenhead.latlon_distance(rx_lat, rx_lon, rx_lat + dlat * r0, rx_lon + dlon * r0) - 1000 * r
                    r1 = 2.0
                    for _ in range(100):
                        d1 = maidenhead.latlon_distance(rx_lat, rx_lon, rx_lat + dlat * r1, rx_lon + dlon * r1) - 1000 * r
                        if abs(d1) < 50 * 1000:
                            break
                        dr = (r1 - r0) / (d1 - d0 + 1.0e-4) * d1 # Secant method
                        r0 = r1
                        d0 = d1
                        r1 = r1 - min(5.0, max(-5.0, dr))
                    if abs(d1) > 50 * 1000:
                        old_x = None
                        old_y = None
                        continue

                    grid = maidenhead.latlon2locator(rx_lat + dlat * r1, rx_lon + dlon * r1)
                    xcoor, ycoor = maps.project(self.CURMAP, grid)  # fetch coordinates

                    if xcoor == -1:                   # doesn't belong on current map
                        old_x = None
                        old_y = None
                        continue

                    xcoor /= 2 - self.map_scale.get()
                    ycoor /= 2 - self.map_scale.get()

                    if old_x is not None and (old_x != xcoor or old_y != ycoor):
                        self.canvas.create_line(
                            old_x,
                            old_y,
                            xcoor,
                            ycoor,
                            fill=line_color,
                            tag='MAP'
                            )
                    old_x = xcoor
                    old_y = ycoor

                    if phi == 90 or phi == 270:
                        self.canvas.create_text(
                            xcoor,
                            ycoor,
                            text='%d km' % r,
                            anchor='n' if phi < 180 else 'n',
                            angle=90 if phi < 180 else -90,
                            fill=line_color,
                            tag='MAP'
                            )

        self.flag_map = True

    #
    # flashes a locator over the grid location when user clicks on grid in call/grid window
    #
    def listflashgrid(self, event):
        # grab the grid data underneath our mouse when we click...
        index = event.widget.index('@%s,%s' % (event.x, event.y))
        tk.SEL_FIRST = index + 'wordstart'
        tk.SEL_LAST = index + 'wordend'
        word = self.text_wd.get(tk.SEL_FIRST, tk.SEL_LAST)

        if index.startswith('1.'): # header clicked
            # reproject index to column of table
            c = 0
            pos = int(index[2:])
            keys = list(self.row_division.keys())
            while c < len(self.row_division):
                if pos < self.row_division[keys[c]]:
                    break # found
                else:
                    pos -= self.row_division[keys[c]]
                    c += 1

            # set sorting criteria and indicate need for an update
            attr = keys[c]
            if self.sortby != attr:
                self.sortby = attr # new sorting order
            else:
                self.sortby = '!' + self.sortby # reverse sorting order
            self.flag_list = True
        elif word in [call for band in self.station_data for call in self.station_data[band]]:
            self.selected_call = word
            self.show_call_details(word)
        else:
            # sanity check grid data
            if maidenhead.locator_valid(word):
                self.flashgrid(word)
        #    grid = [self.station_data[band][call].grid for band in self.station_data for call in self.station_data[band] if self.station_data[band][call].call == word][0]
        #    self.flashgrid(grid)

    def listlookup(self, event):
        # grab the grid data underneath our mouse when we click...
        index = event.widget.index('@%s,%s' % (event.x, event.y))
        tk.SEL_FIRST = index + 'wordstart'
        tk.SEL_LAST = index + 'wordend'
        word = self.text_wd.get(tk.SEL_FIRST, tk.SEL_LAST)

        if word == self.selected_call:
            self.on_lookup(word)

    def flashgrid(self, grid):
        logger.debug('flashing %s on map' % grid)
        xcoor, ycoor = maps.project(self.CURMAP, grid)  # get x,y for current map and grid locale

        if xcoor == -1:                   # doesn't belong on current map
            return

        xcoor /= 2 - self.map_scale.get()
        ycoor /= 2 - self.map_scale.get()

        # first circle is big to attract user attention
        itag = self.canvas.create_oval(xcoor - 16, ycoor - 16, xcoor + 32, ycoor + 32, width=1, fill='firebrick1')
        self.wndo.update()
        time.sleep(0.1)
        self.canvas.delete(itag)

        # second circle smaller
        itag = self.canvas.create_oval(xcoor - 4, ycoor - 4, xcoor + 12, ycoor + 12, width=1, fill='firebrick1')
        self.wndo.update()
        time.sleep(0.1)
        self.canvas.delete(itag)

        # last circle lands on map to show location of grid...
        itag = self.canvas.create_oval(xcoor, ycoor, xcoor + 8, ycoor + 8, width=1, fill='firebrick1')
        self.wndo.update()
        time.sleep(0.1)
        self.canvas.delete(itag)

    #
    # set the shutdown flag for ft8mapper...
    #
    def confirm_quit(self):
        logger.debug('request to quit by user. asking for confirmation...')
        if tk.messagebox.askokcancel(title=self.version.APPNAME, message='Really quit %s?' % self.version.APPNAME):
            logger.info('quit by user')
            self.close()

    def close(self):
        logger.info('close GUI')
        self.save_map_position()
        self.save_config()

        if not self.example_stations: # when using example station data, do not save them!
            self.save_stations()
            self.save_messages()

        # important: stop network while ui is still alive
        # because callbacks will otherwise try to access tkinter while no main loop is running
        if self.on_exit is not None:
            self.on_exit()
        self.wndo.destroy()  # destroy window and kill app

    # canvas scroll function
    def scrollfilt(self, _):
        logger.debug('update scrollbars')
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))

    def drag_map(self, e):
        if self.last_mouse is not None:
            dx = e.x - self.last_mouse[0]
            dy = e.y - self.last_mouse[1]
            self.canvas.xview_scroll(-dx, 'units')
            self.canvas.yview_scroll(-dy, 'units')
        self.last_mouse = [e.x, e.y]

    def drag_map_end(self, _):
        self.last_mouse = None

    def zoom_map(self, event, level=None):
        if level is None:
            level = 1 if event.delta > 1 else 0 # based on mouse wheel (Windows only)

        if level == self.map_scale.get():
            return
        self.map_scale.set(level)
        self.change_map_scale()

    def on_resize(self, e):
        if hasattr(self, 'plots') and e.widget == self.plots:
            self.flag_replot = True

    def change_dark_mode(self):
        self.mode = 'dark' if self.dark_mode.get() == 1 else 'light'
        self.plots.config(bg=self.master.cget('bg'))
        self.root.tk.call("set_theme", self.mode)
        self.change_map()

    def save_map_position(self, scale=None):
        if scale is None:
            scale = self.map_scale.get()
        x = self.canvas.xview()            # record x,y values
        y = self.canvas.yview()
        self.mto[self.CURMAP + str(scale)] = (x[0], y[0])     # save current window settings for previous (!) map scale

    def change_map_scale(self):
        self.save_map_position(1 - self.map_scale.get())
        self.change_map()
        self.scrollfilt(None) # adjust scrollbars
        self.move_map(None)

    def configure_canvas(self, e):
        if not self.once:
            self.change_map()
            self.scrollfilt(None)
            self.move_map(None)
            self.once = True

    def create_ui(self):
        logger.debug('creating ui')
        self.wndo.protocol('WM_DELETE_WINDOW', self.confirm_quit)   # catch if they hit windows 'X'
        self.wndo.geometry(self.config['window']['position'])
        self.wndo.title(self.version.APPNAME)    # title
        self.wndo.bind("<Configure>", self.on_resize)

        # images used for maps
        # generate dark mode variants on the fly
        def load_map_image(filepath):
            with Image.open(filepath) as image:
                images = {}
                images['light-large'] = ImageTk.PhotoImage(image)
                images['light-small'] = ImageTk.PhotoImage(image.resize((image.width // 2, image.height // 2)))
                image = image.convert('HSV')
                h, s, v = image.split()
                v = v.point(lambda p: 255 - p) # invert value channel only
                image = Image.merge('HSV', [h, s, v])
                images['dark-large'] = ImageTk.PhotoImage(image)
                images['dark-small'] = ImageTk.PhotoImage(image.resize((image.width // 2, image.height // 2)))
            return images
        self.bg_w  = load_map_image(os.path.join(self.config['configdir'], 'maps', 'wm.png'))
        self.bg_na = load_map_image(os.path.join(self.config['configdir'], 'maps', 'wm-na.png'))
        self.bg_sa = load_map_image(os.path.join(self.config['configdir'], 'maps', 'wm-sa.png'))
        self.bg_eu = load_map_image(os.path.join(self.config['configdir'], 'maps', 'wm-eu.png'))
        self.bg_af = load_map_image(os.path.join(self.config['configdir'], 'maps', 'wm-af.png'))
        self.bg_as = load_map_image(os.path.join(self.config['configdir'], 'maps', 'wm-as.png'))
        self.bg_oc = load_map_image(os.path.join(self.config['configdir'], 'maps', 'wm-oc.png'))

        # bottom bar
        wframe = ttk.Frame(self.wndo)
        wframe.grid(row=3, column=0, columnspan=4, sticky='swe')

        # canvas
        self.canvas = tk.Canvas(
            self.wndo,
            bd=0,
            highlightthickness=0,
            xscrollincrement='1',
            yscrollincrement='1'
        )
        self.canvas.bind('<Configure>', self.configure_canvas)
        self.canvas.bind('<B1-Motion>', self.drag_map)
        self.canvas.bind('<ButtonRelease-1>', self.drag_map_end)
        self.canvas.bind("<MouseWheel>", self.zoom_map)
        self.canvas.bind("<4>", partial(self.zoom_map, level=1))
        self.canvas.bind("<5>", partial(self.zoom_map, level=0))

        yscrollbar = ttk.Scrollbar(self.wndo, orient='vertical')     # set up scrollbar y-axis
        yscrollbar.grid(row=0, rowspan=2, column=1, sticky='ns')
        yscrollbar.config(command=self.canvas.yview)

        xscrollbar = ttk.Scrollbar(self.wndo, orient='horizontal')   # set up scrollbar x-axis
        xscrollbar.grid(row=2, column=0, sticky='we')
        xscrollbar.config(command=self.canvas.xview)

        self.canvas.configure(scrollregion=self.canvas.bbox('all'))       # all of canvas is scrolled
        self.canvas.config(xscrollcommand=xscrollbar.set, yscrollcommand=yscrollbar.set)
        self.canvas.grid(row=0, column=0, rowspan=2, sticky='nswe')

        # list window
        self.fs = tkFont.Font(family='Courier', size=10, weight='normal')

        self.text_wd = tk.Text(self.wndo, font=self.fs)
        self.text_wd.grid(column=2, row=0, sticky='nsew')
        self.text_wd.bind('<Button-1>', self.listflashgrid)
        self.text_wd.bind('<Double-Button-1>', self.listlookup)

        vscrollbar = ttk.Scrollbar(self.wndo, orient='vertical')   # make scrollable
        vscrollbar.grid(column=3, row=0, sticky='ns')
        vscrollbar.config(command=self.text_wd.yview)
        self.text_wd.config(yscrollcommand=vscrollbar.set)

        # detail window
        self.details_window = tk.Text(self.wndo, font=self.fs, width=constants.details_width, height=10, wrap='none')
        self.details_window.grid(column=2, row=1, columnspan=2, sticky='nsew')

        # resize canvas and table when resizing window
        self.wndo.grid_rowconfigure(0, weight=1)
        self.wndo.grid_columnconfigure(0, weight=1)
        self.running = True

        # drop in the regional buttons at bottom of screen
        group_maps = ttk.LabelFrame(wframe, text='Map')
        group_maps.pack(side='left', anchor='n')

        drop_map = ttk.Combobox(group_maps, textvariable=self.mapidx, values=list(['WM', 'NA', 'SA', 'EU', 'AF', 'AS', 'OC']), state='readonly', width=2)
        drop_map.grid(row=0, column=0, sticky='we', padx=4)

        self.check_map_scale = ttk.Checkbutton(group_maps, text='large map', command=self.change_map_scale, variable=self.map_scale)
        self.check_map_scale.grid(row=1, column=0, sticky='we', padx=4, pady=4)
        self.check_range_rings = ttk.Checkbutton(group_maps, text='range rings', command=self.change_map, variable=self.range_rings)
        self.check_range_rings.grid(row=2, column=0, sticky='we', padx=4, pady=4)

        # add the 'Last:' label and the dropdown menu
        group_filter = ttk.LabelFrame(wframe, text='View')
        group_filter.pack(side='left', anchor='n')

        drop_band = ttk.Combobox(group_filter, textvariable=self.bclick, values=list(constants.band_labels.keys()), state='readonly', width=max(len(k) for k in constants.band_labels.keys()))
        drop_band.grid(row=0, column=0, sticky='we', padx=4)
        drop_time = ttk.Combobox(group_filter, textvariable=self.tclick, values=list(constants.age_labels.keys()), state='readonly', width=max(len(k) for k in constants.age_labels.keys()))
        drop_time.grid(row=1, column=0, sticky='we', padx=4)
        self.check_dark_mode = ttk.Checkbutton(group_filter, text='dark mode', command=self.change_dark_mode, variable=self.dark_mode)
        self.check_dark_mode.grid(row=2, column=0, sticky='we', padx=4, pady=4)

        # add statistics group
        group_stats = ttk.LabelFrame(wframe, text='Statistics')
        group_stats.pack(side='left', anchor='n', ipady=4)

        # label
        ttk.Label(group_stats, text='Max. range:').grid(row=0, column=0, sticky='we', padx=(4,0))
        ttk.Label(group_stats, text='Decode rate:').grid(row=1, column=0, sticky='we', padx=(4,0))
        ttk.Label(group_stats, text='Heard:').grid(row=2, column=0, rowspan=2, sticky='we', padx=(4,0))
        ttk.Label(group_stats, text='Time span:').grid(row=4, column=0, sticky='we', padx=(4,0))
        # value
        self.label_maxrange = ttk.Label(group_stats,   text='?', anchor='e', width=5)
        self.label_decoderate = ttk.Label(group_stats, text='?', anchor='e')
        self.label_nostations = ttk.Label(group_stats, text='?', anchor='e')
        self.label_nosquares = ttk.Label(group_stats,  text='?', anchor='e')
        self.label_timespan = ttk.Label(group_stats,  text='?', anchor='e')
        self.label_maxrange.grid(row=0, column=1, sticky='we', padx=4, pady=0)
        self.label_decoderate.grid(row=1, column=1, sticky='we', padx=4, pady=0)
        self.label_nostations.grid(row=2, column=1, sticky='we', padx=4, pady=0)
        self.label_nosquares.grid(row=3, column=1, sticky='we', padx=4, pady=0)
        self.label_timespan.grid(row=4, column=1, columnspan=2, sticky='we', padx=4, pady=0)
        # unit
        ttk.Label(group_stats, text='km').grid(row=0, column=2, sticky='we', padx=(0,4))
        ttk.Label(group_stats, text='msg/min').grid(row=1, column=2, sticky='we', padx=(0,4))
        ttk.Label(group_stats, text='stations').grid(row=2, column=2, sticky='we', padx=(0,4))
        ttk.Label(group_stats, text='squares').grid(row=3, column=2, sticky='we', padx=(0,4))

        # clear and quit buttons added
        group_general = ttk.LabelFrame(wframe, text='Program')
        group_general.pack(side='right', anchor='n')

        b = [None] * 3
        b[0] = ttk.Button(group_general, text='Settings', command=self.on_settings)
        #b[1] = ttk.Button(group_general, text='Load...', command=self.load_logfile)
        b[2] = ttk.Button(group_general, text='Quit', command=self.confirm_quit)
        b[0].grid(row=0, column=0, sticky='we', padx=2, pady=2)
        #b[1].grid(row=1, column=0, sticky='we', padx=2, pady=2)
        b[2].grid(row=2, column=0, sticky='we', padx=2, pady=2)

        # options for list window
        group_listing = ttk.LabelFrame(wframe, text='List')
        group_listing.pack(side='right', anchor='n')

        check_grid     = ttk.Checkbutton(group_listing, text='Grid',     command=self.change_list, variable=self.list_grid)
        check_band     = ttk.Checkbutton(group_listing, text='Band',     command=self.change_list, variable=self.list_band)
        check_report   = ttk.Checkbutton(group_listing, text='Report',   command=self.change_list, variable=self.list_report)
        check_range    = ttk.Checkbutton(group_listing, text='Range',    command=self.change_list, variable=self.list_range)
        check_age      = ttk.Checkbutton(group_listing, text='Age',      command=self.change_list, variable=self.list_age)
        check_msgs     = ttk.Checkbutton(group_listing, text='Msgs',     command=self.change_list, variable=self.list_msgs)
        check_last_msg = ttk.Checkbutton(group_listing, text='Last Msg', command=self.change_list, variable=self.list_last_msg)
        check_grid     .grid(row=0, column=0, sticky='we')
        check_band     .grid(row=1, column=0, sticky='we')
        check_report   .grid(row=2, column=0, sticky='we')
        check_range    .grid(row=0, column=1, sticky='we')
        check_age      .grid(row=1, column=1, sticky='we')
        check_msgs     .grid(row=2, column=1, sticky='we')
        check_last_msg .grid(row=3, column=0, columnspan=2, sticky='we')

        # add plot area last to fill space
        group_plot = tk.LabelFrame(wframe, text='Plot')
        group_plot.pack(side='left', anchor='n', fill='both', expand=True, pady=2)

        group_plot_control = tk.Frame(group_plot)
        group_plot_control.pack(side='bottom', anchor='w')
        graph_metric = ttk.Combobox(group_plot_control, textvariable=self.plotmetric, values=list(constants.plot_metrics.keys()), state='readonly', width=11)
        graph_time = ttk.Combobox(group_plot_control, textvariable=self.plottime, values=list(constants.age_labels.keys()), state='readonly', width=max(len(k) for k in constants.age_labels.keys()))
        graph_metric.grid(row=0, column=0)
        graph_time.grid(row=0, column=1)

        self.plots = tk.Canvas(group_plot, bg=self.master.cget('bg'), width=1, height=1)
        self.plots.pack(fill='both', expand=True)

        self.wndo.after(constants.UPDATE_PERIOD, self.update)

    def change_plot(self, *_):
        self.plotx = constants.age_labels[self.plottime.get()]
        self.ploty = constants.plot_metrics[self.plotmetric.get()]
        self.flag_replot = True

    def change_list(self, *_):
        self.flag_list = True

    def plot(self, x0, y0, x1, y1, fcol, call, lift=False):
        spot = self.canvas.find_withtag(call)
        if len(spot) == 0:
            x0 /= 2 - self.map_scale.get()
            y0 /= 2 - self.map_scale.get()
            x1 /= 2 - self.map_scale.get()
            y1 /= 2 - self.map_scale.get()
            if self.CURMAP != 'WM':
                spot = self.canvas.create_rectangle(
                    x0,
                    y0,
                    x1 - 1,
                    y1 - 1,
                    fill=fcol,
                    outline='black',
                    tag=call
                )
            else:
                spot = self.canvas.create_oval(
                    x0 - constants.wm_spot_radius,
                    y0 - constants.wm_spot_radius,
                    x0 + constants.wm_spot_radius - 1,
                    y0 + constants.wm_spot_radius - 1,
                    fill=fcol,
                    outline='black',
                    tag=call
                )
            self.canvas.tag_bind(spot, '<Enter>', self.on_spot_enter)  # if touched call on_spot_enter
            self.canvas.tag_bind(spot, '<Leave>', self.on_spot_leave)  # when untouched
            self.canvas.tag_bind(spot, '<Button-1>', self.on_detail) # when clicked
            self.canvas.tag_bind(spot, '<Double-Button-1>', self.on_lookup) # when clicked
            self.spots.add(call)
        else:
            spot = spot[0] # already plotted, but allow a lift
        if lift:
            self.canvas.tag_raise(spot)

    def plot_station(self, caller, grid, band):
        band_color = constants.band_colors[band]   # select bands color for plotting

        # calculate coordinates
        x0, y0 = maps.project(self.CURMAP, grid + 'aa')
        x1, y1 = maps.project(self.CURMAP, grid + 'rr')

        if x0 == -1 or x1 == -1:                   # doesn't belong on current map
            return True

        self.plot(x0, y0, x1, y1, band_color, caller)

    def hide_station(self, call):
        if call in self.spots:
            self.canvas.delete(call)
            self.spots.remove(call)

    def sort_listwin(self, tree, col, descending):
        data = [(tree.set(child, col), child) for child in tree.get_children('')]
        data.sort(reverse=descending)
        for ix, (_, child) in enumerate(data):
            tree.move(child, '', ix)
        tree.heading(col, command=lambda _col=col:self.sort_listwin(tree, col, int(not descending)))

    def update_listwin(self):
        logger.debug('updating listwin')
        now = datetime.datetime.now()

        stations = list(self.station_data[band][call] for band in self.station_data for call in self.station_data[band])
        stations = [station for station in stations if station.band == self.bandfilter or self.bandfilter == constants.any_band] # filter by band
        stations = [station for station in stations if now - station.time <= datetime.timedelta(seconds=self.agelimit)] # filter by age
        stations.sort(key=lambda entry: int(entry.band), reverse=True) # sort by band

        pos = self.text_wd.yview()
        self.text_wd.delete('1.0', 'end') # purge content

        if len(stations) == 0: # no data after view filter
            no_data = 'no data'
            self.text_wd.insert(tk.END, no_data)
            self.text_wd.configure(width=len(no_data))
            return
        
        visible_columns = []
        visible_columns.append('Call')
        if self.list_grid.get():
            visible_columns.append('Grid')
        if self.list_band.get():
            visible_columns.append('Band')
        if self.list_report.get():
            visible_columns.append('Report')
        if self.list_range.get():
            visible_columns.append('Range')
        if self.list_age.get():
            visible_columns.append('Age')
        if self.list_msgs.get():
            visible_columns.append('Msgs')
        if self.list_last_msg.get():
            visible_columns.append('Last Msg')

        if 'Msgs' in visible_columns:
            message_count = {entry.call: len([m for m in self.message_data if m.call == entry.call]) for entry in stations}
        if 'Range' in visible_columns:
            distances = {entry.call: maidenhead.locator_distance(self.rx_station.grid, entry.grid) for entry in stations}

        # split message into tokens
        # so that each "word" can be aligned horizontally later
        message_tokens = {}
        for station in stations:
            tokens = station.message.split(' ')
            undo = False
            if len(tokens) >= 2 and tokens[0] == 'CQ' and len(tokens[1]) == 2: # CQ <two letters>
                undo = True
            if len(tokens) >= 2 and tokens[0] == 'CQ' and len(tokens[1]) in [3, 4] and all(not t.isdigit() for t in tokens[1]): # CQ <three or four letters but no digits>
                undo = True
            if undo:
                tokens = [' '.join(tokens[:2]),] + tokens[2:] # join back together
            message_tokens[station.call] = tokens
        max_tokens = max(len(tokens) for tokens in message_tokens.values())
        for call in message_tokens:
            while len(message_tokens[call]) < max_tokens:
                message_tokens[call].append('')
        max_token_length = [max(len(tokens[t]) for tokens in message_tokens.values()) for t in range(max_tokens)]

        # sort data first
        if self.sortby.endswith('Call'): # by call
            stations.sort(key=lambda entry: entry.call)
        elif self.sortby.endswith('Msgs'): # by message count
            message_count = {entry.call: len([m for m in self.message_data if m.call == entry.call]) for entry in stations}
            stations.sort(key=lambda entry: message_count[entry.call], reverse=True)
        elif self.sortby.endswith('Range') and self.rx_station is not None: # by distance to receiver location, i.e. range
            distances = {entry.call: maidenhead.locator_distance(self.rx_station.grid, entry.grid) for entry in stations}
            stations.sort(key=lambda entry: distances[entry.call])
        elif self.sortby.endswith('Report'): # by report/snr
            stations.sort(key=lambda entry: entry.report, reverse=True)
        elif self.sortby.endswith('Age'): # by age of last message
            stations.sort(key=lambda entry: entry.time, reverse=True)
        if self.sortby.startswith('!'):
            stations.reverse()

        # collect data for all rows
        data = []
        data.append(visible_columns)
        for station in stations:
            row = []
            row.append(station.call)
            if self.list_grid.get():
                row.append(station.grid)
            if self.list_band.get():
                row.append('%3dm' % station.band)
            if self.list_report.get():
                row.append('%+d' % station.report)
            if self.list_range.get():
                row.append('%5.0fkm' % (distances[station.call] / 1000))
            if self.list_age.get():
                row.append('%ds' % (now - station.time).total_seconds())
            if self.list_msgs.get():
                row.append('%d' % message_count[station.call])

            if self.list_last_msg.get():
                message = ''
                for t in range(max_tokens): # iterate latest message's tokens
                    message += ' ' + message_tokens[station.call][t].ljust(max_token_length[t]) # pad to max token length for horizontal alignment
                row.append(message)

            data.append(row)

        # adjust width of columns to content
        longest = [max([len(row[col]) for row in data]) for col in range(len(visible_columns))]
        row_format = ' '.join(['%%-%ds' % longest[c] for c in range(len(visible_columns))])
        for r in range(len(data)):
            data[r] = row_format % tuple(data[r])
        self.row_division = {visible_columns[col]: longest[col] for col in range(len(visible_columns))}

        # insert bold header
        self.text_wd.insert(tk.END, '\n'.join(data))
        self.text_wd.configure(width=len(data[0]))
        self.text_wd.yview_moveto(pos[0])

    def update_statwin(self):
        logger.debug('updating statwin')
        # filter based on viewing configuration (band and 'last')
        now = datetime.datetime.now()
        band_filtered_data = self.message_data
        if self.bandfilter != constants.any_band:
            band_filtered_data = [m for m in band_filtered_data if m.band == self.bandfilter]
        filtered_data = [m for m in band_filtered_data if now - m.time < datetime.timedelta(seconds=self.agelimit)]
        last_minute = [m for m in filtered_data if now - m.time < datetime.timedelta(minutes=1)]

        maxrange = None
        if self.rx_station is not None and len(filtered_data) > 0:
            ranges = [maidenhead.locator_distance(self.rx_station.grid, m.grid) / 1000.0 for m in filtered_data]
            maxrange = max(ranges) # km
        decoderate = len(last_minute)
        nostations = len(set([m.call for m in filtered_data]))
        nosquares = len(set([m.grid for m in filtered_data]))
        timespan = (filtered_data[-1].time if len(filtered_data) > 0 else now) - (filtered_data[0].time if len(filtered_data) > 0 else now)

        self.label_maxrange.config(text=('%.0f' % maxrange) if maxrange is not None else '?')
        self.label_maxrange.bind('<Button-1>', lambda _: self.flashgrid(filtered_data[ranges.index(maxrange)].grid))
        self.label_decoderate.config(text='%d' % decoderate)
        self.label_nostations.config(text='%d' % nostations)
        self.label_nosquares.config(text='%d' % nosquares)
        self.label_timespan.config(text='%2d h %02d min %02d sec' % (timespan.total_seconds() // 3600, (timespan.total_seconds() / 60) % 60, timespan.total_seconds() % 60))

        # draw plot window
        self.plots.delete('GRAPH')
        line_color = ttk.Style().lookup(ttk.Button().winfo_class(), "foreground", default="gray")
        axes_color = ttk.Style().lookup(ttk.Frame().winfo_class(), "foreground", default="black")
        text_color = ttk.Style().lookup(ttk.Label().winfo_class(), "foreground", default="black")
        graph_data = [m for m in band_filtered_data if now - m.time < datetime.timedelta(seconds=self.plotx)]
        if len(graph_data) > 0:
            if self.plots.winfo_width() == 1: # widget not fully drawn yet
                self.flag_replot = True # try again
                logging.debug('requesting replot again')
                return

            t_res, tic_res, label_res, label_unit = constants.plot_resolutions[self.plotx]
            num_bins = self.plotx // t_res
            now.fromtimestamp(now.timestamp() // t_res * t_res)

            y = [[] for _ in range(num_bins)]
            y_default = 0.0
            if self.ploty == 'M': # mean number of messages
                total_min = 0
                total_max = None
                min_mean_max = False
                histogram = [[] for _ in range(0, self.plotx, t_res)] # number of messages per minute
                for m in graph_data:
                    bin = (now - m.time).total_seconds() / t_res
                    bin = int(bin)
                    histogram[bin].append(1)
                for b in range(len(histogram)):
                    bin = b
                    bin = int(bin)
                    y[bin].append(len(histogram[b]) * 60 / t_res)
            elif self.ploty == 'R': # report/SNR
                total_min = None # -49
                total_max = None #  50
                min_mean_max = True
                for m in graph_data:
                    bin = (now - m.time).total_seconds() / t_res
                    bin = int(bin)
                    y[bin].append(m.report)
            elif self.ploty == 'D': # distance to (current!) receiver location
                total_min = 0
                total_max = None
                min_mean_max = True
                for m in graph_data:
                    bin = (now - m.time).total_seconds() / t_res
                    bin = int(bin)
                    if self.rx_station is not None:
                        distance = maidenhead.locator_distance(self.rx_station.grid, m.grid) / 1000.0
                    else:
                        distance = y_default
                    y[bin].append(distance)
            elif self.ploty == 'S': # number of unique stations heard
                total_min = 0
                total_max = None
                min_mean_max = False
                unique = [set() for _ in range(num_bins)]
                for bin in range(num_bins):
                    y[bin].append(y_default)
                for m in graph_data:
                    bin = (now - m.time).total_seconds() / t_res
                    bin = int(bin)
                    if m.call not in unique[bin]:
                        y[bin][0] += 1
                        unique[bin].add(m.call)
            elif self.ploty == 'G': # number of unique grids heard
                total_min = 0
                total_max = None
                min_mean_max = False
                unique = [set() for _ in range(num_bins)]
                for bin in range(num_bins):
                    y[bin].append(y_default)
                for m in graph_data:
                    bin = (now - m.time).total_seconds() / t_res
                    bin = int(bin)
                    if m.grid not in unique[bin]:
                        y[bin][0] += 1
                        unique[bin].add(m.grid)

            # calculate min, mean and max
            y_mean = [(sum(x) / len(x)) if len(x) > 0 else y_default for x in y]
            y_min  = [min(x) if len(x) > 0 else y_default for x in y]
            y_max  = [max(x) if len(x) > 0 else y_default for x in y]
            y = [y_max, y_mean, y_min]
            if total_min is None:
                total_min = min(y_min)
            if total_max is None:
                total_max = max(y_max)

            # labels
            # estimate size now
            # and create them later
            # when all remaining dimensions are known
            text_pad = 2
            ytics_format = '%.1f' if self.ploty == 'M' else '%d'
            label_x_max = self.plots.create_text(text_pad, text_pad, text=ytics_format % total_max, fill='black', tags='GRAPH', anchor='nw', justify='right') # maximum on y-axis
            label_x_min = self.plots.create_text(text_pad, self.plots.winfo_height() - 2, text=ytics_format % total_min, fill='black', tags='GRAPH', anchor='sw', justify='right') # minimum on y-axis
            bbox_x_max = self.plots.bbox(label_x_max)
            bbox_x_min = self.plots.bbox(label_x_min)
            label_width  = max([bbox_x_max[2] - bbox_x_max[0], bbox_x_min[2] - bbox_x_min[0]])
            label_height  = max([bbox_x_max[3] - bbox_x_max[1], bbox_x_min[2] - bbox_x_min[0]])
            self.plots.delete(label_x_max)
            self.plots.delete(label_x_min)

            # build graph
            #TODO round wall clock time
            pad = 4      # padding within the canvas
            bin_pad = 2  # bars are drawn a bit smaller so they do not touch
            tic_size = 3 # half length of tics on axes
            left_pad = pad + label_width + text_pad    # area for y labels
            bottom_pad = pad + label_height + text_pad # area for x labels
            usable_width = self.plots.winfo_width() - pad - left_pad     # width of graph area
            usable_height = self.plots.winfo_height() - pad - bottom_pad # height of graph area
            bin_width = (usable_width - 2 * bin_pad) / num_bins
            def value_to_screen_x(x):
                return left_pad + (usable_width - 2 * bin_pad) - int(x * bin_width) + bin_pad
            def value_to_screen_y(y):
                return pad + usable_height - (y - total_min) / (total_max - total_min) * usable_height
            zero_y = value_to_screen_y(0)
            min_y = value_to_screen_y(total_min)
            max_y = value_to_screen_y(total_max)
            min_x = value_to_screen_x(num_bins)
            max_x = value_to_screen_x(0)
            for b in range(num_bins):
                # bin b corresponds to the time from b * t_res to (b + 1) * t_res in the past
                # bins are drawn from right (present) to left (past)
                bin_x_left = value_to_screen_x(b + 1) + bin_pad
                bin_x_right = bin_x_left + int(bin_width) - 2 * bin_pad # enforce constant width, equal to value_to_screen_x(b) - bin_pad except for rounding errors
                draw_order = sorted([[s, y[s][b]] for s in range(len(y))], key=lambda x: abs(x[1]), reverse=True) # draw largest boxes first
                for s, y_s in draw_order:
                    plot_y = value_to_screen_y(y_s)
                    self.plots.create_rectangle(
                        bin_x_left,
                        zero_y,
                        bin_x_right + 1,
                        plot_y + 1,
                        fill=['green', 'orange', 'red'][s] if min_mean_max else line_color,
                        outline='',
                        tags='GRAPH'
                    )

            # axes
            self.plots.create_line(min_x, zero_y, max_x, zero_y, fill=axes_color, tag='GRAPH') # x-axis
            self.plots.create_line(min_x, min_y, min_x, max_y, fill=axes_color, tag='GRAPH') # y-axis

            # x-tics
            for b in range(0, num_bins, tic_res // t_res):
                x = value_to_screen_x(b)
                self.plots.create_line(x, zero_y - tic_size, x, zero_y + tic_size, fill=axes_color, tag='GRAPH')
                self.plots.create_text(x, min_y + text_pad, text='%d%s' % ((b * t_res) // label_res, label_unit), fill=text_color, tags='GRAPH', anchor='ne')

            # y-tics
            self.plots.create_line(min_x - tic_size, min_y, min_x + tic_size, min_y, fill=axes_color, tag='GRAPH')
            self.plots.create_line(min_x - tic_size, max_y, min_x + tic_size, max_y, fill=axes_color, tag='GRAPH')
            self.plots.create_text(left_pad - text_pad, max_y, text=ytics_format % total_max, fill=text_color, tags='GRAPH', anchor='ne') # maximum on y-axis
            self.plots.create_text(left_pad - text_pad, min_y, text=ytics_format % total_min, fill=text_color, tags='GRAPH', anchor='ne') # minimum on y-axis

            self.flag_replot = False
        else:
            self.plots.create_text(2, 2, text='no data', fill=text_color, tags='GRAPH', anchor='nw')

    def redraw(self):
        now = datetime.datetime.now()
        
        for band in self.station_data:
            for call in self.station_data[band]:
                station = self.station_data[band][call]
                if self.bandfilter != constants.any_band and int(band) != self.bandfilter:
                    self.hide_station(station.call) # band does not match current view filter
                elif now - station.time > datetime.timedelta(seconds=self.agelimit):
                    self.hide_station(station.call) # too old
                else:
                    self.plot_station(station.call, station.grid, station.band)

        if self.rx_station is not None:
            # plot rx station
            x0, y0 = maps.project(self.CURMAP, self.rx_station.grid + 'aa')  # fetch coordinates
            x1, y1 = maps.project(self.CURMAP, self.rx_station.grid + 'rr')  # fetch coordinates
            if x0 == -1 or x1 == -1:                   # doesn't belong on current map
                return True
            self.plot(x0, y0, x1, y1, 'white', self.rx_station.call, lift=True)

    def remove_old_data(self):
        now = datetime.datetime.now()
        if self.last_remove_old_data is not None and now - self.last_remove_old_data < datetime.timedelta(minutes=constants.CLEAN_PERIOD):
            return # limit frequency of cleanup

        threshold = datetime.timedelta(seconds=constants.MAX_MESSAGE_AGE)
        removed_stations = 0
        removed_messages = 0
        for band in self.station_data: # iterate all bands
            for call in list(self.station_data[band].keys()): # iterate all heard stations
                if now - self.station_data[band][call].time > threshold:
                    del self.station_data[band][call] # remove old station
                    removed_stations += 1
        for message in self.message_data:
            if now - message.time > threshold:
                self.message_data.remove(message)
                removed_messages += 1
        self.last_remove_old_data = now
        logger.info('removed %d stations and %d messages that were older than %s.' % (removed_stations, removed_messages, str(constants.MAX_MESSAGE_AGE)))

    def update(self):
        # event dispatching in chronological order
        while True:
            try:
                event = self.event_queue.get(block=False)

                if event.type == events.Type.MESSAGE:
                    self.dispatch_message(event.payload)
                elif event.type == events.Type.BAND:
                    self.dispatch_band_changed(event.payload)
                elif event.type == events.Type.LOCATION:
                    self.dispatch_receiver_location(event.payload)
            except queue.Empty:
                break

        self.remove_old_data()

        if self.flag_filter or self.flag_message or self.flag_band_change or self.flag_receiver_location or self.flag_map:
            self.redraw()

        if self.flag_list or self.flag_filter or self.flag_message or self.flag_band_change or self.flag_receiver_location:
            self.update_listwin()

        if datetime.datetime.now() - self.last_statwin_update > datetime.timedelta(seconds=constants.plot_resolutions[self.plotx][0]): # when data moves to another bin -> replot
            self.flag_replot = True
        if self.flag_replot or self.flag_filter or self.flag_message or self.flag_band_change or self.flag_receiver_location:
            self.update_statwin()
            self.last_statwin_update = datetime.datetime.now()

        # reset flags (except flag_replot)
        self.flag_message = False
        self.flag_band_change = False
        self.flag_receiver_location = False
        self.flag_filter = False
        self.flag_list = False
        self.flag_map = False

        self.wndo.update()
        self.wndo.after(constants.UPDATE_PERIOD, self.update)

    def run_loop(self):
        # ThemedTKinterFrame.run causes multiple problems
        #   - it sets the minimal window size to the initial window size
        #   - this leads to the window being moved right and down, i.e. restoring the position does not work
        # We use this function as a simple replacement.
        self.root.mainloop()

    @staticmethod
    def on_message(self, caller, grid, snr, msg):
        tval = int(time.time())   # grab timestamp
        self.event_queue.put(events.Event(events.Type.MESSAGE, (caller, grid, snr, msg, tval)))

    @staticmethod
    def on_band_changed(self, freq):
        self.event_queue.put(events.Event(events.Type.BAND, freq))

    @staticmethod
    def on_receiver_location(self, call, grid):
        self.event_queue.put(events.Event(events.Type.LOCATION, (call, grid)))

    def dispatch_message(self, args):
        caller, grid, snr, msg, tval = args

        if self.sband == constants.any_band:
            return # band not known yet
        if grid == '': # no grid in this message
            if caller in self.station_data[str(self.sband)]: # if heard before
                grid = self.station_data[str(self.sband)][caller].grid # keep previous grid

        logger.debug('adding station %s in %s (snr=%s, msg="%s") heard in %d m band' % (caller, grid, snr, msg, self.sband))
        station = _station.Station(
            tval,
            caller,
            grid,
            self.sband,
            snr,
            msg
            )

        self.station_data[str(self.sband)][caller] = station
        self.message_data.append(station)

        self.flag_message = True

    def dispatch_band_changed(self, args):
        freq = args

        for band_lower, band_upper, band, _ in constants.band_list:              # step thru bandlist using freq
            if  band_lower <= freq < band_upper:    # in this band?
                self.wndo.title('%s - %d m' % (self.version.APPNAME, band))     # yes, set title
                self.sband = int(band)
                self.flag_band_change = True
                break
        
        if not self.flag_band_change:
            logging.warn('out of band frequency %d Hz detected.' % freq)

    def dispatch_receiver_location(self, args):
        _, grid = args

        # store receiving station
        tval = int(time.time())   # grab timestamp
        self.rx_station = _station.Station(
            tval,
            constants.RX_CALL,
            grid,
            self.sband,
            0
        )

        self.flag_receiver_location = True

    # for debugging and presentation purposes
    # add positions of world cities by faking decoded messages
    def load_example_data(self):
        i = 0
        for caller, grid in examples.world_cities:
            # fake remaining values...
            snr = -(i % 12)
            msg = 'example No. %d' % i

            self.on_band_changed(self, constants.band_list[i % len(constants.band_list)][0])
            self.on_message(self, caller, grid, snr, msg)
            i += 1

        if self.rx_grid is None:
            # place fake receiver station
            call = 'RX'
            grid = 'II55' # center of world map (0 deg N, 0 deg E)
            self.on_receiver_location(self, call, grid)

    #TODO use time and mode from logfile
    def load_logfile(self, *_):
        filename = tk.filedialog.askopenfilename(title=self.version.APPNAME)
        with open(filename, 'r') as file:
            lines = file.readlines()
        for line in lines:
            tokens = re.search('([0-9\.]+) Rx (\w+)\s+([0-9-])\s+[0-9\.]+ [0-9]{4,4} (CQ [0-9]+|[A-Z0-9]+) ([A-Z0-9]+) ([A-Z]{2,2}[0-9]{2,2})', line)
            if tokens is not None:
                freq, mode, snr, _, caller, grid = tokens.groups()
                if grid == 'RR73':
                    continue
                freq = int(1.0e6 * float(freq))
                msg = ''
                self.on_band_changed(self, freq)
                self.on_message(self, caller, grid, snr, msg)
                continue
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import TKinterModernThemes
import ipaddress

from . import constants

class Settings(TKinterModernThemes.ThemedTKinterFrame):
    def __init__(self, parent, config, mode='light', on_settings_changed=None):
        self.config = config
        self.on_settings_changed = on_settings_changed

        self.handleExit = self.on_cancel
        super().__init__('Settings', 'sun-valley', mode)

        # center settings window over parent
        x = parent.winfo_width()
        y = parent.winfo_height()
        x //= 2
        y //= 2

        geom = '+%d+%d' % (x, y)
        self.master.geometry(geom)
        self.master.title('Settings')

        group_network = ttk.LabelFrame(self.master, text='Network')
        group_network.pack(side='top', anchor='n', ipady=4)
        host = ttk.Label(group_network, text='Host:', anchor='w', justify='left')
        port = ttk.Label(group_network, text='Port:', anchor='w', justify='left')
        host.grid(row=0, column=0, sticky='we', padx=4, pady=4)
        port.grid(row=1, column=0, sticky='we', padx=4, pady=4)

        self.taddr = ttk.Entry(group_network)
        self.tport = ttk.Entry(group_network)
        self.taddr.grid(row=0, column=1, columnspan=2, sticky='we', padx=4, pady=4)
        self.tport.grid(row=1, column=1, columnspan=2, sticky='we', padx=4, pady=4)
        self.taddr.insert(0, self.config['network']['host'])
        self.tport.insert(0, self.config['network']['port'])

        group_lookup = ttk.LabelFrame(self.master, text='Lookup')
        group_lookup.pack(side='top', anchor='n', ipady=4)

        self.lookup_idx = tk.IntVar(value=self.config['lookup']) # lookup callsign on QRZ (1) or HamCall (2)
        r1 = ttk.Radiobutton(group_lookup, text='QRZ.com', variable=self.lookup_idx, value=constants.lookup_QRZ)
        r2 = ttk.Radiobutton(group_lookup, text='HamCall.net', variable=self.lookup_idx, value=constants.lookup_HamCall)
        r1.grid(row=0, column=0, sticky='w', padx=2, pady=2)
        r2.grid(row=1, column=0, sticky='w', padx=2, pady=2)

        group_controls = ttk.Frame(self.master)
        group_controls.pack(side='top', anchor='n', ipady=4)
        ok = ttk.Button(group_controls, text='Ok', command=self.on_ok)
        cancel = ttk.Button(group_controls, text='Cancel', command=self.on_cancel)
        ok.grid(row=0, column=1, sticky='we', padx=4, pady=4)
        cancel.grid(row=0, column=2, sticky='we', padx=4, pady=4)

    #
    # setok - settings clicked ok
    #
    def on_ok(self):
        try:
            self.config['network']['host'] = self.taddr.get()
            try:
                self.config['network']['port'] = int(self.tport.get())
            except:
                tk.Label(self.master, text='Port is not an integer!', fg='red'). \
                    grid(row=3, column=1, sticky=tk.W)
                raise
            self.config['lookup'] = self.lookup_idx.get()

            c = int(self.config['network']['port'])
            if c >= 1024 and c <= 65536:
                pass
            else:
                #TODO warning
                tk.Label(self.master, text='Port must be >1024 and <65536!', fg='red'). \
                    grid(row=3, column=1, sticky=tk.W)
                raise
            try:
                ipaddress.ip_address(self.config['network']['host'])
            except:
                tk.Label(self.master, text='Not a valid IP address!',fg='red'). \
                    grid(row=3, column=1, sticky=tk.W)
                raise

            if self.on_settings_changed is not None:
                self.on_settings_changed()
            #messagebox.showinfo(message='Application restart is now required!')
        finally:
            self.master.destroy()

    def on_cancel(self):
        self.master.destroy()
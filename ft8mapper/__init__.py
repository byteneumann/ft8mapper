import os
import sys
import json
import logging
from functools import partial

logger = logging.getLogger('app')

class Application():
    from . import gui
    from . import version
    from . import networking

    def __init__(self, example_stations=False, rx_grid=None):
        # directory we are executing from, i.e. current working directory
        self.cwd = os.path.realpath(os.path.dirname(sys.argv[0]))

        self.load_config()

        self.gui = self.gui.GUI(
            self.config,
            on_config_changed=partial(self.save_config, self),
            on_exit=partial(self.exit, self),
            example_stations=example_stations,
            rx_grid=rx_grid
            )
        
        self.network = self.networking.Networking(
            self.config['network']['host'],
            self.config['network']['port'],
            on_message=partial(self.gui.on_message, self.gui),
            on_band_changed=partial(self.gui.on_band_changed, self.gui),
            on_receiver_location=partial(self.gui.on_receiver_location, self.gui)
            )

        logger.info('%s is initialized' % self.version.APPNAME)

    def run(self):
        try:
            self.message_queue = [] # filled by network thread, read by app
            self.network.start()

            logger.info('%s is running...' % self.version.APPNAME)
            self.gui.run_loop()
        except Exception as e:
            logger.error('%s caught an error!' % self.version.APPNAME)
            logger.error(e)
        finally:
            logger.info('%s is exiting' % self.version.APPNAME)
            self.network.stop()

    def default_config(self):
        self.config = {}
        self.config['configdir'] = self.cwd
        self.config['network'] = {}
        self.config['network']['host'] = '127.0.0.1'
        self.config['network']['port'] = 2237
        self.config['window'] = {}
        self.config['map'] = {}

        self.gui.GUI.default_config(self.config)

    def load_config(self):
        logger.info('loading config file')
        try:
            with open(os.path.join(self.cwd, 'config.json'), 'r') as file:
                self.config = json.load(file)
        except:
            # set default values instead
            logger.warning('could not load config file. using default values instead')
            self.default_config()
            self.save_config(self) # create config for the first time

    @staticmethod
    def save_config(self):
        logger.info('saving config file')
        with open(os.path.join(self.cwd, 'config.json'), 'w') as file:
            json.dump(self.config, file, indent=4) # persist all variables stored in config dictionary

    @staticmethod
    def exit(self):
        self.network.stop()
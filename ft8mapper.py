#!/usr/bin/env python3
#
# ft8mapper - maps stations by their grid data from WSJT-X
#   == v1.0, Copyright (C) 2024 TCJC
#   >= v1.1.0-byteneumann, Copyright (C) 2024 byteneumann
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  <https://www.gnu.org/licenses/>
#
import sys
import logging
import argparse
from ft8mapper import Application

if __name__ == '__main__':
    try:
        retval = 0

        parser = argparse.ArgumentParser()
        parser.add_argument('--verbose', default=False, action='store_true', help='Include DEBUG messages in console output.')
        parser.add_argument('--example-stations', default=False, action='store_true', help='Add world cities as example stations. No messages will be saved on exit.')
        parser.add_argument('--rx-grid', metavar='GRID', type=str, help='Overwrite maidenhead locator of receiving station.')

        try:
            args = parser.parse_args()
        except Exception as e:
            logging.error(e)
            sys.exit(1)

        logging.basicConfig(level=logging.INFO if not args.verbose else logging.DEBUG)

        app = Application(example_stations=args.example_stations, rx_grid=args.rx_grid)
        app.run()
    except Exception as e:
        logging.error(e)
        retval = 1
    finally:
        sys.exit(retval)
import json
import time
import datetime

class Station():
    def __init__(self, time, call, grid, band, report, message=''):
        self.time = datetime.datetime.fromtimestamp(time)
        self.call = call
        self.grid = grid
        self.band = int(band)
        self.report = int(report)
        self.message = message

    def utc(self):
        return time.strftime('%H:%M:%SZ', time.gmtime(self.time.timestamp()))
    
class Serializer(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Station):
            return {
                'time': o.time.timestamp(),
                'call': o.call,
                'grid': o.grid,
                'band': o.band,
                'report': o.report,
                'message': o.message
            }
        else:
            return super().default(o)

def from_json(o):
    try:
        if 'time' in o and 'call' in o and 'grid' in o and 'band' in o and 'report' in o and 'message' in o:
            return Station(
                o['time'],
                o['call'],
                o['grid'],
                o['band'],
                o['report'],
                o['message']
            )
    except:
        pass
    return o
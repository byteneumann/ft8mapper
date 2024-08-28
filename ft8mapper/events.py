import enum

class Type(enum.Enum):
    MESSAGE = 0
    BAND = 1
    LOCATION = 2

class Event:
    def __init__(self, type, payload):
        self.type = type
        self.payload = payload
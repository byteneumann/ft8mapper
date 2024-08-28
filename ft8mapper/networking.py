import time
import logging
import socket
import threading

from . import constants

logger = logging.getLogger('net')

class Networking():
    def __init__(self, host, port, on_message=None, on_band_changed=None, on_receiver_location=None):
        self.host = host
        self.port = port
        self.on_message = on_message
        self.on_band_changed = on_band_changed
        self.on_receiver_location = on_receiver_location

        # build response to heartbeat request a priori
        self.heartbeat =  b'\xad\xbc\xcb\xda\x00\x00\x00\x02'  # magic# & schema
        self.heartbeat += b'\x00\x00\x00\x00\x00\x00\x00\x06'  # pkt 0 and utf len
        self.heartbeat += bytes('WSJT-X','utf-8')              # utf identifier
        self.heartbeat += b'\x00\x00\x00\x02'                  # max schema version
        self.heartbeat += b'\x00\x00\x00\x00\x00\x00\x00\x00'  # sw release revs (0's)
        
        self.ofreq = None # last known receive frequency
        self.tm0 = time.time()                             # grab time for heartbeat tracking
        self.tdstamp = time.time()                         # get timestamp used for tracking decode
        self.otmi = -1                                     # initialize old time tracker

    def start(self):
        logger.info('starting network client')
        self.running = True
        self.network_thread = threading.Thread(name='Network', target=self._recv_loop)
        self.network_thread.start()

    def stop(self):
        if self.network_thread.is_alive():
            logger.info('stopping network client')
            self.running = False
            while self.network_thread.is_alive():
                logger.debug('waking up network loop...')
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                    sock.sendto(bytearray(0), (self.host, self.port)) # unblock network thread
                self.network_thread.join(timeout=1.0)
            logger.debug('network client is now stopped')

    # protocol reference
    # https://sourceforge.net/p/wsjt/wsjtx/ci/master/tree/Network/NetworkMessage.hpp

    def _check_frequency(self, freq):
        if freq != self.ofreq:                    # if new freq doesn't equal old
            if self.on_band_changed is not None and self.running:
                self.on_band_changed(freq)
            self.ofreq = freq                 # old freq becomes new freq
    
    def _check_message(self, mesg):
        cq = 0                            # flag indicates whether CQ, 73 or QSO
        caller = ''                       # callsign of 1 callsign mesg
        called = ''                       # holds 2nd callsign if 2 callsign QSO mesg
        grid = ''                         # holds grid
        ota = ''                          # 'on the air' - holds stuff like 'POTA' or 'DX'

        smesg = mesg.decode('utf-8')      # decode from byte to string
        rtext = smesg
        msglist = smesg.split()           # split by whitespace
        nitem = len(msglist)              # how many items came out of split?

        if msglist[0] == 'CQ':          # 'cq caller grid'
            cq = 1                        # mark as a CQ
            if any(char.isdigit() for char in msglist[1]):
                if nitem > 1:
                    caller = msglist[1]   # get the callsign
                if nitem > 2:
                    grid = msglist[2]     # get the grid
            else:                       # 'cq dx/ota call1 grid'
                ota = msglist[1]          # grab dx, pota, vota, etc.
                if nitem > 2:
                    caller = msglist[2]   # get the callsing
                    caller += '/' + ota   # append ota suffix
                if nitem > 3:
                    grid = msglist[3]     # get the grid
            caller = caller.replace('<', '')
            caller = caller.replace('>', '')
            if len(caller) < 3 or caller == 'RR73': # malformed
                raise Exception('caller is malformed')
        else:                           # 'called caller snr/grid/rr73'
            if any(char.isdigit() for char in msglist[0]):
                called = msglist[0]        # grab 1st callsign
                called = called.replace('<', '')
                called = called.replace('>', '')
            if nitem > 1:
                if any(char.isdigit() for char in msglist[1]):
                    caller = msglist[1]    # grab 2nd callsign
                    caller = caller.replace('<', '')
                    caller = caller.replace('>', '')
                    if len(caller) < 3 or caller == 'RR73': # malformed
                        raise Exception('caller is malformed')
            if nitem > 2:
                if msglist[2].isalnum():    # kill R-23 and -10 stuff
                    if msglist[2] == '73' or msglist[2] == 'RR73':
                        cq = 2            # 73 as RR73 isn't a valid grid
                    else:
                        if any(char.isdigit() for char in msglist[2]):
                            if len(msglist[2]) == 4:  # 4 chars long & no punct
                                grid = msglist[2]     # assume grid
        if caller == '' or caller[0 : 4] == 'RR73':  # caller is blank, trash...
            raise Exception('caller is blank')

        #if self.sband == constants.unknown_band:          # before plotting we have to know the band
        #    return True

        if len(grid) < 4:   # garbage grid... usually 'a7' or '73' due to misformatted QSO
            raise Exception('grid is garbage')
        if len(grid) > 4:   # if length of grid > 4
            grid = grid[:4]   # truncate to 4 chars

        return caller, grid, rtext

    def _pkttype0(self, addr):
        self.sock.sendto(self.heartbeat, addr) # respond with heartbeat
        return True

    def _pkttype1(self, data):
        offset = 0
        self.nfreq = int.from_bytes(data[offset : offset + 8], 'big')
        self._check_frequency(self.nfreq)
        offset += 8

        # skip Mode, DX call, Report, Tx mode
        for i in range(4):
            size = int.from_bytes(data[offset : offset + 4], 'big')
            offset += 4 + (size if size != 0xFFFFFFFF else 0)

        # skip TX Enabled, Transmitting, Decoding
        offset += 3

        # skip Rx DF, Tx DF
        offset += 8

        # get DE call
        size = int.from_bytes(data[offset : offset + 4], 'big')
        offset += 4
        if size > 0:
            de_call = data[offset : offset + size].decode('utf-8')
        else: # no callsign
            de_call = '-'
        offset += (size if size != 0xFFFFFFFF else 0)

        # get DE grid
        size = int.from_bytes(data[offset : offset + 4], 'big')
        offset += 4
        if size > 0:
            de_grid = data[offset : offset + size].decode('utf-8')
            de_grid = de_grid[:4]

            if self.on_receiver_location is not None and self.running:
                self.on_receiver_location(de_call, de_grid)
        offset += (size if size != 0xFFFFFFFF else 0)

        return True

    def _pkttype2(self, data):
        # inside a DECODE packet
        offset = 0
        if bool.from_bytes(data[offset : offset + 1], 'big') is False: # New?
            return True                        # just a replay pkt, ignore...
        offset += 1                          # step 1 byte past new flag
        qtime = data[offset : offset + 4]       # get 4 byte time since midnite
        offset += 4                          # step past those 4
        tmi = int.from_bytes(qtime, 'big') / 1000 # grab time from pkt
        if tmi != self.otmi:                       # new batch of decodes starting
            self.tdstamp = int(time.time())        # grab realtime timestamp
            self.otmi = tmi                        # set to avoid re-fire till new batch
        snr = int.from_bytes(data[offset : offset + 4], 'big', signed=True)
        offset += 4                          # step past those 4
        deltat = data[offset : offset + 8]      # 8 byte time delta value
        offset += 8                          # step past those 8
        deltaf = data[offset : offset + 4]      # grab freq of remote station
        offset += 4                          # step past those 4
        # grab 4 byte length of mode field converting to integer
        modelenval = int.from_bytes(data[offset : offset + 4], 'big')
        offset += 4                          # step past those 4
        # use length of mode field to grab the whole thing
        mode = data[offset : offset + modelenval]
        offset += modelenval                 # step past by length of mode field
        # grab 4 byte length of message field converting to integer
        mesglenval = int.from_bytes(data[offset : offset + 4], 'big')
        offset += 4                          # step past those 4
        # use length of mesg field to grab the whole thing
        mesg = data[offset : offset + mesglenval]
        # offset+=mesglenval               # step past the mesg field

        if time.time() - self.tm0 <= 6:            # we can still get late decodes
            self.tm0 = time.time()                 # if deep decode is set...

        try:
            caller, grid, rtext = self._check_message(mesg)
        except:
            return False

        if self.on_message is not None and self.running:
            self.on_message(caller, grid, snr, rtext)

        return True

    def _recv_loop(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as self.sock:     # UDP datagrams
            try:
                self.sock.bind((self.host, self.port))             # bind to port
            except:
                logger.error('caught network error')
                raise Exception('could not bind to %s:%s!' % (self.host, self.port))

            logger.info('entering network loop...')
            while self.running:
                try:
                    data, addr = self.sock.recvfrom(2048)    # data for us?

                    if not self.running:
                        break

                    # WSJT-X gave us a packet to inspect
                    pkttype = int.from_bytes(data[8 : 12], 'big')
                    idlen = int.from_bytes(data[12 : 16], 'big')
                    offset = 16  # set offset past magic#, schema, pkttype and idlen
                    swid = data[offset : offset + idlen]    # use idlen to grab full swid
                    offset += idlen  # adjust offset by length of software ID (swid)

                    # handle packets based on type
                    payload = data[offset:]
                    if pkttype == 0:
                        self._pkttype0(addr)
                    elif pkttype == 2:  # if not decode packet restart loop
                        _ = self._pkttype2(payload)
                    elif pkttype == 1:                          # packet type 1 - grab frequency
                        _ = self._pkttype1(payload)
                    elif pkttype == 6:                          # WSJT-X is shutting down
                        pass # ignore it and leave the window open
                    else:
                        logger.warning('unhandled pkttype %d received.' % pkttype)
                except Exception as e:
                    logger.error('caught network error')
                    self.running = False
                    raise e # rethrow exception
        logger.info('network loop is terminated')
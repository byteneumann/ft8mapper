RX_CALL = '__RX__' # special callsign for receiving station (never shown)

# plot offsets for multi stations in the same maidenhead locator
collision_offset = [
    [ 0,  0],
    [-4, -4],
    [ 0, -4],
    [ 4, -4],
    [-4,  0],
    [ 4,  0],
    [-4,  4],
    [ 0,  4],
    [ 4,  4]
]

# radius of circles drawn for spots when viewing the world map
wm_spot_radius = 3

# number of characters per line in details panel
details_width = 16

# special value indicating any or unknown band
any_band = 0

# band ranges hopefully chosen wide enough to cover internationa as well
# format: start freq., end freq., meters, index
band_list = [
    [  1800000,   2000000, 160,  0],
    [  3500000,   4000000,  80,  1],
    [  5320000,   5410000,  60,  2],
    [  7000000,   7300000,  40,  3],
    [ 10100000,  10150000,  30,  4],
    [ 14000000,  14350000,  20,  5],
    [ 18068000,  18168000,  17,  6],
    [ 21000000,  21450000,  15,  7],
    [ 24890000,  24990000,  12,  8],
    [ 28000000,  29700000,  10,  9],
    [ 50000000,  54000000,   6, 10],
    [144000000, 148000000,   2, 11]
]

# plot metrics
plot_metrics = {
    'Decode rate': 'M',
    'Report': 'R',
    'Range': 'D',
    'Stations': 'S',
    'Grids': 'G'
}

# convert text to seconds
age_labels = {
    '7 days': 604800,
    '3 days': 259200,
    '24 hours': 86400,
    '12 hours': 43200,
    '6 hours': 21600,
    '3 hours': 10800,
    '2 hours': 7200,
    '1 hour': 3600,
    '30 minutes': 1800,
    '15 minutes': 900,
    '5 minutes': 300,
    '1 minute': 60
}

# age limit: [bar plot resolution, major tic resolution, label resolution, unit]
plot_resolutions = {
    604800: [21600, 86400, 86400, 'd'],
    259200: [21600, 86400, 86400, 'd'],
    86400: [3600, 4 * 3600, 3600, 'h'],
    43200: [3600, 4 * 3600, 3600, 'h'],
    21600: [900, 3600, 3600, 'h'],
    10800: [900, 3600, 3600, 'h'],
    7200: [900, 3600, 3600, 'h'],
    3600: [60, 15 * 60, 60, '\''],
    1800: [60, 10 * 60, 60, '\''],
    900: [60, 5 * 60, 60, '\''],
    300: [60, 60, 60, '\''],
    60: [15, 15, 1, '"']
}

MAX_MESSAGE_AGE = max(age_labels.values())

# convert band label to band_name
band_labels = {
    'All bands': any_band,
}
for _, _, band, _ in band_list:
    band_labels['%s m' % band] = band

# colors for the different bands -- look like PSKreporter
band_colors = {
    2: 'DeepPink2',
    6: 'red',
    10: 'HotPink',
    12: 'brown',
    15: 'BurlyWood',
    17: 'yellow2',
    20: 'Gold',
    30: 'mediumseagreen',
    40: 'dodgerblue1',
    60: 'MediumBlue',
    80: 'Violet',
    160: 'green1'
}

# index of callsign lookup website
lookup_QRZ = 1
lookup_HamCall = 2

UPDATE_PERIOD = 250 # milliseconds between GUI updates
CLEAN_PERIOD = 5 # minutes until data that is too old is removed
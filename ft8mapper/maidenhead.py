import math

EARTH_RADIUS = 6371000 # meter

def locator_valid(grid):
    if len(grid) < 2:
        return False # too short
    
    if not ('A' <= grid[0] <= 'R'):
        return False
    if not ('A' <= grid[1] <= 'R'):
        return False
    
    if len(grid) > 2:
        if not ('0' <= grid[2]<='9'):
            return False
        if not ('0' <= grid[3] <= '9'):
            return False
        
    if len(grid) > 4:
        if not ('a' <= grid[4]<='r'):
            return False
        if not ('a' <= grid[5] <= 'r'):
            return False
        
    return True

# locator format:
# A -> longitude, A (180 deg west) to R (180 deg east)
# B -> latitude, A (90 deg south) to R (90 deg north)
# 1 -> longitude, 0 (0 deg) to 9 (18 deg)
# 2 -> latitude, 0 (0 deg) to 9 (9 deg)
# a -> longitude, a (0 deg) to r (2 deg)
# b -> latitude, a (0 deg) to r (1 deg)
def locator2latlon(grid):
    # 18 x 18 fields, 20 and 10 deg each
    lon = (ord(grid[0]) - ord('A')) * 20 - 180
    lat = (ord(grid[1]) - ord('A')) * 10 -  90

    # 10 x 10 squares, 2 and 1 deg each
    lon += (ord(grid[2]) - ord('0')) * 2
    lat += (ord(grid[3]) - ord('0')) * 1

    if len(grid) > 4:
        # 18 x 18 squares
        lon += (ord(grid[4]) - ord('a')) * 2
        lat += (ord(grid[5]) - ord('a')) * 1
    else:
        # for mapping purposes we want to center the position within the square
        lon += 1.0 # deg
        lat += 0.5 # deg

    return lat, lon

def latlon2locator(lat, lon):
    locator = ''

    # 18 x 18 fields, 20 and 10 deg each
    lon = (lon + 180) / 20
    lat = (lat +  90) / 10
    locator += chr(ord('A') + int(lon))
    locator += chr(ord('A') + int(lat))

    ## 10 x 10 squares, 2 and 1 deg each
    lon = 10 * (lon - int(lon))
    lat = 10 * (lat - int(lat))
    locator += chr(ord('0') + int(lon))
    locator += chr(ord('0') + int(lat))

    return locator

# calculate distance on earth surface using haversine formula
def latlon_distance(lat_a, lon_a, lat_b, lon_b):
    lat_a = math.radians(lat_a)
    lat_b = math.radians(lat_b)
    lon_a = math.radians(lon_a)
    lon_b = math.radians(lon_b)

    dlat = lat_b - lat_a
    dlon = lon_b - lon_a

    # haversine formula
    a = math.pow(math.sin(0.5 * dlat), 2.0) + math.cos(lat_a) * math.cos(lat_b) * math.pow(math.sin(0.5 * dlon), 2.0)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    d = c * EARTH_RADIUS

    return d

def locator_distance(a, b):
    lat_a, lon_a = locator2latlon(a)
    lat_b, lon_b = locator2latlon(b)

    return latlon_distance(lat_a, lon_a, lat_b, lon_b)

# calculate bearing between two points on a sphere
def locator_bearing(a, b):
    lat_a, lon_a = locator2latlon(a)
    lat_b, lon_b = locator2latlon(b)

    lat_a = math.radians(lat_a)
    lat_b = math.radians(lat_b)
    lon_a = math.radians(lon_a)
    lon_b = math.radians(lon_b)

    dlon = lon_b - lon_a

    x = math.cos(lat_a) * math.sin(lat_b) - math.sin(lat_a) * math.cos(lat_b) * math.cos(dlon)
    y = math.sin(dlon) * math.cos(lat_b)
    bearing = math.atan2(y, x)

    bearing = math.degrees(bearing)
    bearing = math.fmod(bearing + 360.0, 360.0) # [-180;180] -> [0;360]

    return bearing
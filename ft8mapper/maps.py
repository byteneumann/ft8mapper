#
# Magic data tables that map dot into the maps from OpenStreet... ugly
# but we are offline...whatcha going to do?
#

IMAGE_WIDTH = 1345
IMAGE_HEIGHT = 940
INVALID_COORDS = (-1, -1)

# project a maidenhead locator to map image coordinates using several lookup tables and offsets
def gridto_ex(grid, lon_fields, lat_fields, lon_squares, lat_squares, xoff, yoff):
    # field
    lngo = grid[0 : 1]
    if not lngo in lon_fields.keys():
        return INVALID_COORDS
    xcoor = lon_fields[lngo]

    lato = grid[1 : 2]
    if not lato in lat_fields.keys():
        return INVALID_COORDS
    ycoor = lat_fields[lato]

    # square
    xlngo = grid[2 : 3]
    if not ('0' <= xlngo <= '9'):
        return INVALID_COORDS
    xcoor += lon_squares[xlngo]

    ylato = grid[3 : 4]
    if not ('0' <= ylato <= '9'):
        return INVALID_COORDS
    ycoor -= lat_squares[lato] * int(ylato)

    if len(grid) > 4:
        # get next square (south-east)
        def east(field, square):
            if square == '9':
                square = '0'
                if field == 'R':
                    field = 'A'
                else:
                    field = chr(ord(field) + 1)
            else:
                square = chr(ord(square) + 1)
            return field, square
        def south(field, square):
            if square == '0':
                square = '9'
                if field == 'A':
                    field = 'R'
                else:
                    field = chr(ord(field) - 1)
            else:
                square = chr(ord(square) - 1)
            return field, square
        g0 = lngo
        g1 = lato
        g2 = xlngo
        g3 = ylato
        g0, g2 = east(g0, g2)
        g1, g3 = south(g1, g3)
        x1, y1 = gridto_ex(''.join([g0, g1, g2, g3]), lon_fields, lat_fields, lon_squares, lat_squares, xoff, yoff)

        # interpolate coordinates
        xcoor += (x1 - xcoor) * (ord(grid[4]) - ord('a')) / (ord('r') - ord('a') - 1)
        ycoor += (y1 - ycoor) * (ord(grid[5]) - ord('a')) / (ord('r') - ord('a') - 1)

    # check against map image size
    if not (0 <= xcoor <= IMAGE_WIDTH):
        return INVALID_COORDS

    if not (0 <= ycoor <= IMAGE_HEIGHT):
        return INVALID_COORDS

    xcoor += xoff
    ycoor += yoff
    return xcoor, ycoor

# WorldMap (WM)
WM_LON_FIELDS = {"A":12,"B":83,"C":154,"D":225,"E":296,"F":367,"G":439,"H":511,"I":583,"J":655,"K":727,"L":798,"M":869,"N":940,"O":1011,"P":1082,"Q":1153,"R":1224}
WM_LAT_FIELDS = {"A":950,"B":945,"C":921,"D":836,"E":773,"F":722,"G":678,"H":640,"I":602,"J":566,"K":530,"L":492,"M":454,"N":410,"O":361,"P":298,"Q":211,"R":67}
WM_LON_SQUARES = {"0":4,"1":11,"2":18,"3":25,"4":32,"5":40,"6":47,"7":54,"8":61,"9":68}
WM_LAT_SQUARES = {"A":0,"B":0,"C":8.5,"D":6.3,"E":5.1,"F":4.4,"G":3.8,"H":3.8,"I":3.6,"J":3.6,"K":3.8,"L":3.8,"M":4.4,"N":4.9,"O":6.3,"P":8.7,"Q":14.4,"R":14.5}
WM_X_OFFSET = 2
WM_Y_OFFSET = -4

# North America (NA)
NA_LON_FIELDS = {'B':0,'C':226,'D':452,'E':678,'F':904,'G':1130}
NA_LAT_FIELDS = {'J':950,'K':841,'L':724,'M':600,'N':461,'O':301,'P':102}
NA_LON_SQUARES = {'0':19,'1':42,'2':64,'3':87,'4':109,'5':132,'6':155,'7':177,'8':200,'9':222}
NA_LAT_SQUARES = {'J':10.9,'K':11.7,'L':12.4,'M':13.9,'N':16,'O':19.9,'P':26.9}
NA_X_OFFSET = 2
NA_Y_OFFSET = 2

# South America (SA)
SA_LON_FIELDS = {'D':0,'E':226,'F':452,'G':678,'H':904,'I':1130}
SA_LAT_FIELDS = {'D':1012,'E':802,'F':642,'G':506,'H':382,'I':266,'J':154,'K':42}
SA_LON_SQUARES = {'0':11,'1':34,'2':57,'3':79,'4':102,'5':124,'6':147,'7':170,'8':192,'9':214}
SA_LAT_SQUARES = {'D':20,'E':16,'F':13.6,'G':12.4,'H':11.6,'I':11.2,'J':11.2,'K':11.5}
SA_X_OFFSET = 2
SA_Y_OFFSET = 2

# Europe (EU)
EU_LON_FIELDS = {'H':0,'I':226,'J':452,'K':678,'L':904,'M':1130}
EU_LAT_FIELDS = {'L':932,'M':805,'N':666,'O':505,'P':306,'Q':34}
EU_LON_SQUARES = {'0':11,'1':34,'2':57,'3':79,'4':102,'5':124,'6':147,'7':170,'8':192,'9':214}
EU_LAT_SQUARES = {'L':12.7,'M':13.9,'N':16.1,'O':19.9,'P':27.2,'Q':36}
EU_X_OFFSET = 2
EU_Y_OFFSET = 2

# Africa (AF)
AF_LON_FIELDS = {'H':0,'I':226,'J':452,'K':678,'L':904,'M':1130}
AF_LAT_FIELDS = {'F':950,'G':847,'H':721,'I':604,'J':491,'K':378,'L':261,'M':136}
AF_LON_SQUARES = {'0':11,'1':34,'2':57,'3':79,'4':102,'5':124,'6':147,'7':170,'8':192,'9':214}
AF_LAT_SQUARES = {'F':9,'G':12.6,'H':11.7,'I':11.3,'J':11.3,'K':11.7,'L':12.5,'M':14.0}
AF_X_OFFSET = 2
AF_Y_OFFSET = 2

# Asia (AS)
AS_LON_FIELDS = {'L':0,'M':226,'N':452,'O':678,'P':904,'Q':1130}
AS_LAT_FIELDS = {'J':902,'K':788,'L':671,'M':546,'N':408,'O':247,'P':49}
AS_LON_SQUARES = {'0':11,'1':34,'2':57,'3':79,'4':102,'5':124,'6':147,'7':170,'8':192,'9':214}
AS_LAT_SQUARES = {'J':11.4,'K':11.7,'L':12.5,'M':13.8,'N':16.1,'O':19.8,'P':27}
AS_X_OFFSET = 2
AS_Y_OFFSET = 2

# Oceania (OC)
OC_LON_FIELDS = {'N':0,'O':226,'P':452,'Q':678,'R':904,'A':1130}
OC_LAT_FIELDS = {'E':950,'F':786,'G':648,'H':524,'I':406,'J':292,'K':179,'L':62}
OC_LON_SQUARES = {'0':11,'1':34,'2':57,'3':79,'4':102,'5':124,'6':147,'7':170,'8':192,'9':214}
OC_LAT_SQUARES = {'E':16.4,'F':13.8,'G':12.4,'H':11.8,'I':11.4,'J':11.3,'K':11.7,'L':12.4}
OC_X_OFFSET = 2
OC_Y_OFFSET = 2

# given the current map and the grid, fetch x,y from appropriate mappings
def project(current_map, grid):
    return {
        'WM': lambda grid: gridto_ex(grid, WM_LON_FIELDS, WM_LAT_FIELDS, WM_LON_SQUARES, WM_LAT_SQUARES, WM_X_OFFSET, WM_Y_OFFSET),
        'NA': lambda grid: gridto_ex(grid, NA_LON_FIELDS, NA_LAT_FIELDS, NA_LON_SQUARES, NA_LAT_SQUARES, NA_X_OFFSET, NA_Y_OFFSET),
        'SA': lambda grid: gridto_ex(grid, SA_LON_FIELDS, SA_LAT_FIELDS, SA_LON_SQUARES, SA_LAT_SQUARES, SA_X_OFFSET, SA_Y_OFFSET),
        'EU': lambda grid: gridto_ex(grid, EU_LON_FIELDS, EU_LAT_FIELDS, EU_LON_SQUARES, EU_LAT_SQUARES, EU_X_OFFSET, EU_Y_OFFSET),
        'AF': lambda grid: gridto_ex(grid, AF_LON_FIELDS, AF_LAT_FIELDS, AF_LON_SQUARES, AF_LAT_SQUARES, AF_X_OFFSET, AF_Y_OFFSET),
        'AS': lambda grid: gridto_ex(grid, AS_LON_FIELDS, AS_LAT_FIELDS, AS_LON_SQUARES, AS_LAT_SQUARES, AS_X_OFFSET, AS_Y_OFFSET),
        'OC': lambda grid: gridto_ex(grid, OC_LON_FIELDS, OC_LAT_FIELDS, OC_LON_SQUARES, OC_LAT_SQUARES, OC_X_OFFSET, OC_Y_OFFSET),
    }[current_map](grid)
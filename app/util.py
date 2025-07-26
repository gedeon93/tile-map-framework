import math
import numpy as np
from typing import List, Tuple, Optional

RADIUS_OF_EARTH = 3443.918 # Nautical miles

def is_numeric(text: str) -> bool:
    """
    Check if a string is numerical (with optional signage).
    """
    text = str(text).lstrip("+-")
    try:
        float(text)
    except (ValueError, TypeError):
        return False
    return True    

def degree_to_tile(lat_deg: float, lon_deg: float, zoom: int, snap: bool = False) -> Tuple[float, float]:
    """
    Convert latitude and longitude in degrees to tile x, y coordinates at a given level of zoom Level of Detail (LOD).
    using the Web Mercator projection.

    Args:
        lat_deg (float): Latitude in degrees.
        lon_deg (float): Longitude in degrees.
        zoom (int): Zoom level (LOD). Range from 0 to 21 is dependent on application.

    Returns:
        Tuple[float, float]: The (x, y) tile coordinates corresponding to the input coordinates.
    """
    if not (-85.0511 <= lat_deg <= 85.0511):
        raise ValueError("Latitude must be between -85.0511 and 85.0511 for Web Mercator projection.")

    if not (-180.0 <= lon_deg <= 180.0):
        raise ValueError("Longitude must be between -180.0 and 180.0.")

    if not (0 <= zoom <= 21):
        raise ValueError("Zoom level must be between 0 and 23.")
    
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    xTile = (lon_deg + 180.0) / 360.0 * n
    yTile = (1.0 - math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi) / 2.0 * n
    if snap:
        xTile = float(int(xTile))
        yTile = float(int(yTile))
    return (xTile, yTile)

def tile_to_degree(xTile: float, yTile: float, zoom: int) -> Tuple[float, float]:
    """
    Convert x, y projection coorindates to latitude, longitude coordinates at a given zoom (LOD).
    using the Web Mercator projection.

    Args:
        tile X (float): x tile position.
        tile Y (float): y tile position.
        zoom (int): Zoom level (LOD). Range from 0 to 21 is dependent on application.

    Returns:
        Tuple[float, float]: The (latitude, longitude) coordinates corresponding to the input tiles.
    """
    n = 2 ** zoom
    lon_deg = float(xTile / n * 360.0) - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - (2 * yTile / n))))
    lat_deg = float(lat_rad * 180.0 / math.pi)
    return (lat_deg, lon_deg)    

def angular_to_decimal_degree(str_deg: str) -> float:
    """
    Convert string decimal (DMS component form) to decimal degree. Expects compass direction.

    Args:
        str_deg (string): compass-degree expressed as decimal, minutes, and seconds (DMS).

    Returns:
        float: signed decimal degree.
    """
    str_deg = str(str_deg)
    new_str = ''
    last_ch = ''
    # conversions: degrees, minutes, seconds
    cvt = [1, 60, 3600]
    fmt = []
    signage = 1
    for c, i in zip(str_deg, range(len(str_deg))):
        if not (c.isnumeric() or c in ['-', '.']):
            if last_ch != 'x':
                new_str += 'x'
            if c.lower() == "'":
                fmt.append(1)
            elif c.lower() == '"':
                fmt.append(2)
            elif c.upper() in "NESW":
                fmt.append(0)
                if c.upper() in 'SW':
                    signage = -1
        else:
            new_str += c
        last_ch = new_str[-1]

    decimal = [float(elem) for elem in new_str.split('x') if len(elem) > 0]
    return signage * sum([decimal[i] / cvt[fmt[i]] for i in range(len(cvt))])

def feet_to_degree_offsets(lat_deg: float, distance: float) -> Tuple[float, float]:
    """
    Convert a distance in feet approximate changes in latitude and longitude degrees at
    a given reference latitude, assuming a spherical Earth.

    Args:
        lat_deg (float): Reference latitude in degrees.
        distance (float): Distance in feet.

    Returns:
        Tuple[float, float]: (delta_latitude, delta_longitude) in degrees.
    """
    lat_deg_diff = distance / 60.0
    lon_deg_diff = distance / (60.0 * math.cos(math.radians(lat_deg)))
    return (lat_deg_diff, lon_deg_diff)

def haversine_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points using the haversine formula.

    Args:
        lat1 (float): Latitude of point 1 in degrees.
        lon1 (float): Longitude of point 1 in degrees.
        lat2 (float): Latitude of point 2 in degrees.
        lon2 (float): Longitude of point 2 in degrees.

    Returns:
        float: Distance in nautical miles.
    """
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return RADIUS_OF_EARTH * c

def get_cartesian_coordinates_unit(lat: float, lon: float, alt: bool = None) -> Tuple[float, float, float]:
    """
    Convert geographic coordinates (latitude, longitude, altitude) into 3D Cartesian
    coordinates (x, y, z) on a unit sphere, assuming a spherical Earth.

    Args:
        lat (float): Latitude of point in degrees.
        lon (float): Longitude of point in degrees.
        altitude (float, optional): Altitude scale. Defaults to 0.0.
        
    Returns:
        Tuple[float, float, float]: Cartesian coordinates (x, y, z) on a unit sphere.
    """
    lat_rad, lon_rad = map(math.radians, [lat, lon])
    x = math.cos(lat_rad) * math.cos(lon_rad)
    y = math.cos(lat_rad) * math.sin(lon_rad)
    z = math.sin(lat_rad)
    if alt is not None:
        z = alt
    
    return [x, y, z]

def get_cartesian_coordinates_nm(lat: float, lon: float, alt: bool = None) -> Tuple[float, float, float]:
    """
    Convert geographic coordinates (latitude, longitude, altitude) into 3D Cartesian
    coordinates (x, y, z) in nautical miles, assuming a spherical Earth.

    Args:
        lat (float): Latitude of point in degrees.
        lon (float): Longitude of point in degrees.
        altitude (float, optional): Altitude in feet. Defaults to 0.0.
        
    Returns:
        Tuple[float, float, float]: Cartesian coordinates (x, y, z) in nautical miles.
    """
    lat_rad, lon_rad = map(math.radians, [lat, lon])
    distance_to_axis = RADIUS_OF_EARTH * math.cos(lat_rad)
    x = distance_to_axis * math.cos(lon_rad)
    y = distance_to_axis * math.sin(lon_rad)
    z = RADIUS_OF_EARTH  * math.sin(lat_rad)
    if alt is not None:
        z = alt
    
    return [x, y, z]

def get_geodesic_coordinates(x: float, y: float, z: float) -> Tuple[float, float]:
    """
    Convert 3D Cartesian coordinates (x, y, z) on a unit sphere to geographic coordinates
    (latitude, longitude, altitude) in degrees.

    Args:
        x (float): X-coordinate (unitless).
        y (float): Y-coordinate (unitless).
        z (float): Z-coordinate (unitless).
        
    Returns:
        Tuple[float, float]: (latitude, longitude) in degrees.
    """
    hyp = np.hypot(x, y)
    lat = np.arctan2(z, hyp) * 180 / math.pi
    lon = np.arctan2(y, x) * 180 / math.pi
    return [lat, lon]

def interpolate_interval(lat1: float, lon1: float, lat2: float, lon2: float, interval: int) -> list:
    """
    Calculates interval coorindates between two geographic coorindates at the specified interval amount.

    Args:
        lat1 (float): Latitude of point 1 in degrees.
        lon1 (float): Longitude of point 1 in degrees.
        lat2 (float): Latitude of point 2 in degrees.
        lon2 (float): Longitude of point 2 in degrees.
        Interval (float): Interval distance (in nautical miles).
        
    Returns:
        list (points): list of [latitude, longitude] in degrees.
    """
    p1 = np.array(get_cartesian_coordinates_unit(lat1, lon1))
    p2 = np.array(get_cartesian_coordinates_unit(lat2, lon2))

    angle = np.arccos(np.clip(np.dot(p1, p2), -1.0, 1.0))
    total_dist = angle * RADIUS_OF_EARTH

    num_pts = int(total_dist // interval)

    points = []
    for i in range(num_pts):
        f = (i * interval) / total_dist
        sin_angle = np.sin(angle)
        if sin_angle == 0:
            # interp = p1
            continue
        else:
            interp = (np.sin((1 - f) * angle) * p1 + np.sin(f * angle) * p2) / sin_angle
        lat, lon = get_geodesic_coordinates(interp[0], interp[1], interp[2])
        points.append([lat, lon])

    return points
    
def get_center_of_coordinates(coordinate1: List[float], coordinate2: List[float]) -> Tuple[float, float]:
    """
    Calculates the center point as a geographic coordinate between two cartesian coordinates.

    Args:
        coordinate1 (List[float]): a 2D or 3D cartesian coordinate.
        coordinate2 (List[float]): a 2D or 3D cartesian coordinate. 
        
    Returns:
        Tuple[float, float]: latitude and longitude in degrees.
    """
    # Convert both to Cartesian
    x1, y1, z1 = get_cartesian_coordinates_nm(coordinate1[0], coordinate1[1])
    x2, y2, z2 = get_cartesian_coordinates_nm(coordinate2[0], coordinate2[1])

    # Average the coordinates
    x = (x1 + x2) / 2
    y = (y1 + y2) / 2
    z = (z1 + z2) / 2
    
    hyp = math.hypot(x, y)
    center_lat = math.degrees(math.atan2(z, hyp))
    center_lon = math.degrees(math.atan2(y, x))

    return center_lat, center_lon

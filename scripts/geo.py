"""SIRGAS 2000 / UTM zone 21S (EPSG:31981) <-> WGS84 and isometric map projections."""

import math

from config import CX, CY, XMAX, XMIN, YMAX, YMIN

HX, HZ = (XMAX - XMIN) / 2, (YMAX - YMIN) / 2

# UTM Zone 21S (GRS80 / WGS84 ellipsoid) constants
_A = 6378137.0
_F = 1 / 298.257222101
_B = _A * (1 - _F)
_E2 = (_A**2 - _B**2) / _A**2
_E_PRIME2 = (_A**2 - _B**2) / _B**2
_E1 = (1 - math.sqrt(1 - _E2)) / (1 + math.sqrt(1 - _E2))
_K0 = 0.9996
_LON0 = -57.0  # central meridian for zone 21
_X0 = 500000.0
_Y0 = 10000000.0  # southern hemisphere false northing


def wgs_to_rd(lat, lon):
    """WGS84 lat, lon to UTM Zone 21S (x, y) meters."""
    lat_r = math.radians(lat)
    lon_r = math.radians(lon)
    lon0_r = math.radians(_LON0)

    N = _A / math.sqrt(1 - _E2 * math.sin(lat_r) ** 2)
    T = math.tan(lat_r) ** 2
    C = _E_PRIME2 * math.cos(lat_r) ** 2
    A = (lon_r - lon0_r) * math.cos(lat_r)

    M = _A * (
        (1 - _E2 / 4 - 3 * _E2**2 / 64 - 5 * _E2**3 / 256) * lat_r
        - (3 * _E2 / 8 + 3 * _E2**2 / 32 + 45 * _E2**3 / 1024) * math.sin(2 * lat_r)
        + (15 * _E2**2 / 256 + 45 * _E2**3 / 1024) * math.sin(4 * lat_r)
        - (35 * _E2**3 / 3072) * math.sin(6 * lat_r)
    )

    x = _X0 + _K0 * N * (A + (1 - T + C) * A**3 / 6 + (5 - 18 * T + T**2 + 72 * C - 58 * _E_PRIME2) * A**5 / 120)
    y = _Y0 + _K0 * (
        M
        + N
        * math.tan(lat_r)
        * (
            A**2 / 2
            + (5 - T + 9 * C + 4 * C**2) * A**4 / 24
            + (61 - 58 * T + T**2 + 600 * C - 330 * _E_PRIME2) * A**6 / 720
        )
    )
    return x, y


def rd_to_wgs(x, y):
    """UTM Zone 21S (x, y) meters to WGS84 lat, lon."""
    x_m = x - _X0
    y_m = y - _Y0
    M = y_m / _K0
    mu = M / (_A * (1 - _E2 / 4 - 3 * _E2**2 / 64 - 5 * _E2**3 / 256))
    phi1_r = (
        mu
        + (3 * _E1 / 2 - 27 * _E1**3 / 32) * math.sin(2 * mu)
        + (21 * _E1**2 / 16 - 55 * _E1**4 / 32) * math.sin(4 * mu)
        + (151 * _E1**3 / 96) * math.sin(6 * mu)
        + (1097 * _E1**4 / 512) * math.sin(8 * mu)
    )

    N1 = _A / math.sqrt(1 - _E2 * math.sin(phi1_r) ** 2)
    T1 = math.tan(phi1_r) ** 2
    C1 = _E_PRIME2 * math.cos(phi1_r) ** 2
    R1 = _A * (1 - _E2) / (1 - _E2 * math.sin(phi1_r) ** 2) ** 1.5
    D = x_m / (N1 * _K0)

    lat_r = phi1_r - (N1 * math.tan(phi1_r) / R1) * (
        D**2 / 2
        - (5 + 3 * T1 + 10 * C1 - 4 * C1**2 - 9 * _E_PRIME2) * D**4 / 24
        + (61 + 90 * T1 + 298 * C1 + 45 * T1**2 - 252 * _E_PRIME2 - 3 * C1**2) * D**6 / 720
    )
    lon_r = math.radians(_LON0) + (
        D
        - (1 + 2 * T1 + C1) * D**3 / 6
        + (5 - 2 * C1 + 28 * T1 - 3 * C1**2 + 8 * _E_PRIME2 + 24 * T1**2) * D**5 / 120
    ) / math.cos(phi1_r)
    return math.degrees(lat_r), math.degrees(lon_r)



def screen(x, z, h=0.0, look=45):
    """Local meters (x east, z south, h up) to the render's screen meters (u right, v up) for a camera looking `look`
    degrees from north, 30 degrees down (render/scene.js). Works on numbers and numpy arrays alike."""
    a = math.radians(look)
    return x * math.cos(a) + z * math.sin(a), (x * math.sin(a) - z * math.cos(a)) * 0.5 + h * math.cos(math.radians(30))


def rd_to_image(x, y, scale=4, height_m=0.0):
    """Pixel position in the full isometric render of an RD point at a height above ground (see render/scene.js)."""
    width = round(2 * (HX + HZ) / math.sqrt(2) * scale)
    lx, lz = x - CX, CY - y
    u = (lx + lz) / math.sqrt(2)
    v = (lx - lz) / (2 * math.sqrt(2)) + height_m * math.cos(math.radians(30))
    top = (HX + HZ) / math.sqrt(2) * 0.5 + 32
    return u * scale + width / 2, (top - v) * scale

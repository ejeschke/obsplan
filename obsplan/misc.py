#
# misc.py -- miscellaneous support functions
#
import math

def alt2airmass(alt_deg):
    xp = 1.0 / math.sin(math.radians(alt_deg + 244.0/(165.0 + 47*alt_deg**1.1)))
    return xp

am_inv = []
for alt in range(0, 91):
    alt_deg = float(alt)
    am = alt2airmass(alt_deg)
    am_inv.append((am, alt_deg))

def airmass2alt(am):
    for (x, alt_deg) in am_inv:
        if x <= am:
            return alt_deg
    return 90.0

def calc_slew_time(d_az, d_el, rate_az=0.5, rate_el=0.5):
    """Calculate slew time given a delta in azimuth aand elevation.
    """
    time_sec = max(math.fabs(d_el) / rate_el,
                   math.fabs(d_az) / rate_az)
    return time_sec


class Bunch(object):
    def __init__(self, **kwdargs):
        self.__dict__.update(kwdargs)

#END

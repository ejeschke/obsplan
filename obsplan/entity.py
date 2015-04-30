#
# entity.py -- various entities used for observation planning
#
#  Eric Jeschke (eric@naoj.org)
#
# Some code based on "Observer" module by Daniel Magee
#   Copyright (c) 2008 UCO/Lick Observatory.
#
from datetime import datetime
import math

# local imports
from obsplan import misc

# 3rd party imports
import ephem
import pytz
import numpy


class BaseTarget(object):
    pass

class StaticTarget(object):
    def __init__(self, name=None, ra=None, dec=None, equinox=2000.0):
        super(StaticTarget, self).__init__()
        self.name = name
        self.ra = ra
        self.dec = dec
        self.equinox = equinox

        if self.ra is not None:
            self._recalc_body()

    def _recalc_body(self):
        self.xeph_line = "%s,f|A,%s,%s,0.0,%s" % (
            self.name[:20], self.ra, self.dec, self.equinox)
        self.body = ephem.readdb(self.xeph_line)


    def import_record(self, rec):
        code = rec.code.strip()
        self.name = rec.name
        self.ra = rec.ra
        self.dec = rec.dec

        # transform equinox, e.g. "J2000" -> 2000
        eq = rec.eq
        if isinstance(eq, str):
            eq = eq.upper()
            if eq[0] in ('B', 'J'):
                eq = eq[1:]
                eq = float(eq)
        eq = int(eq)
        self.equinox = eq

        self._recalc_body()
        return code

    def calc(self, observer, time_start):
        return CalculationResult(self, observer, time_start)

    # for pickling

    def __getstate__(self):
        d = self.__dict__.copy()
        # ephem objects can't be pickled
        d['body'] = None
        return d

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.body = ephem.readdb(self.xeph_line)


class Observer(object):
    """
    Observer
    """
    def __init__(self, name, timezone=None, longitude=None, latitude=None,
                 elevation=None, pressure=None, temperature=None,
                 date=None, description=None):
        super(Observer, self).__init__()
        self.name = name
        self.timezone = timezone
        self.longitude = longitude
        self.latitude = latitude
        self.elevation = elevation
        self.pressure = pressure
        self.temperature = temperature
        self.date = date
        self.horizon = -1 * numpy.sqrt(2 * elevation / ephem.earth_radius)

        self.tz_local = pytz.timezone(self.timezone)
        self.tz_utc = pytz.timezone('UTC')
        self.site = self.get_site(date=date)

        # used for sunset, sunrise calculations
        self.horizon12 = -1.0*ephem.degrees('12:00:00.0')
        self.horizon18 = -1.0*ephem.degrees('18:00:00.0')
        self.sun = ephem.Sun()
        self.moon = ephem.Moon()
        self.sun.compute(self.site)
        self.moon.compute(self.site)

    def get_site(self, date=None, horizon_deg=None):
        site = ephem.Observer()
        site.lon = self.longitude
        site.lat = self.latitude
        site.elevation = self.elevation
        site.pressure = self.pressure
        site.temp = self.temperature
        if horizon_deg != None:
            site.horizon = math.radians(horizon_deg)
        else:
            site.horizon = self.horizon
        #site.epoch = ephem.Date("2000/1/1 12:00:00")
        if date == None:
            date = datetime.now()
            date.replace(tzinfo=self.tz_utc)
        site.date = ephem.Date(date)
        return site

    def set_date(self, date):
        try:
            date = date.astimezone(self.tz_utc)
        except Exception:
            date = self.tz_utc.localize(date)
        self.date = date
        self.site.date = ephem.Date(date)

    def calc(self, body, time_start):
        return body.calc(self, time_start)

    def get_date(self, date_str, timezone=None):
        if timezone == None:
            timezone = self.tz_local

        formats = ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d %H',
                   '%Y-%m-%d']
        for fmt in formats:
            try:
                date = datetime.strptime(date_str, fmt)
                timetup = tuple(date.timetuple()[:6])
                # re-express as timezone
                date = datetime(*timetup, tzinfo=timezone)
                return date

            except ValueError as e:
                continue

        raise e

    def observable(self, target, time_start, time_stop,
                   el_min_deg, el_max_deg, time_needed,
                   airmass=None):
        """
        Return True if `target` is observable between `time_start` and
        `time_stop`, defined by whether it is between elevation `el_min`
        and `el_max` during that period, and whether it meets the minimum
        airmass.
        """
        # set observer's horizon to elevation for el_min or to achieve
        # desired airmass
        if airmass != None:
            # compute desired altitude from airmass
            alt_deg = misc.airmass2alt(airmass)
            min_alt_deg = max(alt_deg, el_min_deg)
        else:
            min_alt_deg = el_min_deg

        site = self.get_site(date=time_start, horizon_deg=min_alt_deg)

        d1 = self.calc(target, time_start)

        # TODO: worry about el_max_deg

        # important: pyephem only deals with UTC!!
        time_start_utc = ephem.Date(time_start.astimezone(self.tz_utc))
        time_stop_utc = ephem.Date(time_stop.astimezone(self.tz_utc))
        #print "period (UT): %s to %s" % (time_start_utc, time_stop_utc)

        if d1.alt_deg >= min_alt_deg:
            # body is above desired altitude at start of period
            # so calculate next setting
            time_rise = time_start_utc
            time_set = site.next_setting(target.body, start=time_start_utc)
            #print "body already up: set=%s" % (time_set)

        else:
            # body is below desired altitude at start of period
            try:
                time_rise = site.next_rising(target.body, start=time_start_utc)
                time_set = site.next_setting(target.body, start=time_start_utc)
            except ephem.NeverUpError:
                return (False, None, None)

            #print "body not up: rise=%s set=%s" % (time_rise, time_set)
            ## if time_rise < time_set:
            ##     print "body still rising, below threshold"
            ##     # <-- body is still rising, just not high enough yet
            ## else:
            ##     # <-- body is setting
            ##     print "body setting, below threshold"
            ##     # calculate rise time backward from end of period
            ##     #time_rise = site.previous_rising(target.body, start=time_stop_utc)
            ##     pass

        if time_rise < time_start_utc:
            raise AssertionError("time rise (%s) < time start (%s)" % (
                time_rise, time_start))

        # last observable time is setting or end of period,
        # whichever comes first
        time_end = min(time_set, time_stop_utc)
        # calculate duration in seconds (subtracting two pyephem Date
        # objects seems to give a fraction in days)
        duration = (time_end - time_rise) * 86400.0
        # object is observable as long as the duration that it is
        # up is as long or longer than the time needed
        ## diff = duration - float(time_needed)
        ## can_obs = diff > -0.001
        can_obs = duration >= time_needed
        #print "can_obs=%s duration=%f needed=%f diff=%f" % (
        #    can_obs, duration, time_needed, diff)

        # convert time_rise back to a datetime (and add timezone
        # info for easy conversion to other timezones)
        time_rise = self.tz_utc.localize(time_rise.datetime())
        time_end = self.tz_utc.localize(time_end.datetime())

        return (can_obs, time_rise, time_end)

    def distance(self, tgt1, tgt2, time_start):
        """
        Calculate the distance from observer's position between two
        targets at the given time.

        Returns a tuple (alt sep deg, az sep deg)
        """
        c1 = self.calc(tgt1, time_start)
        c2 = self.calc(tgt2, time_start)

        d_alt = c1.alt_deg - c2.alt_deg
        d_az = c1.az_deg - c2.az_deg
        return (d_alt, d_az)

    def sunset(self, date=None):
        """Sunset in UTC"""
        self.site.horizon = self.horizon
        if date is None:
            date = self.date
        self.site.date = ephem.Date(date)
        r_date = self.site.next_setting(self.sun)
        return self.tz_utc.localize(r_date.datetime())

    def sunrise(self, date=None):
        """Sunrise in UTC"""
        self.site.horizon = self.horizon
        if date is None:
            date = self.date
        self.site.date = ephem.Date(date)
        r_date = self.site.next_rising(self.sun)
        return self.tz_utc.localize(r_date.datetime())

    def evening_twilight_12(self, date=None):
        """Evening 12 degree (nautical) twilight in UTC"""
        self.site.horizon = self.horizon12
        if date is None:
            date = self.date
        self.site.date = ephem.Date(date)
        r_date = self.site.next_setting(self.sun)
        return self.tz_utc.localize(r_date.datetime())

    def evening_twilight_18(self, date=None):
        """Evening 18 degree (civil) twilight"""
        self.site.horizon = self.horizon18
        if date is None:
            date = self.date
        self.site.date = ephem.Date(date)
        r_date = self.site.next_setting(self.sun)
        return self.tz_utc.localize(r_date.datetime())

    def morning_twilight_12(self, date=None):
        """Morning 12 degree (nautical) twilight in UTC"""
        self.site.horizon = self.horizon12
        if date is None:
            date = self.date
        self.site.date = ephem.Date(date)
        r_date = self.site.next_rising(self.sun)
        return self.tz_utc.localize(r_date.datetime())

    def morning_twilight_18(self, date=None):
        """Morning 18 degree (civil) twilight in UTC"""
        self.site.horizon = self.horizon18
        if date is None:
            date = self.date
        self.site.date = ephem.Date(date)
        r_date = self.site.next_rising(self.sun)
        return self.tz_utc.localize(r_date.datetime())

    def sun_set_rise_times(self, date):
        """
        Sunset, sunrise and twilight times.
        Returns a tuple with (sunset, 12d, 18d, 18d, 12d, sunrise).
        """
        rstimes = (self.sunset(date=date),
                   self.evening_twilight_12(date=date),
                   self.evening_twilight_18(date=date),
                   self.morning_twilight_18(date=date),
                   self.morning_twilight_12(date=date),
                   self.sunrise(date=date),
                   )
        return rstimes

    def moon_rise(self, date=None):
        """Moon rise time in UTC"""
        if date is None:
            date = self.date
        self.site.date = date
        moonrise = self.site.next_rising(self.moon)
        moonrise = self.tz_utc.localize(moonrise.datetime())
        if moonrise < self.sunset(date):
            None
        return moonrise

    def moon_set(self, date=None):
        """Moon set time in UTC"""
        if date is None:
            date = self.date
        self.site.date = date
        moonset = self.site.next_setting(self.moon)
        moonset = self.tz_utc.localize(moonset.datetime())
        if moonset > self.sunrise(date):
            moonset = None
        return moonset

    def moon_phase(self, date=None):
        """Moon percentage of illumination"""
        if date is None:
            date = self.date
        self.site.date = ephem.Date(date)
        return self.moon.moon_phase

    def night_center(self, date=None):
        """Compute night center"""
        return (self.sunset(date=date) + self.sunrise(date=date))/2.0

    def local2utc(self, date_s):
        """Convert local time to UTC"""
        y, m, d = date_s.split('/')
        tlocal = datetime(int(y), int(m), int(d), 12, 0, 0,
                          tzinfo=self.tz_local)
        r_date = ephem.Date(tlocal.astimezone(self.tz_utc))
        return r_date

    def utc2local(self, date_time):
        """Convert UTC to local time"""
        if date_time != None:
            dt = date_time.datetime()
            utc_dt = datetime(dt.year, dt.month, dt.day, dt.hour, dt.minute,
                              dt.second, dt.microsecond, tzinfo=self.tz_utc)
            r_date = ephem.Date(utc_dt.astimezone(self.tz_local))
            return r_date
        else:
            return None

    def get_text_almanac(self, date, tz=None):
        if tz == None:
            tz = self.tz_local
        date_s = date.astimezone(tz).strftime("%Y-%m-%d")
        text = ''
        text += 'Almanac for the night of %s\n' % date_s.split()[0]
        text += '\nEvening\n'
        text += '_'*30 + '\n'
        rst = self.sun_set_rise_times(date)
        rst = [t.astimezone(tz).strftime('%H:%M') for t in rst]
        text += 'Sunset: %s\n12d: %s\n18d: %s\n' % (rst[0], rst[1], rst[2])
        text += '\nMorning\n'
        text += '_'*30 + '\n'
        text += '18d: %s\n12d: %s\nSunrise: %s\n' % (rst[3], rst[4], rst[5])
        return text

    def get_target_info(self, target, time_start=None, time_stop=None,
                        time_interval=5):
        """Compute various values for a target from sunrise to sunset"""

        def _set_time(dtime):
            # Sets time to nice rounded value
            y, m ,d, hh, mm, ss = dtime.tuple()
            mm = mm - (mm % time_interval)
            return ephem.Date(datetime(y, m, d, hh, mm, 5, 0))

        def _set_data_range(sunset, sunrise, tint):
            # Returns numpy array of dates 15 minutes before sunset
            # and after sunrise
            ss = _set_time(ephem.Date(sunset - 15*ephem.minute))
            sr = _set_time(ephem.Date(sunrise + 15*ephem.minute))
            return numpy.arange(ss, sr, tint)

        if time_start == None:
            # default for start time is sunset on the current date
            time_start = self.sunset()
        if time_stop == None:
            # default for stop time is sunrise on the current date
            time_stop = self.sunrise(date=time_start)

        t_range = _set_data_range(ephem.Date(time_start.astimezone(self.tz_utc)),
                                  ephem.Date(time_stop.astimezone(self.tz_utc)),
                                  time_interval*ephem.minute)

        # TODO: this should probably return a generator
        ## def history():
        ##     for ut in t_range:
        ##         # ugh
        ##         tup = ephem.Date(ut).tuple()
        ##         args = tup[:-1] + (int(tup[-1]),)
        ##         ut_with_tz = datetime(*args,
        ##                               tzinfo=self.tz_utc)
        ##         info = target.calc(self, ut_with_tz)
        ##         yield info

        ## return history()

        history = []
        for ut in t_range:
            # ugh
            tup = ephem.Date(ut).tuple()
            args = tup[:-1] + (int(tup[-1]),)
            ut_with_tz = datetime(*args,
                                  tzinfo=self.tz_utc)
            info = target.calc(self, ut_with_tz)
            history.append(info)
        return history


    def get_target_info_table(self, target, time_start=None, time_stop=None,
                              time_interval=5):
        """Prints a table of hourly airmass data"""
        history = self.get_target_info(target, time_start=time_start,
                                       time_stop=time_stop,
                                       time_interval=time_interval)
        text = []
        format_hdr = '%(date)-16s  %(utc)5s  %(lmst)5s  %(ha)5s  %(pa)7s %(am)6s %(ma)6s %(ms)7s'
        header = dict(date='Date', utc='UTC', lmst='LMST',
                      ha='HA', pa='PA', am='AM', ma='MnAlt', ms='MnSep')
        hstr = format_hdr % header
        text.append(hstr)
        text.append('_'*len(hstr))

        format_line = '%(date)-16s  %(utc)5s  %(lmst)5s  %(ha)5s  %(pa)7.2f %(am)6.2f %(ma)6.2f %(ms)7.2f'

        for info in history:
            s_date = info.lt.astimezone(self.tz_local).strftime('%d%b%Y  %H:%M')
            s_utc = info.lt.astimezone(self.tz_utc).strftime('%H:%M')
            s_ha = ':'.join(str(ephem.hours(info.ha)).split(':')[:2])
            s_lmst = ':'.join(str(ephem.hours(info.lmst)).split(':')[:2])
            pa = float(numpy.degrees(info.pang))
            am = float(info.airmass)
            ma = float(numpy.degrees(info.moon_alt))
            ms = float(numpy.degrees(info.moon_sep))
            line = dict(date=s_date, utc=s_utc, lmst=s_lmst,
                        ha=s_ha, pa=pa, am=am, ma=ma, ms=ms)
            s_data = format_line % line
            text.append(s_data)
        return '\n'.join(text)

    def __repr__(self):
        return self.name

    __str__ = __repr__


class CalculationResult(object):

    def __init__(self, target, observer, date):
        # TODO: make a COPY of observer.site
        self.observer = observer
        self.site = observer.site
        self.body = target.body
        self.date = date

        # Can/should this calculation be postponed?
        observer.set_date(date)
        self.body.compute(self.site)

        self.lt = self.date.astimezone(observer.tz_local)
        self.ra = self.body.ra
        self.dec = self.body.dec
        self.alt = float(self.body.alt)
        self.az = float(self.body.az)
        # TODO: deprecate
        self.alt_deg = math.degrees(self.alt)
        self.az_deg = math.degrees(self.az)

        # properties
        self._ut = None
        self._gmst = None
        self._lmst = None
        self._ha = None
        self._pang = None
        self._am = None
        self._moon_alt = None
        self._moon_pct = None
        self._moon_sep = None


    @property
    def ut(self):
        if self._ut is None:
            self._ut = self.lt.astimezone(pytz.utc)
        return self._ut

    @property
    def gmst(self):
        if self._gmst is None:
            jd = ephem.julian_date(self.ut)
            T = (jd - 2451545.0)/36525.0
            gmstdeg = 280.46061837+(360.98564736629*(jd-2451545.0))+(0.000387933*T*T)-(T*T*T/38710000.0)
            self._gmst = ephem.degrees(gmstdeg*numpy.pi/180.0)
        return self._gmst

    @property
    def lmst(self):
        if self._lmst is None:
            lmst = ephem.degrees(self.gmst + self.site.long)
            self._lmst = lmst.norm
        return self._lmst

    @property
    def ha(self):
        if self._ha is None:
            self._ha = self.lmst - self.ra
        return self._ha

    @property
    def pang(self):
        if self._pang is None:
            self._pang = self.calc_parallactic(float(self.dec),
                                               float(self.ha),
                                               float(self.site.lat),
                                               self.az)
        return self._pang

    @property
    def airmass(self):
        if self._am is None:
            self._am = self.calc_airmass(self.alt)
        return self._am

    @property
    def moon_alt(self):
        if self._moon_alt is None:
            moon_alt, moon_pct, moon_sep = self.calc_moon(self.site, self.body)
            self._moon_alt = moon_alt
            self._moon_pct = moon_pct
            self._moon_sep = moon_sep
        return self._moon_alt

    @property
    def moon_pct(self):
        if self._moon_pct is None:
            moon_alt, moon_pct, moon_sep = self.calc_moon(self.site, self.body)
            self._moon_alt = moon_alt
            self._moon_pct = moon_pct
            self._moon_sep = moon_sep
        return self._moon_pct

    @property
    def moon_sep(self):
        if self._moon_sep is None:
            moon_alt, moon_pct, moon_sep = self.calc_moon(self.site, self.body)
            self._moon_alt = moon_alt
            self._moon_pct = moon_pct
            self._moon_sep = moon_sep
        return self._moon_sep

    def calc_GMST(self, date):
        """Compute Greenwich Mean Sidereal Time"""
        jd = ephem.julian_date(date)
        T = (jd - 2451545.0)/36525.0
        gmstdeg = 280.46061837+(360.98564736629*(jd-2451545.0))+(0.000387933*T*T)-(T*T*T/38710000.0)
        gmst = ephem.degrees(gmstdeg*numpy.pi/180.0)
        return gmst

    def calc_LMST(self, date, longitude):
        """Compute Local Mean Sidereal Time"""
        gmst = self.calc_GMST(date)
        lmst = ephem.degrees(gmst + longitude)
        return lmst.norm

    def calc_HA(self, lmst, ra):
        """Compute Hour Angle"""
        return lmst - ra

    def calc_parallactic(self, dec, ha, lat, az):
        """Compute parallactic angle"""
        if numpy.cos(dec) != 0.0:
            sinp = -1.0*numpy.sin(az)*numpy.cos(lat)/numpy.cos(dec)
            cosp = -1.0*numpy.cos(az)*numpy.cos(ha)-numpy.sin(az)*numpy.sin(ha)*numpy.sin(lat)
            parang = ephem.degrees(numpy.arctan2(sinp, cosp))
        else:
            if lat > 0.0:
                parang = numpy.pi
            else:
                parang = 0.0
        return parang

    def calc_airmass(self, alt):
        """Compute airmass"""
        if alt < ephem.degrees('03:00:00'):
            alt = ephem.degrees('03:00:00')
        sz = 1.0/numpy.sin(alt) - 1.0
        xp = 1.0 + sz*(0.9981833 - sz*(0.002875 + 0.0008083*sz))
        return xp

    def calc_moon(self, site, body):
        """Compute Moon altitude"""
        moon = ephem.Moon()
        self.observer.set_date(self.date)
        moon.compute(site)
        moon_alt = float(moon.alt)
        # moon.phase is % of moon that is illuminated
        moon_pct = moon.moon_phase
        # calculate distance from target
        moon_sep = ephem.separation(moon, body)
        moon_sep = float(moon_sep)
        return (moon_alt, moon_pct, moon_sep)

    def calc_separation_alt_az(self, target):
        """Compute deltas for azimuth and altitude from another target"""
        self.target.body.compute(self.observer.site)
        target.body.compute(self.observer.site)

        delta_az = float(self.body.az) - float(target.az)
        delta_alt = float(self.body.alt) - float(target.alt)
        return (delta_alt, delta_az)

# define some common bodies
moon = StaticTarget(name="Moon")
moon.body = ephem.Moon()
sun = StaticTarget(name="Sun")
sun.body = ephem.Sun()
mercury = StaticTarget(name="Mercury")
mercury.body = ephem.Mercury()
venus = StaticTarget(name="Venus")
venus.body = ephem.Venus()
mars = StaticTarget(name="Mars")
mars.body = ephem.Mars()
jupiter = StaticTarget(name="Jupiter")
jupiter.body = ephem.Jupiter()
saturn = StaticTarget(name="Saturn")
saturn.body = ephem.Saturn()
uranus = StaticTarget(name="Uranus")
uranus.body = ephem.Uranus()
neptune = StaticTarget(name="Neptune")
neptune.body = ephem.Neptune()
pluto = StaticTarget(name="Pluto")
pluto.body = ephem.Pluto()


#END

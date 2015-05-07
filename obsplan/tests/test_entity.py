from datetime import datetime
import unittest
import math

import pytz
import ephem

from obsplan import entity


        # RA           DEC          EQ
vega = ("18:36:56.3", "+38:47:01", "2000")
altair = ("19:51:29.74", "8:54:23.5", "2000")

class TestEntity01(unittest.TestCase):

    def setUp(self):
        self.hst = pytz.timezone('US/Hawaii')
        self.utc = pytz.utc
        self.obs = entity.Observer('subaru',
                                   longitude='-155:28:48.900',
                                   latitude='+19:49:42.600',
                                   elevation=4163,
                                   pressure=615,
                                   temperature=0,
                                   timezone='US/Hawaii')

    def tearDown(self):
        pass

    def test_get_date0(self):
        time1 = self.obs.get_date("2014-04-15 19:00")
        time2 = datetime(2014, 04, 15, 19, 0, 0)
        time2 = self.hst.localize(time2)
        self.assert_(time1 == time2)

    def test_get_date1(self):
        time1 = self.obs.get_date("2014-04-15 19:00")
        time2 = self.obs.get_date("2014-04-15 20:00")
        ## print((1, time1.astimezone(self.obs.tz_local).strftime("%H:%M"),
        ##        time2.astimezone(self.obs.tz_local).strftime("%H:%M")))
        self.assert_(time1 < time2)

    def test_get_tgt(self):
        tgt = entity.SiderealTarget(name="vega", ra=vega[0], dec=vega[1])
        self.assert_(isinstance(tgt.body, ephem.Body))

    def test_observable_1(self):
        # vega should be visible during this period
        tgt = entity.SiderealTarget(name="vega", ra=vega[0], dec=vega[1])
        cts = entity.Constraints(time_start=self.obs.get_date("2014-04-29 04:00"),
                                 time_stop=self.obs.get_date("2014-04-29 05:00"),
                                 el_min_deg=15.0, el_max_deg=85.0,
                                 duration=59.9*60, airmass=None)
        cts = self.obs.observable(tgt, cts)
        ## print((1, cts.observable,
        ##        cts.time_rise.astimezone(self.obs.tz_local).strftime("%H:%M"),
        ##        cts.time_set.astimezone(self.obs.tz_local).strftime("%H:%M")))
        self.assert_(cts.observable == True)

    def test_observable_2(self):
        # vega should be visible near the end but not in the beginning
        # during this period (rising)
        tgt = entity.SiderealTarget(name="vega", ra=vega[0], dec=vega[1])
        cts = entity.Constraints(time_start=self.obs.get_date("2014-04-28 22:30"),
                                 time_stop=self.obs.get_date("2014-04-28 23:30"),
                                 el_min_deg=15.0, el_max_deg=85.0,
                                 duration=45*60, airmass=None)
        cts = self.obs.observable(tgt, cts)
        self.assert_(cts.observable == True)   # 45 min OK

    def test_observable_3(self):
        # vega should be visible near the end but not in the beginning
        # during this period (rising)
        tgt = entity.SiderealTarget(name="vega", ra=vega[0], dec=vega[1])
        cts = entity.Constraints(time_start=self.obs.get_date("2014-04-28 22:30"),
                                 time_stop=self.obs.get_date("2014-04-28 23:30"),
                                 el_min_deg=15.0, el_max_deg=85.0,
                                 duration=50*60, airmass=None)
        cts = self.obs.observable(tgt, cts)
        self.assert_(cts.observable == False)  # 50 min NOT ok

    def test_observable_4(self):
        # vega should be visible near the beginning but not near the end
        # during this period (setting)
        tgt = entity.SiderealTarget(name="vega", ra=vega[0], dec=vega[1])
        cts = entity.Constraints(time_start=self.obs.get_date("2014-04-29 09:30"),
                                 time_stop=self.obs.get_date("2014-04-29 10:30"),
                                 el_min_deg=15.0, el_max_deg=85.0,
                                 duration=30*60, airmass=None)
        cts = self.obs.observable(tgt, cts)
        self.assert_(cts.observable == True)  # 30 min ok

    def test_observable_5(self):
        # vega should be visible near the beginning but not near the end
        # during this period (setting)
        tgt = entity.SiderealTarget(name="vega", ra=vega[0], dec=vega[1])
        cts = entity.Constraints(time_start=self.obs.get_date("2014-04-29 09:30"),
                                 time_stop=self.obs.get_date("2014-04-29 10:30"),
                                 el_min_deg=15.0, el_max_deg=85.0,
                                 duration=45*60, airmass=None)
        cts = self.obs.observable(tgt, cts)
        self.assert_(cts.observable == False)  # 45 min NOT ok

    def test_observable_6(self):
        # vega should be visible near the beginning but not near the end
        # during this period (setting)
        tgt = entity.SiderealTarget(name="vega", ra=vega[0], dec=vega[1])
        cts = entity.Constraints(time_start=self.obs.get_date("2014-04-29 10:00"),
                                 time_stop=self.obs.get_date("2014-04-29 11:00"),
                                 el_min_deg=15.0, el_max_deg=85.0,
                                 duration=15*60, airmass=None)
        cts = self.obs.observable(tgt, cts)
        self.assert_(cts.observable == False)    # 15 min NOT ok

    def test_airmass1(self):
        # now calculate via misc
        body = entity.SiderealTarget(name='ACTJ0022-0036',
                                   ra='00:22:13.44', dec='-00:36:25.20')
        time1 = self.obs.get_date("2010-10-18 21:00")
        c1 = self.obs.calc(body, time1)
        self.assert_(c1.airmass > 1.13)

    def test_distance_1(self):
        tgt1 = entity.SiderealTarget(name="vega", ra=vega[0], dec=vega[1])
        tgt2 = entity.SiderealTarget(name="altair", ra=altair[0], dec=altair[1])
        time1 = self.obs.get_date("2010-10-18 22:30")
        d_alt, d_az = self.obs.distance(tgt1, tgt2, time1)
        self.assertEquals(str(d_alt)[:7], '-9.9657')
        self.assertEquals(str(d_az)[:7], '36.1910')


if __name__ == "__main__":

    print '\n>>>>> Starting test_misc <<<<<\n'
    unittest.main()

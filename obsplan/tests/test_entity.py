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
        tgt = entity.StaticTarget(name="vega", ra=vega[0], dec=vega[1])
        self.assert_(isinstance(tgt.body, ephem.Body))

    def test_observable_1(self):
        # vega should be visible during this period
        tgt = entity.StaticTarget(name="vega", ra=vega[0], dec=vega[1])
        time1 = self.obs.get_date("2014-04-29 04:30")
        time2 = self.obs.get_date("2014-04-29 05:30")
        is_obs, t1, t2 = self.obs.observable(tgt, time1, time2,
                                             15.0, 85.0, 59.9*60)
        ## print((1, is_obs,
        ##        t1.astimezone(self.obs.tz_local).strftime("%H:%M"),
        ##        t2.astimezone(self.obs.tz_local).strftime("%H:%M")))
        self.assert_(is_obs == True)

    def test_observable_2(self):
        # vega should be visible near the end but not in the beginning
        # during this period (rising)
        tgt = entity.StaticTarget(name="vega", ra=vega[0], dec=vega[1])
        time1 = self.obs.get_date("2014-04-28 22:30")
        time2 = self.obs.get_date("2014-04-28 23:30")
        is_obs, t1, t2 = self.obs.observable(tgt, time1, time2, 15.0, 85.0,
                                             60*45)  # 45 min ok
        self.assert_(is_obs == True)

    def test_observable_3(self):
        # vega should be visible near the end but not in the beginning
        # during this period (rising)
        tgt = entity.StaticTarget(name="vega", ra=vega[0], dec=vega[1])
        time1 = self.obs.get_date("2014-04-28 22:30")
        time2 = self.obs.get_date("2014-04-28 23:30")
        is_obs, t1, t2 = self.obs.observable(tgt, time1, time2, 15.0, 85.0,
                                              60*50)  # 50 min NOT ok
        self.assert_(is_obs == False)

    def test_observable_4(self):
        # vega should be visible near the beginning but not near the end
        # during this period (setting)
        tgt = entity.StaticTarget(name="vega", ra=vega[0], dec=vega[1])
        time1 = self.obs.get_date("2014-04-29 09:30")
        time2 = self.obs.get_date("2014-04-29 10:30")
        is_obs, t1, T2 = self.obs.observable(tgt, time1, time2, 15.0, 85.0,
                                             60*30)  # 30 min ok
        self.assert_(is_obs == True)

    def test_observable_5(self):
        # vega should be visible near the beginning but not near the end
        # during this period (setting)
        tgt = entity.StaticTarget(name="vega", ra=vega[0], dec=vega[1])
        time1 = self.obs.get_date("2014-04-29 09:30")
        time2 = self.obs.get_date("2014-04-29 10:30")
        is_obs, t1, t2 = self.obs.observable(tgt, time1, time2, 15.0, 85.0,
                                             60*45)  # 45 min NOT ok
        self.assert_(is_obs == False)

    def test_observable_6(self):
        # vega should be visible near the beginning but not near the end
        # during this period (setting)
        tgt = entity.StaticTarget(name="vega", ra=vega[0], dec=vega[1])
        time1 = self.obs.get_date("2014-04-29 10:00")
        time2 = self.obs.get_date("2014-04-29 11:00")
        is_obs, t1, t2 = self.obs.observable(tgt, time1, time2, 15.0, 85.0,
                                             60*15)  # 15 min NOT ok
        self.assert_(is_obs == False)

    def test_airmass1(self):
        # now calculate via misc
        body = entity.StaticTarget(name='ACTJ0022-0036',
                                   ra='00:22:13.44', dec='-00:36:25.20')
        time1 = self.obs.get_date("2010-10-18 21:00")
        c1 = self.obs.calc(body, time1)
        self.assert_(c1.airmass > 1.13)

    def test_distance_1(self):
        tgt1 = entity.StaticTarget(name="vega", ra=vega[0], dec=vega[1])
        tgt2 = entity.StaticTarget(name="altair", ra=altair[0], dec=altair[1])
        time1 = self.obs.get_date("2010-10-18 22:30")
        d_alt, d_az = self.obs.distance(tgt1, tgt2, time1)
        self.assertEquals(str(d_alt)[:7], '-9.9657')
        self.assertEquals(str(d_az)[:7], '36.1910')


if __name__ == "__main__":

    print '\n>>>>> Starting test_misc <<<<<\n'
    unittest.main()

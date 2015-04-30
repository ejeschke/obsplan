#
# plots.py -- does matplotlib plots needed for observation planning
#
# Eric Jeschke (eric@naoj.org)
#
# Some code based on "Observer" module by Daniel Magee
#   Copyright (c) 2008 UCO/Lick Observatory.
#
from __future__ import print_function
from datetime import datetime, timedelta
import pytz
import numpy

from matplotlib import figure
import matplotlib.dates as mpl_dt
import matplotlib as mpl

from obsplan import misc

class AirMassPlot(object):

    def __init__(self, width, height, dpi=96):
        # time increments, by minute
        self.time_inc_min = 15

        # create matplotlib figure
        self.fig = figure.Figure(figsize=(width, height), dpi=dpi)

        # colors used for successive points
        self.colors = ['r', 'b', 'g', 'c', 'm', 'y']

    def setup(self):
        pass

    def get_figure(self):
        return self.fig

    def make_canvas(self):
        canvas = FigureCanvas(self.fig)
        return canvas

    ## def get_ax(self):
    ##     return self.ax

    def clear(self):
        #self.ax.cla()
        self.fig.clf()

    def plot_targets(self, site, targets, tz):
        num_tgts = len(targets)
        target_data = []
        lengths = []
        if num_tgts > 0:
            for tgt in targets:
                info_list = site.get_target_info(tgt)
                target_data.append(misc.Bunch(history=info_list, target=tgt))
                lengths.append(len(info_list))

        # clip all arrays to same length
        # TODO: won't work if these become generators instead of lists
        min_len = min(*lengths)
        for info in target_data:
            info.history = info.history[:min_len]

        self.plot_airmass(site, target_data, tz)

    def plot_airmass(self, site, tgt_data, tz):
        self._plot_airmass(self.fig, site, tgt_data, tz)


    def _plot_airmass(self, figure, site, tgt_data, tz):
        """
        Plot into `figure` an airmass chart using target data from `info`
        with time plotted in timezone `tz` (a tzinfo instance).
        """
        # Urk! This seems to be necessary even though we are plotting
        # python datetime objects with timezone attached and setting
        # date formatters with the timezone
        tz_str = tz.tzname(None)
        mpl.rcParams['timezone'] = tz_str

        # set major ticks to hours
        majorTick = mpl_dt.HourLocator(tz=tz)
        majorFmt = mpl_dt.DateFormatter('%Hh')
        # set minor ticks to 15 min intervals
        minorTick = mpl_dt.MinuteLocator(range(0,59,15), tz=tz)

        figure.clf()
        ax1 = figure.add_subplot(111)

        #lstyle = 'o'
        lstyle = '-'
        lt_data = map(lambda info: info.ut.astimezone(tz),
                      tgt_data[0].history)
        # sanity check on dates in preferred timezone
        ## for dt in lt_data[:10]:
        ##     print(dt.strftime("%Y-%m-%d %H:%M:%S"))

        # plot targets airmass vs. time
        for i, info in enumerate(tgt_data):
            am_data = numpy.array(map(lambda info: info.airmass, info.history))
            am_min = numpy.argmin(am_data)
            am_data_dots = am_data
            color = self.colors[i % len(self.colors)]
            lc = color + lstyle
            # ax1.plot_date(lt_data, am_data, lc, linewidth=1.0, alpha=0.3, aa=True, tz=tz)
            ax1.plot_date(lt_data, am_data_dots, lc, linewidth=2.0,
                          aa=True, tz=tz)
            #xs, ys = mpl.mlab.poly_between(lt_data, 2.02, am_data)
            #ax1.fill(xs, ys, facecolor=self.colors[i], alpha=0.2)

            # plot object label
            targname = info.target.name
            ax1.text(mpl_dt.date2num(lt_data[am_data.argmin()]),
                     am_data.min() + 0.08, targname.upper(), color=color,
                     ha='center', va='center')

        ax1.set_ylim(2.02, 0.98)
        ax1.set_xlim(lt_data[0], lt_data[-1])
        ax1.xaxis.set_major_locator(majorTick)
        ax1.xaxis.set_minor_locator(minorTick)
        ax1.xaxis.set_major_formatter(majorFmt)
        labels = ax1.get_xticklabels()
        ax1.grid(True, color='#999999')

        # plot current hour
        lo = datetime.now(tz)
        #lo = datetime.now(tz=tz)
        hi = lo + timedelta(0, 3600.0)
        if lt_data[0] < lo < lt_data[-1]:
            ax1.axvspan(lo, hi, facecolor='#7FFFD4', alpha=0.25)

        # label axes
        localdate = lt_data[0].astimezone(tz).strftime("%Y-%m-%d")
        title = 'Airmass for the night of %s' % (localdate)
        ax1.set_title(title)
        ax1.set_xlabel(tz.tzname(None))
        ax1.set_ylabel('Airmass')

        # Plot moon altitude and degree scale
        ax2 = ax1.twinx()
        moon_data = numpy.array(map(lambda info: numpy.degrees(info.moon_alt),
                                    tgt_data[0].history))
        #moon_illum = site.moon_phase()
        ax2.plot_date(lt_data, moon_data, '#666666', linewidth=2.0,
                      alpha=0.5, aa=True, tz=tz)
        mxs, mys = mpl.mlab.poly_between(lt_data, 0, moon_data)
        # ax2.fill(mxs, mys, facecolor='#666666', alpha=moon_illum)
        ax2.set_ylabel('Moon Altitude (deg)', color='#666666')
        ax2.set_ylim(0, 90)
        ax2.set_xlim(lt_data[0], lt_data[-1])
        ax2.xaxis.set_major_locator(majorTick)
        ax2.xaxis.set_minor_locator(minorTick)
        ax2.xaxis.set_major_formatter(majorFmt)
        ax2.set_xlabel('')
        ax2.yaxis.tick_right()

        canvas = self.fig.canvas
        if canvas is not None:
            canvas.draw()

if __name__ == '__main__':
    import sys
    from obsplan import entity
    from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
    from PyQt4 import QtGui

    app = QtGui.QApplication([])
    plot = AirMassPlot(10, 6)
    plot.setup()
    outfile = None
    if len(sys.argv) > 1:
        outfile = sys.argv[1]

    tz = pytz.timezone('US/Hawaii')
    site = entity.Observer('subaru',
                             longitude='-155:28:48.900',
                             latitude='+19:49:42.600',
                             elevation=4163,
                             pressure=615,
                             temperature=0,
                             timezone='US/Hawaii')

    start_time = datetime.strptime("2015-03-30 18:30:00",
                                   "%Y-%m-%d %H:%M:%S")
    start_time = tz.localize(start_time)
    t = start_time
    # if schedule starts after midnight, change start date to the
    # day before
    if 0 <= t.hour < 12:
        t -= timedelta(0, 3600*12)
    ndate = t.strftime("%Y/%m/%d")

    targets = []
    site.set_date(t)
    tgt = entity.StaticTarget(name='S5', ra='14:20:00.00', dec='48:00:00.00')
    targets.append(tgt)
    tgt = entity.StaticTarget(name='Sf', ra='09:40:00.00', dec='43:00:00.00')
    targets.append(tgt)
    tgt = entity.StaticTarget(name='Sm', ra='10:30:00.00', dec='36:00:00.00')
    targets.append(tgt)
    tgt = entity.StaticTarget(name='Sn', ra='15:10:00.00', dec='34:00:00.00')
    targets.append(tgt)

    # make airmass plot
    plot.plot_targets(site, targets, tz)

    if outfile == None:
        canvas = plot.make_canvas()
        canvas.show()
    else:
        canvas = plot.make_canvas()    # is this necessary?
        self.fig.savefig(outfile)

    app.exec_()



#END

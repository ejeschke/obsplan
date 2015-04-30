import math
from datetime import datetime

import matplotlib
from matplotlib import rc, figure


class AZELPlot(object):

    def __init__(self, width, height, dpi=96):
        # radar green, solid grid lines
        rc('grid', color='#316931', linewidth=1, linestyle='-')
        rc('xtick', labelsize=10)
        rc('ytick', labelsize=10)

        # altitude increments, by degree
        self.alt_inc_deg = 15

        # create matplotlib figure
        self.fig = figure.Figure(figsize=(width, height), dpi=dpi)

        # colors used for successive points
        self.colors = ['r', 'b', 'g', 'c', 'm', 'y']

    def setup(self):
        ax = self.fig.add_axes([0.1, 0.1, 0.8, 0.8],
                               projection='polar', axisbg='#d5de9c')
        ## self.zp = zp.ZoomPan()
        ## self.zp.zoom_factory(ax, base_scale=1.5)
        ## self.zp.pan_factory(ax)
        self.ax = ax
        # don't clear plot when we call plot()
        ax.hold(True)
        #ax.set_title("Slew order", fontsize=14)
        self.orient_plot()

    def get_figure(self):
        return self.fig

    def get_ax(self):
        return self.ax

    def make_canvas(self):
        canvas = FigureCanvas(self.fig)
        return canvas

    def clear(self):
        self.ax.cla()
        self.redraw()

    def map_azalt(self, az, alt):
        return (math.radians(az - 180.0), 90.0 - alt)

    def orient_plot(self):
        ax = self.ax
        # Orient plot for Subaru telescope
        ax.set_theta_zero_location("S")
        #ax.set_theta_direction(-1)
        ax.set_theta_direction(1)

        # standard polar projection has radial plot running 0 to 90,
        # inside to outside.
        # Adjust radius so it goes 90 at the center to 0 at the perimeter
        #ax.set_ylim(90, 0)   # (doesn't work)

        # Redefine yticks and labels
        #alts = [0, 15, 60, 70, 90]
        alts = range(0, 90, self.alt_inc_deg)
        ax.set_yticks(alts)
        #alts_r = list(alts)
        #alts_r.reverse()
        alts_r = range(90, 0, -self.alt_inc_deg)
        ax.set_yticklabels(map(str, alts_r))
        # maximum altitude of 90.0
        ax.set_rmax(90.0)
        ax.grid(True)

        # add compass annotations
        ## for az, d in ((0.0, 'S'), (90.0, 'W'), (180.0, 'N'), (270.0, 'E')):
        ##     ax.annotate(d, xy=self.map_azalt(az, 0.0), textcoords='data')
        ax.annotate('W', (1.08, 0.5), textcoords='axes fraction',
                    fontsize=16)
        ax.annotate('E', (-0.1, 0.5), textcoords='axes fraction',
                    fontsize=16)
        ax.annotate('N', (0.5, 1.08), textcoords='axes fraction',
                    fontsize=16)
        ax.annotate('S', (0.5, -0.08), textcoords='axes fraction',
                    fontsize=16)

    def redraw(self):
        self.orient_plot()

        canvas = self.fig.canvas
        if canvas is not None:
            canvas.draw()

    def plot_coords(self, coords):

        ax = self.ax
        lstyle = 'o'

        for i, tup in enumerate(coords):
            color = self.colors[i % len(self.colors)]
            lc = color + lstyle

            # alt: invert the radial axis
            az, alt = self.map_azalt(tup[0], tup[1])
            name = tup[2]
            ax.plot([az], [alt], lc)
            ax.annotate(name, (az, alt))

        #self.orient_plot()

        self.redraw()

    def plot_azel(self, coords, outfile=None):

        self.plot_coords(coords)

        if outfile == None:
            self.canvas = self.make_canvas()
            self.canvas.show()
        else:
            self.canvas = self.make_canvas()
            self.fig.savefig(outfile)

    def _plot_target(self, observer, target, time_start, color):
        info = target.calc(observer, time_start)
        az, alt = self.map_azalt(info.az_deg, info.alt_deg)
        self.ax.plot([az], [alt], 'o', color=color)
        self.ax.annotate(target.name, (az, alt))
        self.redraw()

    def plot_target(self, observer, target, time_start, color):
        self._plot_target(observer, target, time_start, color)
        self.redraw()

    def plot_targets(self, observer, targets, time_start, colors=None):
        if colors is None:
            colors = self.colors
        i = 0
        for target in targets:
            self._plot_target(observer, target, time_start, colors[i])
            i = (i+1) % len(colors)
        self.redraw()

if __name__ == '__main__':
    from obsplan import entity
    import pytz
    from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
    from PyQt4 import QtGui
    import ephem

    app = QtGui.QApplication([])
    plot = AZELPlot(10, 10)
    plot.setup()
    plot.plot_azel([(-210.0, 60.43, "telescope"),])
    tgt3 = entity.StaticTarget(name="Bootes", ra="14:31:45.40",
                               dec="+32:28:38.50")
    tz = pytz.timezone('US/Hawaii')
    site = entity.Observer('subaru',
                             longitude='-155:28:48.900',
                             latitude='+19:49:42.600',
                             elevation=4163,
                             pressure=615,
                             temperature=0,
                             timezone='US/Hawaii')

    start_time = datetime.strptime("2015-03-27 20:05:00",
                                   "%Y-%m-%d %H:%M:%S")
    start_time = tz.localize(start_time)

    plot.plot_targets(site, [entity.moon, entity.sun, tgt3],
                      start_time, ['white', 'yellow', 'green'])
    app.exec_()

#END

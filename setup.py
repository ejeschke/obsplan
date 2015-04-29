#! /usr/bin/env python
#
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup
from obsplan.version import version
import os

srcdir = os.path.dirname(__file__)

from distutils.command.build_py import build_py

def read(fname):
    buf = open(os.path.join(srcdir, fname), 'r').read()
    return buf

setup(
    name = "obsplan",
    version = version,
    author = "Eric Jeschke",
    author_email = "eric@naoj.org",
    description = ("Observation planning toolbox."),
    long_description = read('README.txt'),
    license = "BSD",
    keywords = "astronomy observation planning",
    url = "http://ejeschke.github.com/obsplan",
    packages = ['obsplan',
                # additional stuff
                'obsplan.plots','obsplan.tests', 'examples'
                ],
    package_data = { },
    scripts = [],
    install_requires = ['numpy', 'pytz', 'pyephem'],
    test_suite = "obsplan.tests",
    classifiers=[
          'Intended Audience :: Science/Research',
          'License :: OSI Approved :: BSD License',
          'Operating System :: MacOS :: MacOS X',
          'Operating System :: Microsoft :: Windows',
          'Operating System :: POSIX',
          'Programming Language :: C',
          'Programming Language :: Python :: 2.7',
          'Topic :: Scientific/Engineering :: Astronomy',
          'Topic :: Scientific/Engineering :: Physics',
          ],
    cmdclass={'build_py': build_py}
)

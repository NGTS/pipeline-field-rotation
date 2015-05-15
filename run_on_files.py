#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division, print_function, absolute_import
import argparse
import logging
import glob
import multiprocessing.dummy as mp
import sys
sys.path.insert(0, '.')
import compute_field_rotation as c
from astropy.io import fits
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from astropy import wcs
from astropy import coordinates as coord
from astropy import units as u
from astropy import time

logging.basicConfig(level='INFO', format='%(levelname)7s %(message)s')
logger = logging.getLogger(__name__)

try:
    import joblib
except ImportError:
    logger.warning('Cannot find joblib, caching is unavailable')
    use_joblib = False
else:
    use_joblib = True

try:
    import seaborn as sns
except ImportError:
    logger.warning('Cannot load seaborn')
else:
    sns.set()



def get_files(dirname):
    return glob.glob('{}/proc*.fits'.format(dirname))


def pixel_movement(distance, theta_degrees):
    theta_rad = np.radians(theta_degrees)
    return distance * theta_rad

def compute_alt_az(header):
    w = wcs.WCS(header)
    site = coord.EarthLocation(lat=header['SITELAT'], lon=header['SITELONG'],
            height=header['SITEALT'] * u.m)
    t = time.Time(header['mjd'], format='mjd')
    ra, dec = w.all_pix2world(1024, 1024, 1)
    c = coord.SkyCoord(ra=ra * u.degree, dec=dec * u.degree)
    altaz = c.transform_to(coord.AltAz(location=site, obstime=t))
    return (altaz.alt.value, altaz.az.value)


def extract_data(fname):
    cd = c.fetch_cd(fname)
    stats = c.compute_stats(cd)
    header = fits.getheader(fname)
    mjd = header['mjd']
    alt, az = compute_alt_az(header)
    return fname, mjd, alt, az, stats.theta.value, stats.scale.value


def get_theta_timeseries(files, output):
    output.write('fname,mjd,alt,az,theta,scale\n')
    pool = mp.Pool()
    mjd, theta = [], []
    for result in pool.imap(extract_data, files):
        mjd.append(result[1])
        theta.append(result[4])

        out_str = ','.join(map(str, result))
        output.write(out_str + '\n')

    mjd, theta = [np.asarray(d) for d in [mjd, theta]]
    return mjd, theta


def main(args):
    if args.verbose:
        logger.setLevel('DEBUG')
    logger.debug(args)

    files = get_files(args.dirname)

    if use_joblib:
        if args.cache:
            memory = joblib.Memory(cachedir='.tmp')
        else:
            memory = joblib.Memory(cachedir=None)

        fn = memory.cache(get_theta_timeseries)
    else:
        fn = get_theta_timeseries

    mjd, theta = fn(files, args.output)

    theta_range = theta.ptp()
    theta_rad = np.radians(theta_range)
    displacement_at_edge = 1024 * theta_rad
    print('Displacement at 1024 pixels: {:f} pixels'.format(displacement_at_edge))

    if args.plot_to:
        mjd0 = int(mjd.min())
        mjd -= mjd0
        fig, axis = plt.subplots()
        axis.plot(mjd, theta, '.')
        axis.set_xlabel(r'MJD - {}'.format(mjd0))
        axis.set_ylabel(r'$\theta$')
        axis.set_title(
            'Rotation: {:.4f} degrees, pixel displacement @1024px: {:.3f} pix'.format(
                theta_range, displacement_at_edge))
        fig.tight_layout()
        fig.savefig(args.plot_to)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('dirname')
    parser.add_argument('--cache',
                        action='store_true',
                        default=False,
                        help='Cache extracted information for files')
    parser.add_argument('-o', '--output',
                        required=False,
                        type=argparse.FileType('w'),
                        default='-')
    parser.add_argument('-p', '--plot-to', required=False)
    parser.add_argument('-v', '--verbose', action='store_true')
    main(parser.parse_args())

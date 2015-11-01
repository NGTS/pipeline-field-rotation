#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division, print_function, absolute_import
import argparse
import logging
import subprocess as sp
import bz2
from contextlib import contextmanager
from astropy.io import fits
import numpy as np
from collections import namedtuple
from astropy import units as u
import os
import tempfile
import shutil
import sys

logging.basicConfig(level='INFO', format='%(message)s')
logger = logging.getLogger(__name__)

stats = namedtuple('stats', ['theta', 'scale'])


@contextmanager
def temporary_directory(*args, **kwargs):
    tdir = tempfile.mkdtemp(*args, **kwargs)
    try:
        yield tdir
    finally:
        shutil.rmtree(tdir)


@contextmanager
def change_directory(path):
    current_pwd = os.getcwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(current_pwd)


@contextmanager
def change_to_tempdir():
    with temporary_directory() as tdir:
        with change_directory(tdir):
            yield


def compute_stats(cd):
    [[cd1_1, cd1_2], [cd2_1, cd2_2]] = cd
    d = np.linalg.det(cd)

    # Compute theta
    parity = 1. if d >= 0. else -1.
    A = parity * cd2_1 - cd1_2
    T = parity * cd1_1 + cd2_2
    theta = -np.arctan2(A, T)

    scale = np.sqrt(np.linalg.det(cd)) * 3600.

    return stats(np.degrees(theta) * u.degree, scale * u.arcsec)


@contextmanager
def open_fits_file(fname):
    if fname.endswith('.bz2'):
        with bz2.BZ2File(fname) as uncompressed:
            with fits.open(uncompressed) as infile:
                yield infile
    else:
        with fits.open(fname) as infile:
            yield infile


def fetch_cd(filename):
    with open_fits_file(filename) as infile:
        header = infile[0].header

    return np.asarray([[header['CD1_1'], header['CD1_2']], [header['CD2_1'],
                                                            header['CD2_2']]])


@contextmanager
def solve_frame(filename, output):
    with change_to_tempdir():
        source_filename = 'source.fits'
        solved_filename = source_filename.replace('.fits', '.new')

        if filename.endswith('.bz2'):
            logger.debug('Compressed file, uncompressing')
            with bz2.BZ2File(filename) as infile:
                with open(source_filename, 'w') as outfile:
                    outfile.write(infile.read())
        else:
            shutil.copyfile(filename, source_filename)

        cmd = list(map(str, ['solve-field', source_filename, '--scale-low', 4.9,
            '--scale-high', 5.1, '--scale-units', 'arcsecperpix',
            '--downsample', 2, '--tweak-order', 7, '--no-plots']))
        logger.debug('Command: %s', ' '.join(cmd))
        sp.check_call(cmd, stdout=sys.stderr)

        if output is not None:
            shutil.copyfile(solved_filename, output)
            yield output
        else:
            yield solved_filename


def render_stats(s, quiet):
    if quiet:
        return '{0}\n{1}'.format(
                s.theta.value, s.scale.value)
    else:
        return 'Theta: {0}\nScale: {1}'.format(
                s.theta, s.scale)


def main(args):
    if args.verbose:
        logger.setLevel('DEBUG')
    logger.debug(args)

    filename = os.path.realpath(args.filename)
    output = os.path.realpath(args.output) if args.output is not None else None
    if not args.no_solve:
        with solve_frame(filename, output=output) as solved_frame_name:
            cd = fetch_cd(solved_frame_name)
    else:
        cd = fetch_cd(filename)

    logger.debug('CD matrix: %s', cd)
    print(render_stats(compute_stats(cd), args.quiet))


if __name__ == '__main__':
    description = '''
    Compute the field rotation and scale value from a NGTS image
    '''
    epilog = '''
    The image by default is solved using astrometry.net, and the results are printed to screen. The
    `--no-solve` argument allows an already solved frame to be analysed.
    '''
    parser = argparse.ArgumentParser(description=description, epilog=epilog)
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('filename')
    parser.add_argument('--no-solve',
                        action='store_true',
                        help='Do not solve the image with astrometry.net first')
    parser.add_argument('-q', '--quiet', action='store_true')
    parser.add_argument('-o', '--output', help='Save the solved image')
    main(parser.parse_args())

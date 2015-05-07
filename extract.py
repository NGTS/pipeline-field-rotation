#!/usr/bin/env python
# coding: utf-8

from sqlalchemy import create_engine
import pandas as pd
from astropy import time
import numpy as np
import gzip


def extract(camera_id):
    engine = create_engine('mysql+pymysql://sw@localhost/swdb')

    df = pd.read_sql_query('select swdb.wcs.*, ngts_ops.raw_image_list.mjd from swdb.wcs '
            'join ngts_ops.raw_image_list using (image_id) where camera_id = %(camera_id)s',
            engine, params={'camera_id': camera_id})

    cd = np.asarray([[df.cd1_1.values, df.cd1_2.values], [df.cd2_1.values, df.cd2_2.values]])
    parity = np.zeros(cd.shape[-1])
    d = np.linalg.det(cd.T)
    parity[d < 0] = -1.
    parity[d >= 0] = 1.
    A = parity * (df.cd2_1 - df.cd1_2)
    T = parity * (df.cd1_1 + df.cd2_2)
    theta = np.degrees(-np.arctan2(A, T))
    df['theta'] = theta
    df['theta_deviations_arcmin'] = (theta % 180.)
    epoch = -0.5
    phase = (df.mjd - epoch) % 1
    df['phase'] = phase

    t = time.Time(df.mjd, format='mjd', scale='utc')
    df.index = t.datetime

    with gzip.open('fr_{camera_id}.csv.gz'.format(camera_id=camera_id), 'w') as outfile:
        df.to_csv(outfile)


def main():
    for camera_id in 802, 803, 804:
        extract(camera_id)



if __name__ == '__main__':
    main()


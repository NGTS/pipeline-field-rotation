#!/usr/bin/env python
# coding: utf-8

import numpy as np
import matplotlib.pyplot as plt
import csv
import gzip
import argparse
import datetime


def extract(filename):
    dt, theta = [], []
    with gzip.open(filename, 'rt') as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            dt_value = datetime.datetime.strptime(row[''], "%Y-%m-%d %H:%M:%S")
            theta_value = float(row['theta'])

            dt.append(dt_value)
            theta.append(theta_value)
    return [np.array(data) for data in [dt, theta]]


def main(args):

    dt, theta = extract(args.filename)

    camera_id = int(args.filename.split('_')[-1].split('.')[0])

    fig, axis = plt.subplots()
    axis.plot_date(dt, theta, ls='None', marker='.')
    axis.set_xlabel(r'Date')
    axis.set_ylabel(r"Theta")
    axis.grid(True)
    axis.set_title(camera_id)
    fig.autofmt_xdate()
    fig.tight_layout()
    plt.show()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('filename')
    main(parser.parse_args())

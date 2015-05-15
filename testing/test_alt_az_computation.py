import sys
sys.path.insert(0, '.')
from run_on_files import compute_alt_az
from astropy.io import fits
import pytest
import os

@pytest.fixture
def filename():
    return os.path.join(os.path.dirname(__file__), 'data',
    'procIMAGE80520150505100031.fits')

def test_computation(filename):
    header = fits.getheader(filename)
    alt, az = compute_alt_az(header)
    assert alt > 0. and az > 0.

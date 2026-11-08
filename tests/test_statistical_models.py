"""Test the application statistics implementation against known boundaries."""
import pytest
from sql.statistics import wilson_interval, compare_groups, sample_size

def test_chi_square_known_and_null_tables():
    assert compare_groups([[50,50],[50,50]])['p_value']==1
    assert compare_groups([[90,10],[10,90]])['p_value']<1e-20
    assert compare_groups([[1,0],[0,1]]) is None

def test_wilson_score_interval():
    low,high=wilson_interval(485,1000)
    assert low==pytest.approx(.4541408,abs=1e-6)
    assert high==pytest.approx(.5159739,abs=1e-6)
    assert wilson_interval(0,0)==(None,None)

def test_sample_size_monotonicity():
    assert sample_size(.4,.02)>sample_size(.4,.05)
    assert sample_size(.4,.05,power=.9)>sample_size(.4,.05,power=.8)

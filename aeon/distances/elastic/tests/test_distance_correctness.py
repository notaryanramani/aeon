"""Test the distance calculations are correct.

Compare the distance calculations on the 1D and 2D (d,m) format input against the
results generated with tsml, in distances.tests.TestDistances.
"""

from numpy.testing import assert_almost_equal

from aeon.datasets import load_basic_motions, load_unit_test
from aeon.distances import (
    ddtw_distance,
    dtw_distance,
    dtw_gi_distance,
    edr_distance,
    erp_distance,
    euclidean_distance,
    lcss_distance,
    msm_distance,
    squared_distance,
    twe_distance,
    wddtw_distance,
    wdtw_distance,
)

distances = [
    "dtw",
    "dtw_gi",
    "wdtw",
    "lcss",
    "msm",
    "ddtw",
    "euclidean",
    "erp",
    "ddtw",
    "wddtw",
    "twe",
]

distance_parameters = {
    "dtw": [0.0, 0.1, 1.0],  # window
    "dtw_gi": [0.0, 0.1, 1.0],  # window
    "wdtw": [0.0, 0.1, 1.0],  # parameter g
    "wddtw": [0.0, 0.1, 1.0],  # parameter g
    "erp": [0.0, 0.1, 1.0],  # window
    "lcss": [0.0, 50.0, 200.0],  # espilon
    "edr": [0.0, 50.0, 200.0],  # espilon
    "ddtw": [0.0, 0.1, 1.0],  # window
    "twe": [0.0, 0.1, 1.0],  # window
    "msm": [0.0, 0.2, 3.0],  # parameter c
}
unit_test_distances = {
    "euclidean": 619.7959,
    "squared": 384147.0,
    "dtw": [384147.0, 315012.0, 275854.0],
    "wdtw": [137927.0, 68406.15849, 2.2296],
    "erp": [2275.0, 2275.0, 2275.0],
    "lcss": [1.0, 0.45833, 0.08333],
    "edr": [1.0, 0.58333, 0.125],
    "ddtw": [80806.0, 76289.0625, 76289.0625],
    "wddtw": [38144.53125, 19121.4927, 1.34957],
    "twe": [4536.0, 3192.0220, 3030.036000000001],
    "msm_ind": [1515.0, 1517.8000000000004, 1557.0],  # msm with independent distance
    "msm_dep": [1897.0, 1898.6000000000001, 1921.0],  # msm with dependent distance
}
basic_motions_distances = {
    "euclidean": 27.51835240,
    "squared": 757.25971908652,
    "dtw": [757.259719, 330.834497, 330.834497],
    "dtw_gi": [259.5333502342899, 310.10738471013804, 310.10738471013804],
    "wdtw": [165.41724, 3.308425, 0],
    "msm": [70.014828, 89.814828, 268.014828],
    "erp": [169.3715, 102.0979, 102.097904],
    "edr": [1.0, 0.26, 0.07],
    "lcss": [1.0, 0.26, 0.05],
    "ddtw": [297.18771, 160.51311645984856, 160.29823],
    "wddtw": [80.149117, 1.458858, 0.0],
    "twe": [338.4842162018424, 173.35966887818674, 173.3596688781867],
    # msm with independent distance
    "msm_ind": [84.36021099999999, 140.13788899999997, 262.6939920000001],
    # msm with dependent distance
    "msm_dep": [33.06825, 71.1408, 190.7397],
}


def test_multivariate_correctness():
    """Test distance correctness on BasicMotions: multivariate, equal length."""
    trainX, trainy = load_basic_motions(return_type="numpy3D")
    case1 = trainX[0]
    case2 = trainX[1]
    d = euclidean_distance(case1, case2)
    assert_almost_equal(d, basic_motions_distances["euclidean"], 4)
    d = squared_distance(case1, case2)
    assert_almost_equal(d, basic_motions_distances["squared"], 4)
    for j in range(0, 3):
        d = dtw_distance(case1, case2, window=distance_parameters["dtw"][j])
        assert_almost_equal(d, basic_motions_distances["dtw"][j], 4)
        d = dtw_gi_distance(case1, case2, window=distance_parameters["dtw_gi"][j])
        assert_almost_equal(d, basic_motions_distances["dtw_gi"][j], 4)
        d = wdtw_distance(case1, case2, g=distance_parameters["wdtw"][j])
        assert_almost_equal(d, basic_motions_distances["wdtw"][j], 4)
        d = lcss_distance(case1, case2, epsilon=distance_parameters["lcss"][j] / 50.0)
        assert_almost_equal(d, basic_motions_distances["lcss"][j], 4)
        d = erp_distance(case1, case2, window=distance_parameters["erp"][j])
        assert_almost_equal(d, basic_motions_distances["erp"][j], 4)
        d = edr_distance(case1, case2, epsilon=distance_parameters["edr"][j] / 50.0)
        assert_almost_equal(d, basic_motions_distances["edr"][j], 4)
        d = ddtw_distance(case1, case2, window=distance_parameters["ddtw"][j])
        assert_almost_equal(d, basic_motions_distances["ddtw"][j], 4)
        d = wddtw_distance(case1, case2, g=distance_parameters["wddtw"][j])
        assert_almost_equal(d, basic_motions_distances["wddtw"][j], 4)
        d = twe_distance(case1, case2, window=distance_parameters["twe"][j])
        assert_almost_equal(d, basic_motions_distances["twe"][j], 4)
        d = msm_distance(case1, case2, c=distance_parameters["msm"][j])
        assert_almost_equal(d, basic_motions_distances["msm_ind"][j], 4)
        d = msm_distance(
            case1, case2, c=distance_parameters["msm"][j], independent=False
        )
        assert_almost_equal(d, basic_motions_distances["msm_dep"][j], 4)


def test_univariate_correctness():
    """Test dtw correctness on UnitTest: univariate, equal length."""
    trainX, trainy = load_unit_test(return_type="numpy3D")
    trainX2, trainy2 = load_unit_test(return_type="numpy2D")
    # Test 2D and 3D instances from UnitTest
    cases1 = [trainX[0], trainX2[0]]
    cases2 = [trainX[2], trainX2[2]]
    # Add test cases1 and 2 are the same
    d = euclidean_distance(cases1[0], cases2[0])
    d2 = euclidean_distance(cases1[1], cases2[1])
    assert_almost_equal(d, unit_test_distances["euclidean"], 4)
    assert d == d2
    d = squared_distance(cases1[0], cases2[0])
    d2 = squared_distance(cases1[1], cases2[1])
    assert_almost_equal(d, unit_test_distances["squared"], 4)
    assert d == d2
    for j in range(0, 3):
        d = dtw_distance(cases1[0], cases2[0], window=distance_parameters["dtw"][j])
        d2 = dtw_distance(cases1[1], cases2[1], window=distance_parameters["dtw"][j])
        assert_almost_equal(d, unit_test_distances["dtw"][j], 4)
        assert d == d2
        d = wdtw_distance(cases1[0], cases2[0], g=distance_parameters["wdtw"][j])
        d2 = wdtw_distance(cases1[1], cases2[1], g=distance_parameters["wdtw"][j])
        assert_almost_equal(d, unit_test_distances["wdtw"][j], 4)
        assert d == d2
        d = lcss_distance(cases1[0], cases2[0], epsilon=distance_parameters["lcss"][j])
        d2 = lcss_distance(cases1[1], cases2[1], epsilon=distance_parameters["lcss"][j])
        assert_almost_equal(d, unit_test_distances["lcss"][j], 4)
        assert d == d2
        d = erp_distance(cases1[0], cases2[0], window=distance_parameters["erp"][j])
        d2 = erp_distance(cases1[1], cases2[1], window=distance_parameters["erp"][j])
        assert_almost_equal(d, unit_test_distances["erp"][j], 4)
        assert d == d2
        d = edr_distance(cases1[0], cases2[0], epsilon=distance_parameters["edr"][j])
        d2 = edr_distance(cases1[1], cases2[1], epsilon=distance_parameters["edr"][j])
        assert_almost_equal(d, unit_test_distances["edr"][j], 4)
        assert d == d2
        d = ddtw_distance(cases1[0], cases2[0], window=distance_parameters["ddtw"][j])
        d2 = ddtw_distance(cases1[1], cases2[1], window=distance_parameters["ddtw"][j])
        assert_almost_equal(d, unit_test_distances["ddtw"][j], 4)
        assert d == d2
        d = wddtw_distance(cases1[0], cases2[0], g=distance_parameters["wddtw"][j])
        d2 = wddtw_distance(cases1[1], cases2[1], g=distance_parameters["wddtw"][j])
        assert_almost_equal(d, unit_test_distances["wddtw"][j], 4)
        assert d == d2
        d = twe_distance(cases1[0], cases2[0], window=distance_parameters["twe"][j])
        d2 = twe_distance(cases1[1], cases2[1], window=distance_parameters["twe"][j])
        assert_almost_equal(d, unit_test_distances["twe"][j], 4)
        assert d == d2
        d = msm_distance(cases1[0], cases2[0], c=distance_parameters["msm"][j])
        d2 = msm_distance(cases1[1], cases2[1], c=distance_parameters["msm"][j])
        assert_almost_equal(d, unit_test_distances["msm_ind"][j], 4)
        assert d == d2
        d = msm_distance(
            cases1[0], cases2[0], c=distance_parameters["msm"][j], independent=False
        )
        d2 = msm_distance(
            cases1[1], cases2[1], c=distance_parameters["msm"][j], independent=False
        )
        assert_almost_equal(d, unit_test_distances["msm_dep"][j], 4)
        assert d == d2

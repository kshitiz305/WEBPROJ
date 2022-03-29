import sys
import json
import pprint

import pytest

from webproj import api


def _get_and_decode_response(entry):
    """
    Retrieves response from API and decodes the JSON data into a dict
    """
    app = api.app.test_client()
    response = app.get(entry)
    decoded_response = json.loads(response.get_data().decode(sys.getdefaultencoding()))
    return decoded_response


def _assert_result(entry, expected_json_output):
    """
    Check that a given API resource return the expected result.
    """
    print(entry)
    decoded_response = _get_and_decode_response(entry)
    pprint.pprint(decoded_response)
    print("-----")
    pprint.pprint(expected_json_output)
    assert decoded_response == expected_json_output


def _assert_coordinate(entry, expected_json_output, tolerance=1e-6):
    """
    Check that a returned coordinate matches the expected result
    within a pre-determined tolerance
    """
    app = api.app.test_client()
    response = app.get(entry)
    result = json.loads(response.get_data().decode(sys.getdefaultencoding()))
    print(expected_json_output)
    print(result)
    for key in expected_json_output.keys():
        if key not in result.keys():
            raise AssertionError

    for key, value in result.items():
        expected_value = expected_json_output[key]
        if value is None and expected_value is None:
            continue
        if abs(value - expected_value) > tolerance:
            raise AssertionError


@pytest.fixture(scope="module", params=["v1.0", "v1.1"])
def api_all(request):
    return request.param


@pytest.fixture(scope="module", params=["v1.1"])
def api_from_v1_1(request):
    return request.param


def test_transformer_caching():
    """
    Check that caching works by comparing objects with the is operator
    """

    transformer_a = api.TransformerFactory.create("EPSG:4095", "EPSG:4096")
    transformer_b = api.TransformerFactory.create("EPSG:4095", "EPSG:4096")

    assert transformer_a is transformer_b


def test_crs(api_all):
    """
    Test that CRS descriptions are presented correctly
    """
    for srid, crsinfo in api.CRS_LIST.items():
        _assert_result(f"/{api_all}/crs/{srid}", crsinfo)


def test_crs_index(api_all):
    """
    Test that the index of all available CRS's is returned
    correctly.
    """
    expected = {}
    for srid, crsinfo in api.CRS_LIST.items():
        if crsinfo["country"] not in expected:
            expected[crsinfo["country"]] = []
        expected[crsinfo["country"]].append(srid)

    _assert_result(f"/{api_all}/crs/", expected)


def test_crs_that_doesnt_exist(api_all):
    """
    Test that we get the proper response when requesting an unknown CRS
    """

    errmsg = f"'unknowncrs' not available. You have requested this URI "
    errmsg += (
        f"[/{api_all}/crs/unknowncrs] but did you mean /{api_all}/crs/<string:crs>"
    )

    response = _get_and_decode_response(f"/{api_all}/crs/unknowncrs")
    assert response["message"].startswith(errmsg)


def test_trans_2d(api_all):
    """
    Test that 2D transformations behaves as expected
    """
    api_entry = f"/{api_all}/trans/EPSG:4258/EPSG:25832/56.0,12.0"
    expected = {
        "v1": 687071.4391094431,
        "v2": 6210141.326748009,
        "v3": None,
        "v4": None,
    }
    _assert_coordinate(api_entry, expected)


def test_trans_3d(api_all):
    """
    Test that 3D transformations behaves as expected
    """
    api_entry = f"/{api_all}/trans/EPSG:4258/EPSG:25832/56.0,12.0,30.0"
    expected = {
        "v1": 687071.4391094431,
        "v2": 6210141.326748009,
        "v3": 30.0,
        "v4": None,
    }
    _assert_coordinate(api_entry, expected)


def test_trans_4d(api_all):
    """
    Test that 4D transformations behaves as expected
    """
    api_entry = f"/{api_all}/trans/EPSG:4258/EPSG:25832/56.0,12.0,30.0,2010.5"
    expected = {
        "v1": 687071.4391094431,
        "v2": 6210141.326748009,
        "v3": 30.0,
        "v4": 2010.5,
    }
    _assert_coordinate(api_entry, expected)


def test_sys34(api_all):
    """
    Test that system 34 is handled correctly. In this case
    we transform from S34J to EPSG:25832 and vice versa.
    """
    api_entry_fwd = f"/{api_all}/trans/DK:S34J/EPSG:25832/295799.3977,175252.0903"
    exp_fwd = {
        "v1": 499999.99999808666,
        "v2": 6206079.587029327,
        "v3": None,
        "v4": None,
    }
    _assert_coordinate(api_entry_fwd, exp_fwd)

    api_entry_inv = f"/{api_all}/trans/EPSG:25832/DK:S34J/500000.0,6205000.0"
    exp_inv = {
        "v1": 295820.9708249467,
        "v2": 174172.32360956355,
        "v3": None,
        "v4": None,
    }
    _assert_coordinate(api_entry_inv, exp_inv)

    api_entry_js = (
        f"/{api_all}/trans/DK:S34J/DK:S34S/138040.74248674404,63621.728972878314"
    )
    exp_js = {
        "v1": 138010.86611871765,
        "v2": 63644.234364821285,
        "v3": None,
        "v4": None,
    }
    _assert_coordinate(api_entry_js, exp_js)


def test_transformation_outside_crs_area_of_use(api_all):
    """
    Test that 404 is returned when a transformation can't return sane
    values due to usage outside defined area of use.
    """
    api_entry = f"/{api_all}/trans/EPSG:4258/DK:S34S/12.0,56.0"
    expected = {
        "message": "Input coordinate outside area of use of either source or destination CRS"
    }
    _assert_result(api_entry, expected)


def test_negative_coordinate_values(api_all):
    """
    Negative coordinate values are occasionally needed, for instance
    longitudes in Greenland. Let's test that we can deal with them.
    """
    api_entry = f"/{api_all}/trans/EPSG:4326/EPSG:25832/-12.0,56.0"
    expected = {
        "v1": 6231950.538290203,
        "v2": -1920310.7126844588,
        "v3": None,
        "v4": None,
    }
    _assert_coordinate(api_entry, expected)


def test_transformation_between_global_and_regional_crs(api_all):
    """
    Transformation between WGS84 and ETRS89/GR96 should be
    possible both ways. Test the logic that determines if two
    CRS's are compatible.
    """
    # first test the case from a global CRS to a regional CRS
    api_entry = (
        f"/{api_all}/trans/EPSG:4326/EPSG:25832/55.68950140789923,12.58696909994519"
    )
    expected = {"v1": 725448.0, "v2": 6177354.999999999, "v3": None, "v4": None}
    _assert_coordinate(api_entry, expected)

    # then test the reverse case from regional to global
    api_entry = f"/{api_all}/trans/EPSG:25832/EPSG:4258/725448.0,6177355.0"
    expected = {
        "v1": 55.689501407899236,
        "v2": 12.58696909994519,
        "v3": None,
        "v4": None,
    }
    _assert_coordinate(api_entry, expected, tolerance=1e-9)

    # test some failing cases DK -> GL
    api_entry = f"/{api_all}/trans/EPSG:4258/EPSG:4909/55.0,12.0"
    expected = {"message": "CRS's are not compatible across countries"}
    _assert_result(api_entry, expected)

    api_entry = f"/{api_all}/trans/EPSG:4909/EPSG:4258/75.0,-50.0"
    expected = {"message": "CRS's are not compatible across countries"}
    _assert_result(api_entry, expected)


def test_integer_coordinates(api_all):
    """
    Test the 'number' Werkzeug converter for parsing coordinates in routes
    """
    api_entry = f"/{api_all}/trans/EPSG:4258/EPSG:25832/56,12"
    expected = {
        "v1": 687071.4391094431,
        "v2": 6210141.326748009,
        "v3": None,
        "v4": None,
    }
    _assert_coordinate(api_entry, expected)

    api_entry = f"/{api_all}/trans/EPSG:4258/EPSG:25832/56.,12."
    expected = {
        "v1": 687071.4391094431,
        "v2": 6210141.326748009,
        "v3": None,
        "v4": None,
    }
    _assert_coordinate(api_entry, expected)

    api_entry = f"/{api_all}/trans/EPSG:4258/EPSG:25832/56.0,12.0"
    expected = {
        "v1": 687071.4391094431,
        "v2": 6210141.326748009,
        "v3": None,
        "v4": None,
    }
    _assert_coordinate(api_entry, expected)

    api_entry = f"/{api_all}/trans/EPSG:4258/EPSG:25832/56,12,0"
    expected = {"v1": 687071.4391094431, "v2": 6210141.326748009, "v3": 0.0, "v4": None}
    _assert_coordinate(api_entry, expected)

    api_entry = f"/{api_all}/trans/EPSG:4258/EPSG:25832/56,12,0,2020"
    expected = {"v1": 687071.4391094431, "v2": 6210141.326748009, "v3": 0.0, "v4": 2020}
    _assert_coordinate(api_entry, expected)


def test_combined_epsg_codes(api_all):
    """
    Test that EPSG codes that consist of a combination of two
    codes (horizontal+vertical) works as expected
    """
    api_entry = f"/{api_all}/trans/EPSG:4909/EPSG:3184+8267/64.0,-51.5,0"
    expected = {
        "v1": -108394.69573,
        "v2": 7156992.58360,
        "v3": -27.91300,
        "v4": None,
    }
    _assert_coordinate(api_entry, expected, tolerance=0.01)


def test_crs_return_srid(api_from_v1_1):
    """
    Test that CRS routes return the calling srid
    """
    testdata = {
        "EPSG:25832": {
            "country": "DK",
            "title": "ETRS89 / UTM Zone 32 Nord",
            "title_short": "ETRS89/UTM32N",
            "v1": "Easting",
            "v1_short": "x",
            "v2": "Northing",
            "v2_short": "y",
            "v3": "Ellipsoidehøjde",
            "v3_short": "h",
            "v4": None,
            "v4_short": None,
            "srid": "EPSG:25832",
            "area_of_use": "Europe between 6°E and 12°E: Austria; Belgium; Denmark - onshore and offshore; Germany - onshore and offshore; Norway including - onshore and offshore; Spain - offshore.",
            "bounding_box": [6.0, 38.76, 12.0, 84.33],
        },
        "EPSG:23032+5733": {
            "country": "DK",
            "title": "ED50 / UTM Zone 32 Nord + Dansk Normal Nul",
            "title_short": "ED50/UTM32N + DNN",
            "v1": "Easting",
            "v1_short": "x",
            "v2": "Northing",
            "v2_short": "y",
            "v3": "Ellipsoidehøjde",
            "v3_short": "h",
            "v4": None,
            "v4_short": None,
            "srid": "EPSG:23032+5733",
            "area_of_use": "Denmark - onshore.",
            "bounding_box": [8.0, 54.51, 15.24, 57.8],
        },
        "DK:S34S": {
            "country": "DK",
            "title": "System 34 Sjælland",
            "title_short": "S34S",
            "v1": "Westing",
            "v1_short": "x",
            "v2": "Northing",
            "v2_short": "y",
            "v3": None,
            "v3_short": None,
            "v4": None,
            "v4_short": None,
            "srid": "DK:S34S",
            "area_of_use": "Denmark - Sealand onshore",
            "bounding_box": [11.0, 54.5, 12.8, 56.5],
        },
    }

    for srid, crsinfo in testdata.items():
        api_entry = f"/{api_from_v1_1}/crs/{srid}"
        _assert_result(api_entry, crsinfo)

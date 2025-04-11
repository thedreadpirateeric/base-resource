"""Test request method."""
from unittest import mock

import pytest

from baseresourcelib.connectors.base import ApiBase


@mock.patch("baseresourcelib.connectors.base.ApiBase._api_request")
def test_success(mockApiRequest):
    """Test a successful API call is made."""
    base = ApiBase()

    resp = base.request("GET", "/endpoint")

    mockApiRequest.assert_called_once_with(
        "GET", "/endpoint", responseAsJson=True, passOnFailure=True, data={},
        timeout=None, json=True, queryParams=None,)

    assert resp == mockApiRequest.return_value.data


@mock.patch("baseresourcelib.connectors.base.ApiBase._api_request")
def test_success_false(mockApiRequest):
    """Test an unsuccessful API is made."""
    base = ApiBase()

    mockApiRequest.return_value.success = False
    resp = base.request("GET", "/endpoint")

    mockApiRequest.assert_called_once_with(
        "GET", "/endpoint", responseAsJson=True, passOnFailure=True, data={},
        timeout=None, json=True, queryParams=None,)

    assert resp is None


@mock.patch("baseresourcelib.connectors.base.ApiBase._api_request")
def test_passonfailure_no_exc(mockApiRequest):
    """Test pass on failures returns correct data.."""
    base = ApiBase()

    mockApiRequest.return_value.exc = False
    resp = base.request("GET", "/endpoint", passOnFailure=False)

    mockApiRequest.assert_called_once_with(
        "GET", "/endpoint", responseAsJson=True, passOnFailure=False, data={},
        timeout=None, json=True, queryParams=None,)

    assert resp == mockApiRequest.return_value.data


@mock.patch("baseresourcelib.connectors.base.ApiBase._api_request")
def test_passonfailure_exc_no_exeption(mockApiRequest):
    """Test pass on failures returns correct data.."""
    base = ApiBase()

    mockApiRequest.return_value.exc = True
    resp = base.request("GET", "/endpoint", passOnFailure=False)

    mockApiRequest.assert_called_once_with(
        "GET", "/endpoint", responseAsJson=True, passOnFailure=False, data={},
        timeout=None, json=True, queryParams=None,)

    assert resp == mockApiRequest.return_value.data


@mock.patch("baseresourcelib.connectors.base.ApiBase._api_request")
def test_passonfailure_exc_exeption(mockApiRequest):
    """Test an API failure causes exception when needed."""
    base = ApiBase()

    mockApiRequest.return_value.exc = ValueError("test")

    with pytest.raises(ValueError):
        base.request("GET", "/endpoint", passOnFailure=False)

    mockApiRequest.assert_called_once_with(
        "GET", "/endpoint", responseAsJson=True, passOnFailure=False, data={},
        timeout=None, json=True, queryParams=None,)

from unittest import mock

import pytest

from baseresourcelib.bases.base import BaseResource
from baseresourcelib.errors.errors import HandlerMethodNotImplemented


def _set_methods(baseObj, methods=None):
    mockMethods = mock.PropertyMock(name="MockMethods",
                                    return_value=methods or ["get"])
    mockApi = mock.PropertyMock(name="MockApi")
    type(baseObj)._api = mockApi
    type(baseObj._api).methods = mockMethods

    return mockMethods, mockApi


def _validate_methods(mockMethods, mockApi):
    mockMethods.assert_called_once_with()
    mockApi.assert_called_with()


def test_exception():
    baseObj = BaseResource()
    mockMethods, mockApi = _set_methods(baseObj, ["post"])

    with pytest.raises(HandlerMethodNotImplemented):
        baseObj._get_from_api()

    _validate_methods(mockMethods, mockApi)


@mock.patch("baseresourcelib.bases.base.BaseResource._get_from_api_many")
@mock.patch("baseresourcelib.bases.base.BaseResource._return_mode_data")
@mock.patch("baseresourcelib.bases.base.BaseResource._dump_data")
def test_api_data_raw(mockDumpData, mockReturnModeData, mockGetFromApiMany):
    baseObj = BaseResource(_preloaded=True)

    mockMethods, mockApi = _set_methods(baseObj)
    mockSingle = mock.PropertyMock(name="MockSingle", return_value=False)
    mockData = mock.PropertyMock(name="MockData", return_value=[])
    type(baseObj._api).data = mockData
    type(baseObj)._single = mockSingle

    baseObj._get_from_api(_raw=True, refresh=False)

    _validate_methods(mockMethods, mockApi)

    mockReturnModeData.assert_called()
    mockDumpData.assert_called()


@mock.patch("baseresourcelib.bases.base.BaseResource._get_from_api_many")
@mock.patch("baseresourcelib.bases.base.BaseResource._make_data")
def test_api_data_no_raw(mockMakeData, mockGetFromApiMany):
    baseObj = BaseResource(_preloaded=True)
    mockMethods, mockApi = _set_methods(baseObj)

    mockSingle = mock.PropertyMock(name="MockSingle", return_value=False)
    mockData = mock.PropertyMock(name="MockData", return_value=[])
    type(baseObj._api).data = mockData
    type(baseObj)._single = mockSingle

    baseObj._get_from_api(_raw=False, refresh=False)

    _validate_methods(mockMethods, mockApi)

    mockMakeData.assert_called_once_with()


@mock.patch("baseresourcelib.bases.base.BaseResource._get_from_api_many")
@mock.patch("baseresourcelib.bases.base.BaseResource._make_data")
def test_no_api_data_no_raw_many(mockMakeData, mockGetFromApiMany):
    baseObj = BaseResource(_preloaded=True)

    mockMethods, mockApi = _set_methods(baseObj)

    mockSingle = mock.PropertyMock(name="MockSingle", return_value=False)
    mockData = mock.PropertyMock(name="MockData", return_value=[])
    type(baseObj._api).data = mockData
    type(baseObj)._single = mockSingle

    retVal = baseObj._get_from_api(_raw=False, refresh=False)

    _validate_methods(mockMethods, mockApi)

    mockMakeData.assert_called_once_with()
    assert 2 == mockData.call_count
    mockGetFromApiMany.assert_called_once_with(
        passOnFailure=True, responseAsJson=True, timeout=None)
    mockSingle.assert_called_once_with()

    assert retVal == mockMakeData.return_value


@mock.patch("baseresourcelib.bases.base.BaseResource._get_from_api_single")
@mock.patch("baseresourcelib.bases.base.BaseResource._make_data")
def test_no_api_data_no_raw_single(mockMakeData, mockGetFromApiSingle):
    baseObj = BaseResource(_preloaded=True)

    mockMethods, mockApi = _set_methods(baseObj)

    mockSingle = mock.PropertyMock(name="MockSingle")
    mockData = mock.PropertyMock(name="MockData", return_value=[])
    type(baseObj._api).data = mockData
    type(baseObj)._single = mockSingle

    retVal = baseObj._get_from_api(_raw=False, refresh=False)

    _validate_methods(mockMethods, mockApi)

    mockMakeData.assert_called_once_with()
    assert 2 == mockData.call_count
    mockGetFromApiSingle.assert_called_once_with(responseAsJson=True,
                                                 passOnFailure=True,
                                                 timeout=None)
    mockSingle.assert_called_once_with()

    assert retVal == mockMakeData.return_value

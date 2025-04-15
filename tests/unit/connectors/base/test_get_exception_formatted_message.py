"""Test get exception formatted message."""
from unittest import mock
import pytest
import requests

from baseresourcelib.connectors.base import ApiBase


@pytest.fixture
def response_with_json():
    data = {'message': 'Invalid tasks.'}
    r = requests.Response()
    r.status_code = 400
    r.url = "test_URL"

    def json_func():
        return data

    r.json = json_func
    return r


@pytest.fixture
def response_without_json():
    r = requests.Response()
    r.status_code = 404
    r.url = "Test_URL"

    def json_func():
        return None

    r.json = json_func
    return r


@mock.patch("baseresourcelib.connectors.base.LOGGER")
def test_get_exception_formatted_message_with_json(mockLogger,
                                                   response_with_json):
    """Test exception formatted message with json."""
    mockLogger.return_value = mock.MagicMock()
    baseObj = ApiBase()
    msg = baseObj._get_exception_formatted_message(response_with_json,
                                                   "CLIENT ERROR")

    assert "CLIENT ERROR" in msg
    assert "400" in msg
    assert "Invalid tasks." in msg


@mock.patch("baseresourcelib.connectors.base.LOGGER")
def test_get_exception_formatted_message_without_json(mockLogger,
                                                      response_without_json):
    """Test exception formatted message without json."""
    mockLogger.return_value = mock.MagicMock()
    baseObj = ApiBase()
    msg = baseObj._get_exception_formatted_message(response_without_json,
                                                   "NOT FOUND")

    assert "NOT FOUND" in msg
    assert "404" in msg

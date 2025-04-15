"""Unit tests for the API Base Resources."""
# pylint: disable=R,W0212
import os
from baseresourcelib.connectors.base import ApiBase


def test_get_token_from_env():
    """Test the token getter."""
    base = ApiBase()
    os.environ['API_TOKEN'] = "testtoken"
    token = base._get_token_from_env()
    assert token == "testtoken"


def test_get_token_from_specified_token():
    """Test the token getter."""
    base = ApiBase()
    token = base._get_token_from_env("TESTTEST")
    assert token == "TESTTEST"

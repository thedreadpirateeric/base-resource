"""Test the base Handler."""
import pytest

from baseresourcelib.bases import base


class BaseField:
    """Mock a field."""


class MockClass:
    """Use for testing the metaclass."""

    dbfield = BaseField
    sfield = BaseField
    inner = None
    skwargs = {}
    dkwargs = {}


class ModeClass:
    _access_mode = None
    _mode = base.Mode()

    def __init__(self, **kwargs):
        self._mode = kwargs.get("_mode", "api")


class TestMode:
    """Test the Mode class."""

    def test_mode_init(self):
        """Test the init of the mode class."""
        mode = ModeClass(_mode="api")
        assert mode._mode == "api"

    def test_mode_init_no_value(self):
        """Test mode without setting the inital value."""
        mode = ModeClass()
        assert mode._mode == "api"

    def test_mode_init_wrong_value(self):
        """Test mode without setting the inital value."""
        # pylint: disable=E1120
        with pytest.raises(ValueError):
            ModeClass(_mode="asdf")

    def test_make_mode(self, monkeypatch):
        """Test the set function of the property."""
        monkeypatch.setattr(base, "Document", MockClass)
        assert isinstance(base.Mode.make_modes(), tuple)
        assert len(base.Mode.make_modes()) == 4
        assert base.Mode.make_modes() == ("api", "rpc", "direct", "db")

    def test_getter(self):
        """Test the getter method."""
        mode = ModeClass(_mode="rpc")
        assert mode._mode == "rpc"

    def test_setter(self):
        """Test the setter method."""
        mode = ModeClass(_mode="direct")
        mode._mode = "api"
        # pylint: disable=W0212
        assert mode._access_mode == "api"
        assert mode._mode == "api"

    def test_setter_wrong_value(self):
        """Test the setter method."""
        mode = ModeClass(_mode="direct")
        with pytest.raises(ValueError):
            mode._mode = "asdf"
        # pylint: disable=W0212
        assert mode._access_mode == "direct"
        assert mode._mode == "direct"

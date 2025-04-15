"""Get the datatype for each field to create other objects as needed."""
# pylint: disable=R
from typing import Any
from marshmallow import fields as schemaFields
from mongoengine import fields as mongoFields


class BaseField:
    """Field types base class.

    Attributes:
        name (str): Title name.

    """

    sfield: type[Any] = schemaFields.Field
    dbfield: type[Any] = mongoFields.BaseField

    def __init__(self, *args, skeys: list | None = None,
                 dkeys: list | None = None, **kwargs: dict) -> None:
        """Field classes for various types of data.

        Args:
            name (str): Name of the object, uses the class name if not given.

        Kwargs:
            skeys (list): List of allowed keys to pass to marshmallow fields.
            dkeys (list): List of allowed keys to pass to mongoengine fields.
            required (bool): Raise a `ValidationError` if the field value is
                not supplied during deserialization.
            allow_none (bool): Set this to `True` if `None` should be
                considered a valid value during validation/deserialization. If
                `missing=None` and `allow_none` is unset, will default to
                `True`. Otherwise, the default is False.
            missing: Default deserialization value for the field if the field
                is not found in the input data. May be a value or a callable.
            default: If set, this value will be used during serialization if
                the input value is missing. If not set, the field will be
                excluded from the serialized output if the input value is
                missing. May be a value or a callable.
            attribute (str): The name of the attribute to get the value from.
                If `None`, assumes the attribute has the same name as the
                field.
            load_from (str): Additional key to look for when deserializing.
                Will only be checked if the field’s name is not found on the
                input dictionary. If checked, it will return this parameter on
                error.
            validate (callable): Validator or collection of validators that are
                called during deserialization. Validator takes a field’s input
                value as its only parameter and returns a boolean. If it
                returns `False`, an `ValidationError` is raised.
            model_default: *same as `default`*

        """
        self.name = args[0] if args else self.__class__.__name__
        skeys = skeys or ["required", "allow_none", "missing", "default",
                          "attribute", "load_from", "validate"]
        dkeys = dkeys or ["required", "model_required", "missing",
                          "model_default", "default"]
        self.skwargs = {k: kwargs.get(k) for k in skeys if k in kwargs}
        self.dkwargs = {self._remove_model_key(k): kwargs.get(k) for k in dkeys
                        if k in kwargs}
        self.inner = kwargs.get("innerField", None)

    def __get__(self, obj, objtype):
        """Use custom getter."""
        if obj is None:
            return self
        return obj._data.get(self.name)

    def __set__(self, obj, val):
        """Use custom settr."""
        obj._data[self.name] = val

    def __delete__(self, obj):
        """Use custom deltr."""
        obj._data[self.name] = None

    @staticmethod
    def _remove_model_key(key):
        if "model_" in key:
            key = key.replace("model_", "")
        return key


class Boolean(BaseField):
    """Boolean."""

    sfield = schemaFields.Boolean
    dbfield = mongoFields.BooleanField


class DateTime(BaseField):
    """DateTime."""

    sfield = schemaFields.DateTime
    dbfield = mongoFields.DateTimeField


class Dictionary(BaseField):
    """Dictionary."""

    sfield = schemaFields.Dict
    dbfield = mongoFields.DictField


class Integer(BaseField):
    """Integer."""

    sfield = schemaFields.Integer
    dbfield = mongoFields.IntField


class Float(BaseField):
    """Float."""

    sfield = schemaFields.Float
    dbfield = mongoFields.FloatField


class List(BaseField):
    """List."""

    sfield = schemaFields.List
    dbfield = mongoFields.ListField


class String(BaseField):
    """String."""

    sfield = schemaFields.String
    dbfield = mongoFields.StringField


class ObjectId(BaseField):
    """String."""

    sfield = schemaFields.String
    dbfield = mongoFields.ObjectIdField

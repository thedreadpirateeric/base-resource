"""Base class."""
# pylint: disable=C0132,C0204,C0209,C0302,E1101,R0902,R1729,R1734,R1735,W
# pylint: disable=W0106,W0212,W0613
import os
from typing import Any
from typing import List
from typing import Dict
from typing import TypeVar

from marshmallow import Schema
from marshmallow import fields as sfields
from marshmallow import ValidationError
try:
    from mongoengine import Document
except ImportError:
    Document = None
from bson import SON

from ..utils.utils import chunkify_list
from ..connectors.responseobjects import (
    ApiMapper, MongoMapper, MySQLMapper, RpcMapper, DirectMapper)
from ..errors.errors import HandlerMethodNotImplemented, ClientInputError
from ..fields.fields import BaseField


__all__ = [
    "BaseResource",
]

TASK = TypeVar("Task")
FIELD = TypeVar("BaseField")


class Mode:
    """Handles the mode of operation.

    This is a descriptor.

    """

    @staticmethod
    def make_modes():
        """All avalible modes of operation are listed in the response."""
        modes = ["api", "rpc", "direct"]
        if Document:
            modes.append("db")
        return tuple(modes)

    def __get__(self, obj: type, objtype: type) -> None:
        """Return custom value."""
        return obj._access_mode

    def __set__(self, obj: type, value) -> None:
        """Return custom value."""
        if value not in self.make_modes():
            raise ValueError("Mode must be on of {}".
                             format(", ".join(self.make_modes())))
        obj._access_mode = value


class Base(type):
    """Base class.

    Attributes:
        _fields (dict): contains the added fields on the :class:'Resource'.
        schema (:class:`Schema`): Created to assist with (de)serialization.
        db (:class:`Document`): If the mongoengine library is installed, the
            :class:'Resource' will have access to MongoDB.

    """

    # @classmethod
    # def __prepare__(cls, name: str, bases: tuple) -> OrderedDict:
    #     """Ensure order of attributes in the `__dict__`."""
    #     return OrderedDict()
    #
    def __new__(mcs, name: str, bases: tuple, dct: dict) -> type:
        """Create the class."""
        # If a base class just call super
        if name == "Base":
            return super().__new__(mcs, name, bases, dct)

        # If we want to mix in any additional classes for creation
        newBases = list()
        for base in bases:
            newBases.append(base)

        dct = {**{"_meta": dict(), "_inner": dict(), "_fields": dict()},
               **dct}
        # If this class has been marked as an abstract class, no fields will be
        # processed.
        _fields = dict()
        _inner = dict()
        # Are there defined fields from bases?
        for base in newBases:
            for k, f in getattr(base, "_fields", dict()).items():
                _fields[k] = f
        # new fields
        for key, field in {**_fields, **dct}.items():
            if isinstance(field, BaseField):
                field.name = key
                _fields[key] = field
                if field.inner:
                    _inner[key] = field.inner

        # Add a section here to check for pre_load methods for data altering
        # Create our custom schema and docuemnt classes
        if dct.get("_meta", {}).get("abstract", False) is False and _fields:
            sch = {key: mcs._schema_field(value)
                   for key, value in _fields.items()}
            dct['schema'] = mcs._make_schema_class(sch)
            dct['paginated'] = mcs._make_paginated_schema_class(dct['schema'])

        # If mongoengine is installed
        if _fields and dct.get("_meta", dict()).get("db", dict()):
            mod = {f: mcs._mongoengine_field(_fields[f]) for f in
                   list(_fields.keys())} if Document else dict()
            # Look for customer meta field for passing to the docuemnt
            mmeta = dct.get(
                "_meta", dict()).get("db", dict()).get("meta", dict())
            if mmeta:
                mod = {**mod, "meta": mmeta}
            # This is where the database model is created.
            dct['dbmodel'] = mcs._make_mongo_class(
                mod, override=dct.get("_meta", dict()).get("db", dict()).get(
                    "document", None),
                name=dct.get("_meta", dict()).get("db", dict()).get(
                    "name", None))

        if _fields:
            dct['_fields'] = _fields
        if _inner:
            dct['_inner'] = _inner
        dct['_uid'] = dct.get("_meta", dict()).get("uid", tuple())
        # Create the new class to be instantiated
        return super().__new__(mcs, name, tuple(newBases), dct)

    @staticmethod
    def _make_schema_class(attrs: dict) -> Schema:
        return type("BaseSchema", (Schema, ), attrs)

    @staticmethod
    def _make_paginated_schema_class(schema: Schema) -> Schema:
        attrs = {"items": sfields.List(
            sfields.Nested(schema), attribute="items")}
        return type("BasePaginatedSchema", (PaginateSchema, ), attrs)

    @staticmethod
    def _make_mongo_class(attrs: dict, override: Document = None,
                          name: str = None) -> Document:
        if not Document:
            return None
        BaseDocument = override or Document
        documentName = name or (override.__name__ if override
                                else "BaseDocument")
        return type(documentName, (BaseDocument, ), attrs)

    @staticmethod
    def _schema_field(field: FIELD) -> dict:
        if field.inner:
            return field.sfield(field.inner, **{**{"allow_none": True},
                                                **field.skwargs})
        return field.sfield(**{**{"allow_none": True}, **field.skwargs})

    @staticmethod
    def _mongoengine_field(field: FIELD) -> dict:
        return field.dbfield(**field.dkwargs)


class BaseResource(metaclass=Base):
    """Wrap the endpoints and RPC and provides easy methods for IO.

    The base resource class is meant to represent an idea and the places to
    get that data from, where to store it, and how to manipulate it.

    TODO: Need to create "field" classes that will represent the data type.
    - We will build the marshaller from the _fields attribute
    - We will build the ORM document from the _fields attribute
    - The fields will accept the instructions for the api endpoints, the rpc
    methods, or the direct methods for `.get`, `.save`, `.delete` methods.

    Each attribute should be of a MapperObject type.

    Current types are ApiMapper, RpcMapper.

    Each Mapper object will have a specific shim provided to handle the `get`,
    `put`, `post`, `delete` methods.

    Attributes:
        live: RpcMapper of specific target.
        cache: ApiMapper of specific target.
        rpc

    """

    _api = None
    _rpc = None
    _direct = None
    _db = None
    _access_mode = None
    _mode = Mode()
    _user = None
    _token = None
    _preloaded = False
    _data = dict()

    def __init__(self, _preloaded: bool = False, **kwargs: dict) -> None:
        """Instantiate the class.

        Some field can be specified as only application side. These fields
        would be excluded from api queries. This would also change how the
        collection sync works and exlude the none api fields from the PUT
        requests.

        Kwargs:
            _mode (str): Choose the shim to use.
            _preloaded (bool): Disable the GET request if data is added
                manually.
            # Setting to set some fields as only app side.
        """
        self._data = dict()
        self._find_user_or_token(**kwargs)
        self._set_mode(kwargs.pop("_mode", "api"))
        self._setup_meta_data(_connector=kwargs.pop("_connector", None))
        self.keyformatter = self._get_key_formatter(**kwargs)
        self._single = self._get_single_status(**kwargs)
        self._preloaded = _preloaded
        self._field_attributes(**kwargs)
        self.queryArgs = kwargs

        # Create mapper links where applicable

    def _set_mode(self, mode: str) -> None:
        self._mode = str(mode).lower()

    def _field_attributes(self, **fielddata: dict) -> None:
        for field in self._fields.keys():
            self._remove_field_attribute(field)
            self._add_kwarg_data(field, **fielddata)
        setmethod = getattr(self, f"_set_{self._mode}_data")
        setmethod(**fielddata)

    def _remove_field_attribute(self, field: str) -> None:
        setattr(self, field, None)
        self._data[f"__{field}"] = None

    def _add_kwarg_data(self, field: str, **fielddata: dict) -> None:
        if field not in fielddata:
            return
        setattr(self, field, fielddata[field])
        _preload = fielddata.pop("_preloaded", self._preloaded)
        if _preload:
            self._data[f"__{field}"] = fielddata[field]

    def _find_user_or_token(self, **kwargs: dict) -> None:
        self._user = self._get_user_from_env(**kwargs)
        self._token = self._get_token_from_env(**kwargs)

    @staticmethod
    def _get_token_from_env(**kwargs: dict) -> str:
        token = kwargs.get("_token", None)
        return token if token else os.environ.get("API_TOKEN", None)

    @staticmethod
    def _get_user_from_env(**kwargs: dict) -> dict:
        username = os.environ.get("API_USER")
        password = os.environ.get("API_PASS")
        if not username and not password:
            return kwargs.get("_user", None)
        return dict(username=username, password=password)

    def _get_key_formatter(self, **kwargs: dict) -> dict:
        return {k: kwargs.get(k, list()) for k in self._uid
                if kwargs.get(k, None) is not None}

    def _get_single_status(self, **kwargs: dict) -> bool:
        return bool(set(self._uid).issubset(self.keyformatter.keys()))

    def _setup_meta_data(self, **kwargs) -> None:
        self._attach_api_resources()
        self._attach_rpc_resources()
        self._attach_direct_resources()
        self._attach_db_resources(**kwargs)

    def _set_data_checks(self, field: str, **fielddata: dict) -> None:
        if not self._single:
            return False
        if not self._preloaded:
            return False
        if field not in fielddata:
            return False
        return True

    def _set_api_data(self, **fielddata: dict) -> None:
        for field in self._fields.keys():
            if not self._set_data_checks(field, **fielddata):
                continue
            if self._api.data is None:
                self._api.data = dict()
            self._api.data[field] = fielddata.get(field)

    def _set_rpc_data(self, **fielddata: dict) -> None:
        for field in self._fields.keys():
            if not self._set_data_checks(field, **fielddata):
                continue
            if self._rpc.data is None:
                self._rpc.data = dict()
            self._rpc.data[field] = fielddata.get(field)

    def _set_db_data(self, **fielddata: dict) -> None:
        if self._preloaded and fielddata.get("_doc", None) is not None:
            self._db.data = fielddata.get("_doc")
            return
        if self._db.db == "mongo":
            self._db.data = self.dbmodel(
                **{f: v for f, v in fielddata.items()
                   if f in self._fields})
        else:
            self._db.data = fielddata

    def _set_direct_data(self, **fielddata: dict) -> None:
        for field in self._fields.keys():
            if not self._set_data_checks(field, **fielddata):
                continue
            if self._direct.data is None:
                self._direct.data = dict()
            self._direct.data[field] = fielddata.get(field)

    def _attach_api_resources(self):
        if not self._meta.get("api", dict()):
            return
        uid = {"uid": self._meta.get("uid", ())}
        api = self._meta.get("api", dict())
        self._api = ApiMapper(**uid, **api)
        self._api.activeshim = api.get("shim")(
            user=self._user, token=self._token, **self._api.shimkwargs)

    def _attach_rpc_resources(self):
        if not self._meta.get("rpc", dict()):
            return
        uid = {"uid": self._meta.get("uid", ())}
        rpc = self._meta.get("rpc", dict())
        self._rpc = RpcMapper(**uid, **rpc)
        self._rpc.activeshim = self._meta.get("rpc", dict()).get("shim")(
            user=self._user, token=self._token, **self._rpc.shimkwargs)

    def _attach_direct_resources(self) -> None:
        if not self._meta.get("direct", dict()):
            return
        uid = {"uid": self._meta.get("uid", ())}
        direct = self._meta.get("direct", dict())
        self._direct = DirectMapper(**uid, **direct)
        self._direct.activeshim = self._meta.get("direct", dict()).get("shim")(
            **self._direct.shimkwargs)

    def _attach_db_resources(self, _connector=None) -> None:
        uid = {"uid": self._meta.get("uid", ())}
        db = self._meta.get("db", dict())
        mysql = self._meta.get("mysql", dict())
        if not db and not mysql:
            return
        if db and not mysql:
            self._db = MongoMapper(**uid, **db)
            self._db.db = "mongo"
        if mysql and not db:
            self._db = MySQLMapper(**uid, **mysql)
            self._db.db = "mysql"
            conn = _connector if _connector else mysql.get(
                "shim")(**self._db.shimkwargs)
            self._db.connector = conn

    # Main GET
    def get(self, **kwargs: dict) -> (list or dict):
        """Run main get method."""
        return getattr(self, "_get_from_{}".format(self._mode))(**kwargs)

    def get_long_query(self, queryField: str, queryFieldValue: List[str],
                       chunkSize: int = 20, **kwargs) -> List[Dict]:
        """Get long query.

        Read the data in chunks from the `queryField`. This will stop creating
        long url for query. Read the data in chunks and store in `self.data`.

        Args:
            queryField (str): Field on which the query should be execute
            queryFieldValue (list): List of value to passed for `queryField`

        Kwargs:
            chunkSize (int): Size of chunk to sliced to
        All additional kwargs are passed down to the specific get method used.

        Returns:
            list

        """
        # If mode is DB, no need to chunk the data
        if self._mode.lower() == "db":
            return self.get(**{queryField: queryFieldValue}, **kwargs)

        chunkedData = []
        chunkApiData = []
        for chunkData in chunkify_list(queryFieldValue, chunkSize=chunkSize):
            extraKwargs = {queryField: f"{','.join(chunkData)},",
                           **kwargs}
            chunkedData += self.get(**extraKwargs)
            chunkApiData += self._api.data
        self._api.data = chunkApiData
        return chunkedData

    # Main SET
    def save(self, **kwargs: dict) -> None:
        """Run main save method."""
        if self._mode == "db" and self._db.db == "mysql":
            query = self._db.template.substitute(**kwargs)
            return self._db.connector.set_query(query)
        if not self.has_changes():
            return None
        return getattr(self, "_save_to_{}".format(self._mode))(**kwargs)

    def post(self, data: dict, xtraheaders: dict = None, endpoint: str = None,
             **kwargs: dict) -> dict:
        """Make a post to an API."""
        xtraheaders = xtraheaders or dict()
        self._api.activeshim.headers = {
            **self._api.activeshim.headers, **xtraheaders}
        return self._api.activeshim.post(
            endpoint=endpoint or self._api.urlpost.format(**self.keyformatter),
            data=self._add_embeddedkey_to_data(data), **kwargs)

    def bulk_mongo_save(self, data: list, chunkSize: int = 10000) -> None:
        """Make a bulk save for mongo operations.

        Args:
            data: data to be bulk saved to mogno.

        Kwargs:
            chunkSize: what size to chunk the data into. default 10,000

        """
        data = self.make_bson_data(data)
        if data is None:
            raise TypeError("Data not formatted in SON data type for mongo")
        for docs in chunkify_list(data, chunkSize=chunkSize):
            self.dbmodel._collection.insert_many(docs)

    def query(self, query: str, many: bool = True) -> Any:
        """Run a SQL query."""
        return self._db.connector.query(query, many=many)

    # Main DELETE
    def delete(self, **kwargs: dict) -> None:
        """Run main delete method."""
        return getattr(self, "_delete_from_{}".format(self._mode))(**kwargs)

    # Helper TASK (RPC / Automation)
    def run_task(self, task: Any, *args: tuple, **kwargs: dict) -> Any:
        """Initiate a long running (rpc or automation) task.

        Initiate a remote proceedure call (against an infrastucture device) or
        start an automation task (to build a report or perform a multi-step
        process).

        Args:
            task (string): RPC / Automation Task Name.

        KwArgs:
            endppoint (string, optional, "/tasks"): Path to use to make the
                request.
            waitForResponse (boolean, optional, True): If True, checks back
                on the RPC task periodically until the task ends or the check
                limit is reached.
            deviceNumber (integer, optional, None): Device number to run an
                RPC task against.
            username (string, optional, None): Name of user to override as
                api requestor (when using INTERNAL_TOKEN).
            commcellName (string, optional, None): Commcell name of the
                commserver to run an RPC task against.

        Returns:
            dict: Dictionary containing details of the triggered RPC task.

        """
        endpoint = kwargs.pop("endpoint", "/tasks")
        waitForResponse = kwargs.pop("waitForResponse", True)
        deviceNumber = kwargs.pop("deviceNumber", None)
        username = kwargs.pop("username", None)
        payload = dict(
            deviceNumber=deviceNumber,
            args=list(args),
            kwargs=dict(**kwargs)
        )
        if username:
            payload.update({"username": username})
        mode = getattr(self, f"_{self._mode}")
        if mode.activeshim.apiName == "StorageCenterAPI":
            payload['name'] = task
        else:
            payload['task'] = task
        return mode.activeshim.poll_task(
            endpoint=endpoint, data=payload, waitForResponse=waitForResponse)

    # GET

    def _render_output_data(self, output, _raw: bool = False):
        if (isinstance(output, list) and
            all([isinstance(d, (dict, BaseResource)) for d in output])) or \
                isinstance(output, (dict, BaseResource)):
            if _raw:
                output = self._return_mode_data()
                output = self._dump_data(output)
            else:
                output = self._make_data()
        return output

    # API

    def _get_from_api(self,
                      refresh: bool = True,
                      _raw: bool = False,
                      responseAsJson: bool = True,
                      passOnFailure: bool = True,
                      timeout: Any = None,
                      **query: dict) -> Any:
        """
        Get data from api.

        Get the data from the backend api. This will make connection and return
        the data get from the API.

        Kwargs:
            refresh (bool, optional, True): Refresh the data in cache from API
                results. Default=True
            _raw (bool, optional, False): Get raw data instaad of objects.
                Default=False
            query (dict, optional): Filter the data based on query.

        Returns:
            Any: List of Objects or dict if the multiple data requested or
                single Object or dict.

        Raises:
            HandlerMethodNotImplemented: When there is no "get" method
                implemented by connector class.
        """
        reqKwargs = dict(responseAsJson=responseAsJson,
                         passOnFailure=passOnFailure,
                         timeout=timeout)
        if "get" not in self._api.methods:
            raise HandlerMethodNotImplemented(
                "Unable to get from {}".format(self._api.activeshim.apiName))
        if not self._api.data or refresh is True or self._preloaded is False:
            self._get_from_api_single(
                **reqKwargs,
                **query) if self._single else self._get_from_api_many(
                    **reqKwargs, **query)
        return self._render_output_data(self._api.data, _raw=_raw)

    def _get_from_api_single(self,
                             responseAsJson: bool = True,
                             passOnFailure: bool = True,
                             timeout: Any = None,
                             **query) -> dict:
        getkey = "single" if getattr(self._api, "urlsingle", None) else "put"
        url = getattr(self._api, "url{}".format(getkey)).format(
            **self.keyformatter)
        data = self._api.activeshim.get(endpoint=url,
                                        responseAsJson=responseAsJson,
                                        passOnFailure=passOnFailure,
                                        timeout=timeout)
        self._api.data = self._strip_embeddedkey_from_data(data)
        if self._api.data is not None:
            marshalledData = self.schema().load(self._api.data).data
            for field in self._fields.keys():
                self._add_kwarg_data(field, _preloaded=True, **marshalledData)

    def _get_from_api_many(self,  # pylint: disable=too-many-locals
                           responseAsJson=True,
                           passOnFailure=True,
                           timeout=None,
                           **query) -> list:
        paginated = query.pop("_paginated", True)
        url = self._api.urlget.format(**self.keyformatter)
        assignedQuery, errors = self.schema().dump({
            f: getattr(self, f) for f in self._fields.keys()
            if getattr(self, f, None) is not None})
        if errors:
            if not self._api.errors:
                self._api.errors = errors
            else:
                self._api.errors.extend(errors)
        urlSet = set(assignedQuery.keys())
        querySet = set(query.keys())
        for key in urlSet.intersection(querySet):
            del assignedQuery[key]
        qq = {**assignedQuery, **query}
        queryList = ["{}={}".format(k, v) for k, v in qq.items()]
        queryParams = "" if not qq else "?{}".format("&".join(queryList))
        data = self._api.activeshim.get(
            endpoint=url, paginated=paginated, queryParams=queryParams,
            threads=8, responseAsJson=responseAsJson,
            passOnFailure=passOnFailure, timeout=timeout)
        self._api.data = self._strip_embeddedkey_from_data(data)

    # RPC (api)

    def _get_from_rpc(self, **query: dict) -> Any:
        # pylint: disable=R0912
        payload = {"endpoint": self._rpc.rpcurl, **query}
        rpcargs = []
        if "deviceNumber" in self._fields:
            if not self.deviceNumber:
                raise ValueError("Cannot get from RPC, deviceNumber must "
                                 "be set")
            payload['deviceNumber'] = self.deviceNumber
        if "commcellName" in self._fields:
            if not self.commcellName:
                raise ValueError("Cannot get from RPC, commcellName must "
                                 "be set")
            payload['commcellName'] = self.commcellName
        if self._single:
            if getattr(self._rpc, "getid"):
                rpcargs.append(getattr(self, self._rpc.getid))
            self._get_from_rpc_single(*tuple(rpcargs), **payload)
        else:
            self._get_from_rpc_many(*tuple(rpcargs), **payload)
        if self._rpc.task.get("success", False) is True:
            raw = self._rpc.task.get("results", {}).get("response", None)
            add = False
            if "deviceNumber" in self._fields:
                field = "deviceNumber"
                add = True
            if "commcellName" in self._fields:
                field = "commcellName"
                add = True
            if add:
                if isinstance(raw, dict):
                    raw[field] = getattr(self, field)
                elif isinstance(raw, list):
                    raw = [{field: getattr(self, field), **d} for d in raw]
            self._rpc.data = raw
            if self._single:
                if raw:
                    for field in self._fields.keys():
                        self._add_kwarg_data(
                            field, _preloaded=True,
                            **self._load_or_dump_and_load(self._rpc.data))
        else:
            self._rpc.errors = self._rpc.task.get("results",
                                                  {}).get("response", None)
        return self._render_output_data(self._rpc.data)

    def _get_from_rpc_single(self, *args, **kwargs: dict):
        if getattr(self._rpc, "getone"):
            if not args:
                raise ValueError("*args must be set")
            method = getattr(self._rpc, "getone")
        else:
            method = getattr(self._rpc, "getall")
        self._rpc.task = self.run_task(method, *args, **kwargs)

    def _get_from_rpc_many(self, *args, **kwargs: dict):
        self._rpc.task = self.run_task(self._rpc.getall, *args, **kwargs)

    # DIRECT

    def _get_from_direct(self, refresh: bool = True, **query: dict) -> object:
        if (not self._direct.data or refresh is True or
                self._preloaded is False):
            self._get_from_direct_single(
                **query) if self._single else self._get_from_direct_many(
                    **query)
        return self._render_output_data(self._direct.data)

    def _get_from_direct_single(self, **query):
        raise HandlerMethodNotImplemented

    def _get_from_direct_many(self, **query):
        raise HandlerMethodNotImplemented

    # DATABASE

    def _pick_mongo_mysql_query(self, **query: dict) -> Any:
        if self._db.db == "mongo":
            qfields = self.keyformatter if self._single else self._fields
            assignedQuery, errors = self.schema().dump({
                f: getattr(self, f) for f in qfields.keys()
                if getattr(self, f, None) is not None})
            if errors:
                if not self._db.errors:
                    self._db.errors = errors
                else:
                    self._db.errors.extend(errors)
            baseQuerySet = set(assignedQuery.keys())
            filterQuerySet = set(query.keys())
            for key in baseQuerySet.intersection(filterQuerySet):
                del assignedQuery[key]
            return {**assignedQuery, **query}
        if not self._db.template:
            return query
        return {"query": self._db.template.substitute(**query)}

    @staticmethod
    def _generate_object(data):
        return type("doc", (), data)

    def _query_mongo_mysql_many(self, **query: Any) -> Any:
        if self._db.db == "mongo":
            return self.dbmodel.objects(**query)
        return [self._generate_object(d) for d in
                self._db.connector.query(query['query'], many=True)]

    def _query_mongo_mysql_single(self, **query: Any) -> Any:
        if self._db.db == "mongo":
            return self.dbmodel.objects(**query).first()
        return self._generate_object(
            self._db.connector.query(query['query'], many=False))

    def _get_from_db(self, refresh: bool = True, **query: dict) -> Any:
        qq = self._pick_mongo_mysql_query(**query)
        if not self._db.data or refresh is True or self._preloaded is False:
            self._get_from_db_single(
                **qq) if self._single else self._get_from_db_many(**qq)
        return self._make_data()

    def _get_from_db_many(self, **query) -> list:
        docs = self._query_mongo_mysql_many(**query)
        self._db.index = {str(d.id): d for d in docs}
        self._db.data, self._db.errors = self.schema().dump(
            self._db.index.values(), many=True)

    def _get_from_db_single(self, **query) -> Document:
        doc = self._query_mongo_mysql_single(**query)
        if doc:
            self._db.index = {str(doc.id): doc}
            self._db.data = doc
        if doc is not None:
            for field in self._fields.keys():
                self._add_kwarg_data(
                    field, _preloaded=True,
                    **self._load_or_dump_and_load(self._db.data))

    # SET

    # API

    def _save_to_api(self, **kwargs: dict) -> None:
        self._save_api_single(
            **kwargs) if self._single else self._save_api_many(**kwargs)
        return self._make_data()

    def _save_api_single(self, data: dict = None,
                         passOnFailure: bool = True,
                         timeout: Any = None,
                         **kwargs: dict) -> object:
        """Save single object to API.

        First the validation is ran using marshmallow and any requirements
        given to the fields. Raises `ClientInputError` if any validations fail.

        If `_savemethod` is given that will be used in the API call, otherwise
        a GET call is made to the API endpoint and if data is returned a PUT
        will be used and if no data is found (404) a POST will be used.

        If a paticular method was not specified in the Resource, a
        `HandlerMethodNotImplemented` will be raised.

        After the save method is ran, a GET will run.

        Kwargs:
            data: Override data to save. If `data` is `None`, the data in
                the object will be used.
            passOnFailure (bool): Pass the failure forward or not.
            timeout (int or tuple): Timeout for the request.
            _savemethod: `post` or `put`. If not specified, the method will
                choose based on data recieved from api endpoint.

        Returns:
            object

        Raises:
            ClientInputError: If the data to be saved has any validation
                errors along with the message.
            HandlerMethodNotImplemented: If the Resource does not specify the
                required put or post url.

        """
        if data is None:
            data = {k: getattr(self, k) for k in self._fields.keys()}
        validate = self._validate_save(data)
        if validate:
            raise ClientInputError(validate)
        getkey = "single" if getattr(self._api, "urlsingle", None) else "put"
        geturl = getattr(self._api, "url{}".format(getkey)).format(
            **self.keyformatter)
        savemethod = kwargs.pop("_savemethod", None)
        if not savemethod:
            # No need to pass `passOnFailure`, this is just to check which
            # method to use for the api call.
            savemethod = "put" if self._api.activeshim.get(
                endpoint=geturl, timeout=timeout) else "post"
        if savemethod not in self._api.methods:
            raise HandlerMethodNotImplemented(
                "Unable to {} to {}".format(
                    savemethod, self._api.activeshim.apiName))
        saveurl = getattr(self._api, "url{}".format(savemethod), None)
        getattr(self._api.activeshim, savemethod)(
            endpoint=saveurl.format(**self.keyformatter),
            data=self._add_embeddedkey_to_data(self._dump_data(data)),
            passOnFailure=passOnFailure,
            timeout=timeout)
        self.get(passOnFailure=passOnFailure,
                 timeout=timeout)

    def _save_api_many(self, **kwargs):
        if self._single:
            raise TypeError("Save list used on single object")
        raise HandlerMethodNotImplemented

    # RPC (api)

    def _save_to_rpc(self, **kwargs: dict) -> None:
        raise HandlerMethodNotImplemented

    # DIRECT

    def _save_to_direct(self, **kwargs: dict) -> None:
        raise HandlerMethodNotImplemented

    # DATABASE

    def _save_to_db(self, **kwargs: dict) -> None:
        self._save_db_single(
            **kwargs) if self._single else self._save_db_many(**kwargs)
        return self._make_data()

    def _save_db_single(self, data: dict = None, **kwargs: dict) -> None:
        if data is None:
            data = {k: getattr(self, k) for k in self._fields.keys()}
        self.get()
        if not self._db.data:
            self._db.data = self.dbmodel(**data)
        for key, value in data.items():
            setattr(self._db.data, key, value)
        self._db.data.save()
        self.get()

    def _save_db_many(self, **kwargs: dict) -> None:
        if self._single:
            raise TypeError("Save list used on single object")
        raise HandlerMethodNotImplemented

    # DELETE
    def _delete_from_api(self, **kwargs: dict) -> None:
        if "delete" not in self._api.methods:
            raise HandlerMethodNotImplemented(
                "Unable to delete from {}".format(
                    self._api.activeshim.apiName))
        getkey = "single" if getattr(self._api, "urlsingle", None) else "put"
        geturl = getattr(self._api, "url{}".format(getkey)).format(
            **self.keyformatter)
        if not self._api.activeshim.get(endpoint=geturl):
            return None
        self._api.activeshim.delete(endpoint=self._api.urldelete.format(
            **self.keyformatter))
        return None

    def _delete_from_rpc(self, **kwargs: dict) -> None:
        raise HandlerMethodNotImplemented

    def _delete_from_direct(self, **kwargs: dict) -> None:
        raise HandlerMethodNotImplemented

    def _delete_from_db(self, **kwargs: dict) -> None:
        if not self._single:
            raise TypeError("Unable to delete a list of objects")
        self._db.data.delete()
        for field in list(self._fields.keys()):
            setattr(self, field, None)

    # Tests for saving data
    def has_changes(self):
        """Return `True` if the values have changes from the last refresh."""
        return bool(any([self.field_has_change(f)
                         for f in self._fields.keys()]))

    def field_has_change(self, f):
        """Return `True` if the values have changes from the last refresh."""
        return bool(getattr(self, f) != self._data.get(f"__{f}"))

    # Display data

    def objects(self) -> list:
        """Return a list of objects from the .data of the current mode."""
        if self._single is True:
            return None
        return self._make_data() or list()

    def _make_data(self):
        if self._return_mode_data() is None:
            return None
        return self._make_object(
            self._return_mode_data()) if self._single else self._make_objects()

    def _load_or_dump_and_load(self, data: Any) -> Any:
        if (isinstance(data, list) and
            all([isinstance(d, (BaseResource, Document)) for d in data])) \
                or isinstance(data, (BaseResource, Document)):
            data = self._dump_data(data)
        return self.schema().load(
            data, many=isinstance(data, list)).data

    def _validate_save(self, data: Any) -> Any:
        data = self._dump_data(data)
        return self.schema().load(
            data, many=isinstance(data, list)).errors

    def _dump_data(self, data: Any) -> Any:
        return self.schema().dump(data, many=isinstance(data, list)).data

    def _get_embeddedkey(self):
        return self._meta.get("api", dict()).get("embeddedkey")

    def _add_embeddedkey_to_data(self, data):
        embeddedkey = self._get_embeddedkey()
        if embeddedkey and isinstance(data, dict):
            return {embeddedkey: data}
        if embeddedkey and isinstance(data, list):
            return [{embeddedkey: d} for d in data]
        return data

    def _strip_embeddedkey_from_data(self, data):
        embeddedkey = self._get_embeddedkey()
        if embeddedkey and isinstance(data, dict):
            return data.get(embeddedkey) or {}
        if embeddedkey and isinstance(data, list):
            return [d.get(embeddedkey) or {} for d in data]
        return data

    def _return_mode_data(self):
        mode = getattr(self, "_{}".format(self._mode))
        data = getattr(mode, "data", None)
        return None if data is None else self._load_or_dump_and_load(data)

    def _make_fields(self):
        flds = {f: t.__class__() for f, t in self._fields.items()}
        cmpx = {f: self._fields[f].__class__(innerField=t) for f, t in
                self._inner.items()}
        return {**{"_meta": self._meta}, **flds, **cmpx}

    def _make_object(self, data):
        """Create the new objects retaining many of the current settings."""
        dd = {"_mode": self._mode, "_preloaded": True}
        if self._mode in ["api", "rpc"]:
            dd["_token"] = getattr(self, "_{}".format(
                self._mode)).activeshim.token
        if self._mode == "db" and self._db.db == "mysql":
            dd['_connector'] = self._db.connector
        return type(self.__class__.__name__, (self.__class__, ),
                    self._make_fields())(**{**dd, **data})

    def _make_objects(self):
        return [self._make_object(d) for d in self._return_mode_data()]

    def serialize_data(self):
        """Return the marshaled data or the empty type."""
        empty = dict() if self._single else list()
        data = self._return_mode_data()
        if data is None:
            return empty
        return self.schema().dump(data, many=isinstance(data, list)).data

    def deserialize_data(self):
        """Return the marshaled data or the empty type."""
        empty = dict() if self._single else list()
        data = self._return_mode_data()
        if data is None:
            return empty
        return data

    @staticmethod
    def make_bson_data(data: Any) -> SON:
        """Convert standard dictionary to a bson object.

        If the data is neither a list or dict, None is returned.

        """
        if isinstance(data, list):
            return [SON(**d) for d in data]
        if isinstance(data, dict):
            return SON(**data)
        return None

    def __call__(self):
        """Return the marshaled data or the empty type."""
        return self.serialize_data()


def validate_per_page(n):
    """Raise Exception if per_page excedes per page of 2000."""
    if n > 2000:
        raise ValidationError("per_page must not exceed 2000")
    if n < 1:
        raise ValidationError("per_page must be greater than 0")


def validate_page(n):
    """Raise Exception if page is less than 1."""
    if n < 1:
        raise ValidationError("page must be greater than 0")


class PaginateSchema(Schema):
    """Return a paginated schema. Used by the factory."""

    totalItems = sfields.Int(attribute="total")
    totalPages = sfields.Int(attribute="pages")
    currentPage = sfields.Int(attribute="page")
    hasNext = sfields.Bool(attribute="has_next")
    hasPrevious = sfields.Bool(attribute="has_prev")
    page = sfields.Int(missing=1, validate=validate_page)
    per_page = sfields.Int(missing=100, validate=validate_per_page)


def PaginateSchemaFactory(baseSchema, name="PaginatedSchema",
                          includeFields=None, excludeFields=None):
    """Return created Paginated classes."""
    includeFields = includeFields or None
    excludeFields = excludeFields or list()
    value = sfields.List(
        sfields.Nested(baseSchema, only=includeFields, exclude=excludeFields),
        attribute="items", exclude=("_cls", ))
    return type(name, (PaginateSchema,), {"items": value})

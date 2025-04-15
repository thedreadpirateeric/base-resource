"""ResourceMapper and their functions."""
# pylint: disable=C0132,R
from typing import Any
from typing import Type
from typing import List
from typing import Dict
from typing import Callable


class MockAPIBase:
    """Mock for type hinting."""

    apiName: str
    get: Callable


class MapperObject:
    """Holds the data for the resource and contains instructions for the shims.

    Attributes:
        data: contains the data from the shim.
        errors: Contains any errors on index of data.
        uid: Unique keys that make up the primary (composit) key.
        index: Contains the data indexed by primary (composit) key.

    """

    shim: Dict[str, Any] | type[Any] | None = None
    data: Dict[str, Any] | List[Any] | None = None
    errors: List[Any] | None = None
    uid: List[str] = []
    activeshim: MockAPIBase
    index = None

    def __init__(self, _uid: List[str] | None = None,
                 shim: Dict[str, Any] | type[Any] | None = None) -> None:
        """Instantiate the class."""
        self.shim = shim
        self.uid = _uid or []
        self.data = None
        self.errors = None

    class ResourceIndex:
        """Index of data."""

        def __init__(self, **kwargs):
            """Instantiate the class."""
            self.data = kwargs.get("data", None)
            self.errors = kwargs.get("errors", None)

    def index_data(self) -> None:
        """Create an index of the dataset in `.data` based on the 'uid'."""
        indexData: Dict[str, Any] | List[Any] | None = None
        indexErrors: List[str] = []
        if not self.data:
            indexErrors.append("No data to index")
        elif isinstance(self.data, list):
            indexData = self._index_list(self.uid, self.data)
        elif isinstance(self.data, dict):
            indexData = self._index_dict(self.uid, self.data)
        else:
            indexErrors.append(f"Unable to index data type for "
                               f"{type(self.data)}")
        if not indexData:
            indexData = {}
        self.index = self.ResourceIndex(
            **{"data": indexData, "errors": indexErrors})

    def _make_index_key(self, uid: list, data: dict) -> str:
        """Create the key for the index from the given dictionary.

        Args:
            uid (list): Primary keys to build index from.
            data (list): Data to find primary keys.

        Returns:
            str

        """
        return ":::".join([str(data[k]) for k in uid])

    def _index_dict(self, uid: list, data: dict) -> dict:
        indexKey = self._make_index_key(uid, data)
        return {indexKey: data}

    def _index_list(self, uid: list, data: list) -> dict:
        """Create an index based on the uid list from the data.

        Incoming data is a list of dictionaires.

        A dictionary will be created with the values of the uid list as the key
        and the individual item from the list as the value.

        Args:
            uid (list): Primary keys to build index from.
            data (list): Data to index.

        Returns:
            dict

        """
        indexData = {}
        for item in data:
            indexData.update(self._index_dict(uid, item))
        return indexData

    def __call__(self):
        """Retuns the marsalled output from `.data`."""
        if not self.data:
            return None
        return self.data


class ApiMapper(MapperObject):
    """Wapper for API endpoints.

    Attributes:
        urlget (str): URL for get requests.
        urlput (str): URL for put requests.
        urlpost (str): URL for post requests.
        urldelete (str): URL for delete requests.
        schema (:class:`marshmallow.Schema`):

    """

    urlget: str
    urlput: str
    urlpost: str
    urldelete: str
    urlsingle: str
    methods: List[str] = []
    shimkwargs: Dict[str, Any] = {}

    def __init__(self, **kwargs):
        """Instantiate the class."""
        super().__init__(
            _uid=kwargs.get("uid", []), shim=kwargs.get("shim", None))
        self.urlget = kwargs.get("urlget")
        self.urlput = kwargs.get("urlput")
        self.urlpost = kwargs.get("urlpost")
        self.urldelete = kwargs.get("urldelete")
        self.urlsingle = kwargs.get("urlsingle")
        self.shimkwargs = kwargs.get("shimkwargs", {})
        self.methods = self._make_methods()

    def _make_methods(self):
        return [m for m in ("get", "put", "post", "delete")
                if getattr(self, f"url{m}", None)]


class MongoMapper(MapperObject):
    """Mapper for database objects.

    Attributes:
        data (list or dict): contains the data from the shim.
        errors (list): Contains any errors on index of data.

    """

    document = None
    name: str | None = None
    meta: Dict[str, Any] = {}
    index: Dict[str, Any]  # type: ignore
    template = None
    db = "mongo"

    def __init__(self, document: Type | None = None,
                 meta: Dict[str, Any] | None = None,
                 name: str | None = None, **kwargs) -> None:
        """Instantiate the class."""
        self.document = document
        self.meta = meta or {}
        self.name = name
        super().__init__(_uid=kwargs.pop("uid", []), **kwargs)


class MySQLMapper(MapperObject):
    """Mapper for database objects."""

    connector = None
    data = None
    errors = None
    shimkwargs: Dict[str, Any] = {}
    template = None
    substitute = None
    db = "mysql"

    def __init__(self, uid: List[Any] | None = None, **kwargs: dict) -> None:
        """Create the response object.

        Args:
            shim: Mysql shim.
            connect: URI and auth data.

        """
        super().__init__(
            _uid=uid or [], shim=kwargs.get("shim", None))
        self.data = None
        self.errors = None
        self.template = kwargs.get("template", None)
        self.substitute = kwargs.get("substitute", None)
        self.shimkwargs = kwargs.get("shimkwargs", {})


class RpcMapper(MapperObject):
    """Mapper for RPC commands."""

    getall = None
    getone = None
    rpcurl = None
    shimkwargs: Dict[str, Any] = {}
    task = None
    getid = None

    def __init__(self, uid: List[Any] | None = None, **kwargs: dict):
        """Create RPC mapper."""
        self.getall = kwargs.get("getall")
        self.getone = kwargs.get("getone")
        self.rpcurl = kwargs.get("rpcurl")
        self.shimkwargs = kwargs.get("shimkwargs", {})
        self.getid = kwargs.get("getid")
        super().__init__(
            _uid=uid or [], shim=kwargs.get("shim", None))


class DirectMapper(MapperObject):
    """Mapper for direct access."""

    method = None
    module = None
    shimkwargs: Dict[str, Any] = {}

    def __init__(self, uid: List[Any] | None = None, **kwargs: dict):
        """Create RPC mapper."""
        self.method = kwargs.get("method")
        self.module = kwargs.get("module")
        self.command = kwargs.get("command")
        self.shimkwargs = kwargs.get("shimkwargs", {})
        super().__init__(
            _uid=uid or [], shim=kwargs.get("shim", None))


class ApiResponse:
    """Standard API response object."""

    data = None
    code = None
    exc: Any = None
    success = False
    passOnFailure = True

    def __init__(self, data: Any = None, code: int | None = None,
                 success: bool = False, exc: str | None = None,
                 passOnFailure: bool = True) -> None:
        """Create the response object."""
        self.data = data
        self.code = code
        self.exc = exc
        self.success = success
        self.passOnFailure = passOnFailure

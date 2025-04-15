"""Base for API Resources."""
# pylint: disable=R,C0209

import copy
import logging
import os
import time
from typing import Any

import requests
from requests.models import Response
from urllib3.util.retry import Retry
from urllib3 import disable_warnings
from urllib3.exceptions import InsecureRequestWarning

from .responseobjects import ApiResponse
from ..utils.decorators import validate_timeout
from ..errors.errors import ApiRequestError
from ..errors.errors import ClientError4xx
from ..errors.errors import InvalidRequest400
from ..errors.errors import NothingFound404
from ..errors.errors import DuplicateRecord409
from ..errors.errors import QOperationFailed502
from ..errors.errors import ServerError5xx
from ..errors.errors import TokenExpiredError
from ..errors.errors import UnknownError
from ..errors.errors import UpstreamDependencyGone
disable_warnings(InsecureRequestWarning)
LOGGER = logging.getLogger(__name__)


class MockIP:
    """Identity Provider."""

    def new_token(self, password: str) -> str:
        """This would create a new token."""
        return password


class ApiBase:
    """Used for ALL REST API connections."""

    tokenHeader = None
    internalTokenHeader = None
    supportInternalToken = None

    def __init__(self, user: dict[Any, Any] | None = None,
                 token: str | None = None,
                 internalToken: str | None = None,
                 **kwargs: dict) -> None:
        """Instantiate the class."""
        self.apiName = self.__class__.__name__
        self.user = self._get_user_from_env(user=user)
        self.token = self._get_token_from_env(token=token)
        self.internalToken = self._get_internal_token_from_env(
            internalToken=internalToken)
        if self.user is None and self.token is None:
            raise AttributeError("Either `user` or `token` must be set")
        self.baseURL = kwargs.get("baseURL", "http://localhost")
        self.verifySSL = True
        self.headers: dict[Any, Any] = {}
        self.tokenRetryCount = 0
        self.tokenMaxRetries = 2
        self.throttleBackoffFactor = 0.2
        self.throttleMaxRetries = 5
        self.throttleCodes = (429, 502, 503, 504)
        self.responseCodesSuccess = [200, 201, 202, 204, 301]
        self.responseCodesGone = [502, 503, 504]
        self.perPage = 250
        self.iP = MockIP()
        self._attach_identity_provider(**kwargs)

    @staticmethod
    def _get_token_from_env(token: str | None = None) -> str | None:
        return token if token else os.getenv("API_TOKEN")

    @staticmethod
    def _get_internal_token_from_env(
            internalToken: str | None = None) -> str | None:
        return internalToken if internalToken else os.getenv("INTERNAL_TOKEN")

    @staticmethod
    def _get_user_from_env(user: dict | None = None) -> dict | None:
        uu = user or {}
        username = uu.get("username", None) or os.environ.get("API_USER")
        password = uu.get("password", None) or os.environ.get("API_PASS")
        if not username and not password:
            return None
        return dict(username=username, password=password)

    @staticmethod
    def _attach_identity_provider(**kwargs: dict) -> None:
        """If the api requires any auth, override this method."""
        # pylint: disable=W0613

    @staticmethod
    def _make_headers(serializeType: str) -> dict:
        supportedTypes = {"json", }
        if serializeType not in supportedTypes:
            raise AttributeError("Must be one of [{}]".format(supportedTypes))
        if serializeType.lower() == "json":
            return {"Content-Type": "application/json",
                    "Accept": "application/json"}
        return {}

    def _handle_invalid_token(self) -> None:
        if self.internalToken and self.internalTokenHeader:
            raise TokenExpiredError("Internal Token is expired.")
        if self.user is None:
            raise TokenExpiredError("Unable to obtain a new token, user"
                                    " credentials not specified.")
        if self.tokenRetryCount >= self.tokenMaxRetries:
            msg = ("{} token has expired. Unable to obtain a valid token "
                   "after {} attempts.".
                   format(self.apiName, self.tokenMaxRetries))
            attn = "\nATTN: SBDEVs have been automatically notified!"
            LOGGER.error(msg)
            raise TokenExpiredError(msg + attn)
        self.tokenRetryCount += 1
        LOGGER.warning("%s token has expired. Requesting new token (retry=%s)",
                       self.apiName, self.tokenRetryCount)
        self.token = self.iP.new_token(
            password=self.user['password'])

    def _get_exception_formatted_message(self, response: Response,
                                         errBaseMsg: str):
        msg = (f"{errBaseMsg}({self.apiName}): {response.status_code}\n"
               f"{response.url}\n{response.text}")

        if response.json():
            msg = (f"{errBaseMsg}({self.apiName}): {response.status_code}\n"
                   f"{response.url}\n{response.json().get('message', '')}")
        LOGGER.debug(msg)

        return msg

    def _check_response(self, response: Response, responseAsJson: bool = True,
                        passOnFailure: bool = True) -> ApiResponse:
        resp = ApiResponse(
            code=response.status_code, passOnFailure=passOnFailure)
        if response.status_code in self.responseCodesSuccess:
            LOGGER.debug("%s [%s] <= valid response received.",
                         self.apiName, response.status_code)
            if response.status_code == 204:
                resp.data = None
            resp.success = True
            resp.data = response
            if responseAsJson and response.status_code != 204:
                resp.data = response.json()
        elif response.status_code in self.responseCodesGone:
            msg = self._get_exception_formatted_message(
                response, "API GONE")
            resp.exc = UpstreamDependencyGone(msg)
        elif response.status_code == 400:
            msg = self._get_exception_formatted_message(
                response, "CLIENT ERROR")
            resp.exc = InvalidRequest400(msg)
        elif response.status_code == 404:
            msg = self._get_exception_formatted_message(
                response, "NOT FOUND")
            resp.exc = NothingFound404(msg)
        elif response.status_code == 409:
            msg = self._get_exception_formatted_message(
                response, "DUPLICATE RECORD")
            resp.exc = DuplicateRecord409(msg)
        elif str(response.status_code)[0] == "4":
            msg = self._get_exception_formatted_message(
                response, "CLIENT ERROR")
            resp.exc = ClientError4xx(msg)
        elif response.status_code == 502 and self.apiName == "MbuAPI":
            msg = self._get_exception_formatted_message(
                response, "SERVER ERROR")
            resp.exc = QOperationFailed502(msg)
        elif str(response.status_code)[0] == "5":
            msg = self._get_exception_formatted_message(
                response, "SERVER ERROR")
            resp.exc = ServerError5xx(msg)
        else:
            msg = self._get_exception_formatted_message(
                response, "UNKNOWN ERROR")
            resp.exc = UnknownError(msg)
        return resp

    @validate_timeout
    def _api_request(self, method: str, endpoint: str,
                     queryParams: str | None = None, data: dict | None = None,
                     attempts: int = 0, retryDelay: int = 5,
                     responseAsJson: bool = True, passOnFailure: bool = True,
                     timeout: Any = None, json: bool = True):
        """Make basic API request.

        Args:
            method (str): Which method to use to make the request.
            endpoint (str): Path to use to make the request.

        Kwargs:
            queryParams (str): Query parameters as a string. The string must
                start with '?'.
            data (dict): This data will be sent using the `json` kwargs of
                requests.
            attempts (int):
            retryDelay ():
            responseAsJson (bool): Need a response as json or text
            passOnFailure (bool): Pass the failure or raise exception
            timeout: Request timeout.
            json: If data is something other than json, set to `False`

        """
        if data is None:
            data = {}
        requests_session = requests.Session()
        methods = frozenset(["GET", "PUT", "POST", "DELETE"])
        if self.apiName == "CtkAPI":
            methods = frozenset(['GET', 'POST'])
        retry = Retry(
            total=self.throttleMaxRetries,
            status_forcelist=self.throttleCodes,
            backoff_factor=self.throttleBackoffFactor,
            raise_on_redirect=False,
            raise_on_status=False,
            allowed_methods=methods)
        # retry = Retry(**retryArgs)
        adapter = requests.adapters.HTTPAdapter(max_retries=retry)
        requests_session.mount('http://', adapter)
        requests_session.mount('https://', adapter)
        if queryParams:
            url = "{}{}{}".format(self.baseURL, endpoint, queryParams)
        else:
            url = "{}{}".format(self.baseURL, endpoint)
        msg = ("{} REQUEST => {} {}, {}".format(
            self.apiName, method.upper(), url, data))
        LOGGER.debug(msg)
        method = method.lower()
        _data = None
        _json = data or None
        if not json:
            _data = data or None
            _json = None
        if method in ["post", "put", "get", "delete"]:
            apiHeaders = copy.deepcopy(self.headers)
            # Add token if tokenHeader defined
            if self.tokenHeader:
                LOGGER.debug("Adding header %s to the %s url %s call",
                             self.tokenHeader, url, method)
                apiHeaders[self.tokenHeader] = self.token
            if self.internalTokenHeader:
                LOGGER.debug("Adding header %s to the %s url %s call",
                             self.internalTokenHeader, url, method)
                apiHeaders[self.internalTokenHeader] = self.internalToken
            try:
                response = getattr(requests_session, method)(
                    url, json=_json, data=_data, headers=apiHeaders,
                    verify=self.verifySSL, timeout=timeout)
                if self.apiName != 'IdentityAPI':
                    unauthorizedStatusCodes = (
                        [401, 403] if self.apiName == 'CtkAPI' else [401])
                    while response.status_code in unauthorizedStatusCodes:
                        self._handle_invalid_token()
                        response = getattr(requests_session, method)(
                            url, json=_json, data=_data, headers=apiHeaders,
                            verify=self.verifySSL, timeout=timeout)
                    # Reset tokenRetryCount since we got a token before
                    # tokenMaxRetries was exceeded.
                    self.tokenRetryCount = 0
            except requests.exceptions.RequestException as e:
                attempts += 1
                if attempts <= 5:
                    time.sleep(retryDelay)
                    response = self._api_request(
                        method, endpoint, queryParams=queryParams,
                        data=data, attempts=attempts,
                        responseAsJson=responseAsJson,
                        retryDelay=retryDelay,
                        timeout=timeout, json=json)
                else:
                    raise UpstreamDependencyGone(e) from e
        else:
            raise ValueError("Requested method not supported.")

        retVal = response

        # Get ApiResponse when there is response from requests
        if not isinstance(retVal, ApiResponse):
            retVal = self._check_response(response,
                                          responseAsJson=responseAsJson,
                                          passOnFailure=passOnFailure)
        return retVal

    @staticmethod
    def _raise_on_passonfailure(passOnFailure: bool, exc: BaseException):
        """Raise when passonfailure.

        Raise the exception when pass the passOnFailure flag.

        Args:
            passOnFailure (bool): Pass when filure happen or raise exception.
            exc (BaseException): Exception to raise.

        """
        # Check the user select to raise exception and resp.exec is actually a
        # exception. If you try to raise any thing, it will raise exception as
        # TypeError: exceptions must derive from BaseException, means after the
        # raise it should be `BaseException` type
        if passOnFailure is False and exc and isinstance(exc, BaseException):
            raise exc

    def request(self, method: str, endpoint: str, data: dict | None = None,
                queryParams: str | None = None, returnObj: bool = False,
                responseAsJson: bool = True, passOnFailure: bool = True,
                timeout: Any = None, json: bool = True,
                **kwargs: dict | None) -> Any:
        """Override this method in each of the API resources.

        This will allow for custom pagination if required.

        See `_api_request` for all kwargs.
        """
        # pylint: disable=W0613
        resp = self._api_request(
            method, endpoint, queryParams=queryParams,
            responseAsJson=responseAsJson,
            passOnFailure=passOnFailure, data=data or {},
            timeout=timeout, json=json)
        self._raise_on_passonfailure(passOnFailure, resp.exc)
        if resp.success is False:
            return None
        return resp if returnObj else resp.data

    def _verify_get_request(self, method: str) -> None:
        if method.upper() != 'GET':
            msg = ("{} `{}` method not supported for pagination.  "
                   "Please retry request using `GET` method, or setting "
                   "paginated=False.".
                   format(self.apiName, method.upper()))
            LOGGER.error(msg)
            raise ApiRequestError(msg)

    def post(self, endpoint: str = "/", data: dict | None = None,
             queryParams: str | None = None, returnObj: bool = False,
             responseAsJson: bool = True, passOnFailure: bool = True,
             timeout: Any = None, json: bool = True,
             **kwargs: dict | None) -> Any:
        """Post request."""
        # pylint: disable=W0613
        return self.request(method="POST", endpoint=endpoint,
                            data=data or None, queryParams=queryParams,
                            returnObj=returnObj, responseAsJson=responseAsJson,
                            passOnFailure=passOnFailure, timeout=timeout,
                            json=json, **kwargs)

    def get(self, endpoint: str = "/", queryParams: str | None = None,
            returnObj: bool = False, responseAsJson: bool = True,
            passOnFailure: bool = True, timeout: Any = None, json: bool = True,
            **kwargs: dict | None) -> Any:
        """Get request."""
        # pylint: disable=W0221,W0613
        data = self.request(method="GET", endpoint=endpoint, data=None,
                            queryParams=queryParams, returnObj=returnObj,
                            responseAsJson=responseAsJson,
                            passOnFailure=passOnFailure, timeout=timeout,
                            json=json, **kwargs)
        return data

    def put(self, endpoint: str = "/", data: dict | None = None,
            returnObj: bool = False, responseAsJson: bool = True,
            passOnFailure: bool = True, timeout: Any = None, json: bool = True,
            **kwargs: dict | None) -> Any:
        """Put request."""
        # pylint: disable=W0613
        return self.request(method="PUT", endpoint=endpoint,
                            data=data or None, queryParams=None,
                            returnObj=returnObj, responseAsJson=responseAsJson,
                            passOnFailure=passOnFailure, timeout=timeout,
                            json=json, **kwargs)

    def delete(self, endpoint: str = "/", returnObj: bool = False,
               responseAsJson: bool = True, passOnFailure: bool = True,
               timeout: Any = None, json: bool = True,
               **kwargs: dict | None) -> Any:
        """Delete request."""
        # pylint: disable=W0613
        return self.request(method="DELETE", endpoint=endpoint,
                            data=None, queryParams=None,
                            returnObj=returnObj, responseAsJson=responseAsJson,
                            passOnFailure=passOnFailure, timeout=timeout,
                            json=json, **kwargs)

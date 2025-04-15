"""BaseResourceLib REST API."""
# pylint: disable=R,W0221,W0237
from concurrent.futures import as_completed
from concurrent.futures import ThreadPoolExecutor
import logging
from typing import Any

from .base import ApiBase

LOGGER = logging.getLogger(__name__)


class BRLBaseApi(ApiBase):
    """BaseResourceLib API."""

    def brl_request(self, method: str, endpoint: str,
                    queryParams: str | None = None, data: dict | None = None,
                    paginated: bool = False, threads: int = 4,
                    responseAsJson: bool = True, passOnFailure: bool = True,
                    timeout: Any = None, json: bool = True,
                    returnObj: bool = False) -> Any:
        """Creating API with this are paginated."""
        if not paginated:
            response = self._api_request(
                method, endpoint, passOnFailure=passOnFailure,
                responseAsJson=responseAsJson,
                queryParams=queryParams, data=data or dict(),
                timeout=timeout, json=json)

            self._raise_on_passonfailure(response.passOnFailure, response.exc)

            if returnObj is True:
                return response
            if isinstance(response.data, dict) and "items" in response.data:
                return response.data['items']
            return None if response.success is False else response.data
        self._verify_get_request(method)
        results = []
        paginate = "page={page}&per_page={per_page}"
        if not queryParams:
            queryParams = "?{}".format(paginate)
        else:
            queryParams = "{}&{}".format(queryParams, paginate)
        response = self._api_request(
            method, endpoint,
            queryParams.format(page=1, per_page=self.perPage),
            responseAsJson=responseAsJson,
            passOnFailure=passOnFailure,
            timeout=timeout, json=json)
        self._raise_on_passonfailure(response.passOnFailure, response.exc)
        if response.success is False:
            return None
        results.extend(
            response.data['items'] if "items" in response.data
            else response.data)
        hasNext = "has_next" if "has_next" in response.data else "hasNext"
        totalPages = "pages" if "pages" in response.data else "totalPages"
        if response.data[hasNext]:
            urls = []
            for i in range(2, response.data[totalPages] + 1):
                url = "{}{}".format(endpoint, queryParams.format(
                    page=i, per_page=self.perPage))
                urls.append(url)
            with ThreadPoolExecutor(max_workers=threads) as executor:
                future_to_url = {
                    executor.submit(
                        self._api_request,
                        method,
                        endpoint,
                        responseAsJson=responseAsJson,
                        passOnFailure=passOnFailure,
                        timeout=timeout, json=json): endpoint for endpoint in [
                            s for s in urls]}
                for future in as_completed(future_to_url):
                    url = future_to_url[future]
                    try:
                        res = future.result()
                        results.extend(
                            res.data['items'] if "items" in res.data
                            else res.data)
                    except Exception as exc:  # pylint: disable=W0703
                        msg = "{} generated an exception: {}".format(url, exc)
                        LOGGER.exception(msg)
        return results

    def request(self, method: str, endpoint: str, queryParams: str = None,
                data: dict = None, paginated: bool = False, threads: int = 4,
                responseAsJson: bool = True, passOnFailure: bool = True,
                timeout: Any = None, json: bool = True,
                returnObj: bool = False, **kwargs) -> Any:
        """Run an API request for BaseResourceLib API."""
        if queryParams is not None:
            if "__distinct" in queryParams:
                paginated = False
        return self.brl_request(
            method=method, endpoint=endpoint, queryParams=queryParams,
            data=data, paginated=paginated, threads=threads,
            responseAsJson=responseAsJson, passOnFailure=passOnFailure,
            timeout=timeout, json=json, returnObj=returnObj)

from typing import Any
from urllib.parse import urljoin

import requests

from dataverse.errors import DataverseError


class Dataverse:
    """
    The main entrypoint for communicating with a given Dataverse Environment.

    Parameters
    ----------
    session: requests.Session
        The authenticated session used to communicate with the Web API.
    environment_url : str
        The environment URL that is used as a base for all API calls.
    """

    def __init__(self, session: requests.Session, environment_url: str):
        self._session = session
        self._environment_url = environment_url
        self._endpoint = urljoin(environment_url, "api/data/v9.2/")

    def _api_call(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        data: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> requests.Response:
        """
        Send API call to Dataverse.

        Parameters
        ----------
        method : str
            Request method.
        url : str
            URL added to endpoint.
        headers : dict
            Optional request headers. Will replace defaults.
        data : dict
            String payload.
        json : str
            Serializable JSON payload.

        Returns
        -------
        requests.Response
            Response from API call.

        Raises
        ------
        requests.exceptions.HTTPError
        """
        request_url = urljoin(self._endpoint, url)

        default_headers = {
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
            "OData-Version": "4.0",
            "OData-MaxVersion": "4.0",
        }

        if headers:
            for k, v in headers.items():
                default_headers[k] = v

        try:
            resp = self._session.request(
                method=method,
                url=request_url,
                headers=default_headers,
                data=data,
                json=json,
                timeout=120,
            )
            resp.raise_for_status()
        except requests.exceptions.HTTPError as e:
            raise DataverseError(
                message=(
                    f"Error with GET request: {e.args[0]}"
                    + f"{'// Response body: '+ e.response.text if e.response else ''}"
                ),
                response=e.response,
            ) from e

        return resp

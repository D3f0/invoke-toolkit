"""
http helpers

In order to keep the source code in Python only format, the popular
Python library requests would not allow us to use shiv or similar tools
for packaging, so we rather use Python internal HTTP client or use
curl
"""

import json
import urllib.request
import urllib.parse
from logging import getLogger


logger = getLogger(__name__)


def make_request(url: str, method="GET", content_type=None, parse_json=True):
    """Makes a request using urllib.

    Args:
      url: The URL to make the request to.
      method: The HTTP method to use. Defaults to "GET".
      content_type: The content type of the request body.
      parse_json: Whether to unmarshal the response as JSON. Defaults to True.

    Returns:
      The response from the server as either a Python object (if parse_json is True) or raw bytes.
    """

    data = None
    headers = {}

    if method == "POST" and content_type:
        headers["Content-Type"] = content_type
        if isinstance(data, dict):
            data = urllib.parse.urlencode(data).encode("utf-8")

    req = urllib.request.Request(url, data=data, method=method, headers=headers)

    try:
        with urllib.request.urlopen(req) as response:
            response_data = response.read()
            if parse_json:
                try:
                    return json.loads(response_data)
                except json.JSONDecodeError:
                    return response_data  # Return raw data if JSON decoding fails
            else:
                return response_data
    except urllib.error.HTTPError as e:
        logger.exception(f"HTTP Error: {e.code} - {e.reason}")
        return None
    except urllib.error.URLError as e:
        logger.exception(f"URL Error: {e.reason}")

        return None

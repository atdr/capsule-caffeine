"""Fetching nespresso.com pages and reading the JSON embedded in them."""

import json

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

USER_AGENT = "capsule-caffeine (+https://github.com/atdr/capsule-caffeine)"
TIMEOUT_S = 20


class PageError(RuntimeError):
    """A page did not contain the data the scraper expects."""


def make_session(retries: int = 5) -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=retries,
        backoff_factor=1,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers["User-Agent"] = USER_AGENT
    return session


def extract_embedded_json(html: str, selector: str) -> dict:
    """Return the JSON object inside the first element matching `selector`.

    Nespresso renders each page component's data into a <script> placed straight
    after the component's mount <div>, so selectors look like `div[id^=...]+script`.
    """
    tags = BeautifulSoup(html, "html.parser").select(selector)
    if not tags:
        raise PageError(f"no element matches {selector!r}")
    text = tags[0].get_text()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end < start:
        raise PageError(f"no JSON object in the element matching {selector!r}")
    return json.loads(text[start : end + 1])


def fetch_embedded_json(session: requests.Session, url: str, selector: str) -> dict:
    response = session.get(url, timeout=TIMEOUT_S)
    response.raise_for_status()
    try:
        return extract_embedded_json(response.text, selector)
    except PageError as exc:
        raise PageError(f"{url}: {exc}") from exc

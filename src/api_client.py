import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


BASE_URL = "https://api.estrategia.com"
REQUEST_DELAY = 0.2


def create_session(token: str) -> requests.Session:
    """Cria sessao HTTP autenticada com headers padrao."""
    session = requests.Session()

    retry = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)

    session.headers.update({
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://med.estrategia.com",
        "Referer": "https://med.estrategia.com/",
        "x-vertical": "medicina",
        "x-requester-id": "front-student",
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
        ),
    })

    return session


def get(session: requests.Session, path: str, params: dict = None) -> dict:
    """GET request com rate limiting."""
    url = f"{BASE_URL}{path}" if path.startswith("/") else path
    time.sleep(REQUEST_DELAY)
    resp = session.get(url, params=params)
    resp.raise_for_status()
    return resp.json()


def post(session: requests.Session, path: str, json_data: dict = None, params: dict = None) -> dict:
    """POST request com rate limiting."""
    url = f"{BASE_URL}{path}" if path.startswith("/") else path
    time.sleep(REQUEST_DELAY)
    resp = session.post(url, json=json_data, params=params)
    resp.raise_for_status()
    return resp.json()

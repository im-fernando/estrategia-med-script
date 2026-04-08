import os

import requests


LOGIN_URL = "https://api.accounts.estrategia.com/auth/login"
COOKIES_FILE = "cookies.txt"


def login(email: str, password: str) -> str:
    """Faz login e retorna o JWT token."""
    resp = requests.post(
        LOGIN_URL,
        json={"email": email, "password": password},
        headers={
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "Origin": "https://perfil.estrategia.com",
            "Referer": "https://perfil.estrategia.com/",
            "x-requester-id": "perfil",
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
            ),
        },
    )

    if not resp.ok:
        try:
            body = resp.json()
        except Exception:
            body = resp.text
        print(f"  Resposta do servidor ({resp.status_code}): {body}")
        resp.raise_for_status()

    # Tentar extrair token do cookie __Secure-SID
    sid_cookie = None
    for cookie in resp.cookies:
        if cookie.name == "__Secure-SID":
            sid_cookie = cookie.value
            break

    if not sid_cookie:
        for header_val in resp.headers.get("set-cookie", "").split(","):
            if "__Secure-SID=" in header_val:
                sid_cookie = header_val.split("__Secure-SID=")[1].split(";")[0]
                break

    if not sid_cookie:
        try:
            data = resp.json()
            sid_cookie = (
                data.get("token")
                or data.get("access_token")
                or (data.get("data", {}) or {}).get("token")
                or (data.get("data", {}) or {}).get("access_token")
            )
        except Exception:
            pass

    if not sid_cookie:
        raise RuntimeError(
            "Nao foi possivel extrair o token de autenticacao. "
            "Verifique email e senha."
        )

    return sid_cookie


def load_token_from_cookies(path: str = COOKIES_FILE) -> str:
    """Extrai o JWT token do arquivo cookies.txt (formato Netscape)."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Arquivo {path} nao encontrado.")

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) >= 7 and parts[5] == "__Secure-SID":
                token = parts[6]
                if token:
                    return token

    raise RuntimeError(
        f"Cookie __Secure-SID nao encontrado em {path}. "
        "Exporte os cookies do navegador novamente."
    )


def has_cookies_file(path: str = COOKIES_FILE) -> bool:
    """Verifica se o arquivo cookies.txt existe."""
    return os.path.exists(path)

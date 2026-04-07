import requests


LOGIN_URL = "https://api.accounts.estrategia.com/auth/login"


def login(email: str, password: str) -> str:
    """Faz login e retorna o JWT token."""
    resp = requests.post(
        LOGIN_URL,
        json={"email": email, "password": password},
        headers={
            "Content-Type": "application/json",
            "Origin": "https://perfil.estrategia.com",
            "Referer": "https://perfil.estrategia.com/",
            "x-requester-id": "perfil",
        },
    )
    resp.raise_for_status()

    sid_cookie = None
    for cookie in resp.cookies:
        if cookie.name == "__Secure-SID":
            sid_cookie = cookie.value
            break

    if not sid_cookie:
        set_cookie = resp.headers.get("set-cookie", "")
        if "__Secure-SID=" in set_cookie:
            sid_cookie = set_cookie.split("__Secure-SID=")[1].split(";")[0]

    if not sid_cookie:
        data = resp.json()
        if "token" in data:
            sid_cookie = data["token"]
        elif "data" in data and isinstance(data["data"], dict):
            sid_cookie = data["data"].get("token")

    if not sid_cookie:
        raise RuntimeError(
            "Nao foi possivel extrair o token de autenticacao. "
            "Verifique email e senha."
        )

    return sid_cookie

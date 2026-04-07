import requests

from src.api_client import get


def fetch_config(session: requests.Session) -> dict:
    """Busca configuracao de filtros da plataforma."""
    data = get(session, "/bff/questions/config")
    return data.get("data", data)


def get_catalogs(config: dict) -> list[dict]:
    """Retorna lista de catalogs disponiveis."""
    return config.get("catalogs", [])


def get_default_filters(config: dict) -> list[dict]:
    """Monta lista de filtros default (including_filters com default=True)."""
    filters = []
    for f in config.get("including_filters", []):
        if f.get("default"):
            filters.append(f["filter"])
    return filters


def get_excluding_filters(config: dict) -> list[dict]:
    """Retorna filtros de exclusao disponiveis."""
    return config.get("excluding_filters", [])


def get_advanced_filters(config: dict) -> list[dict]:
    """Retorna filtros avancados disponiveis."""
    return config.get("advanced_filters", [])

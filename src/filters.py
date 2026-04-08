import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

import requests

from src.api_client import BASE_URL


# Rate limiter compartilhado entre threads
_rate_lock = Lock()
_last_request = [0.0]
MIN_INTERVAL = 0.05  # 50ms entre requests (rapido mas seguro)


def _rate_limited_get(session: requests.Session, path: str, params: dict = None) -> dict:
    """GET com rate limiting thread-safe."""
    url = f"{BASE_URL}{path}" if path.startswith("/") else path
    with _rate_lock:
        elapsed = time.time() - _last_request[0]
        if elapsed < MIN_INTERVAL:
            time.sleep(MIN_INTERVAL - elapsed)
        _last_request[0] = time.time()
    resp = session.get(url, params=params)
    if not resp.ok:
        try:
            err = resp.json()
        except Exception:
            err = resp.text
        print(f"  GET {path} -> {resp.status_code}: {err}")
    resp.raise_for_status()
    return resp.json()


def fetch_classifications(session: requests.Session, parent_id: str, per_page: int = 100) -> list[dict]:
    """Busca opcoes de classificacao paginadas para um dado parent_id."""
    all_items = []
    page = 1

    while True:
        data = _rate_limited_get(
            session,
            f"/bff/questions/filters/classifications/{parent_id}",
            params={"page": page, "per_page": per_page},
        )

        items = data.get("data", []) if isinstance(data, dict) else data
        if not items:
            break

        all_items.extend(items)

        pagination = data.get("pagination", {}) if isinstance(data, dict) else {}
        total = pagination.get("total", 0)

        if len(all_items) >= total or len(items) < per_page:
            break

        page += 1

    return all_items


def _fetch_children(session: requests.Session, item: dict, depth: int, max_depth: int) -> list[dict]:
    """Busca filhos de um item e retorna lista flat com depth."""
    if depth >= max_depth or not item.get("has_children") or not item.get("id"):
        return []

    children = fetch_classifications(session, item["id"])
    results = []
    parent_id = item.get("id")
    for child in children:
        child["_depth"] = depth
        if parent_id:
            child["_parent_id"] = parent_id
        results.append(child)
    return results


def fetch_tree_parallel(
    session: requests.Session,
    root_items: list[dict],
    root_depth: int = 1,
    max_depth: int = 10,
    max_workers: int = 8,
) -> list[dict]:
    """Busca arvore de classificacoes em paralelo usando BFS por nivel."""
    all_items = []

    # Fila: itens cujos filhos precisamos buscar
    pending = [(item, root_depth) for item in root_items if item.get("has_children")]

    while pending:
        next_pending = []

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            future_map = {}
            for item, depth in pending:
                if depth >= max_depth:
                    continue
                fut = pool.submit(_fetch_children, session, item, depth, max_depth)
                future_map[fut] = (item, depth)

            for fut in as_completed(future_map):
                item, depth = future_map[fut]
                try:
                    children = fut.result()
                    all_items.extend(children)
                    # Agendar filhos que tambem tem children
                    for child in children:
                        if child.get("has_children"):
                            next_pending.append((child, depth + 1))
                except Exception:
                    pass

        pending = next_pending

    return all_items


def fetch_topics_full_tree(session: requests.Session, topic_catalog_id: str) -> list[dict]:
    """Busca arvore completa de topicos em paralelo."""
    from src.api_client import get

    print(f"    Buscando topicos raiz...")
    try:
        data = get(session, "/bff/questions/topics")
        root_topics = data.get("data", data) if isinstance(data, dict) else data
        if not isinstance(root_topics, list):
            root_topics = []
    except Exception:
        root_topics = fetch_classifications(session, topic_catalog_id)
    print(f"    {len(root_topics)} especialidades raiz encontradas.")

    # Marcar depth 0
    for t in root_topics:
        t["_depth"] = 0

    # Buscar subtopicos em paralelo
    print(f"    Buscando subtopicos em paralelo (8 threads)...")
    subtopics = fetch_tree_parallel(session, root_topics, root_depth=1, max_workers=8)
    print(f"    {len(subtopics)} subtopicos encontrados.")

    return root_topics + subtopics


def fetch_catalog_options(session: requests.Session, catalog_id: str) -> list[dict]:
    """Busca todas as opcoes de um catalogo paginado."""
    return fetch_classifications(session, catalog_id)


def fetch_teachers(session: requests.Session) -> list[dict]:
    """Busca lista de professores (paginado)."""
    all_teachers = []
    page = 1
    per_page = 100

    while True:
        data = _rate_limited_get(
            session,
            "/bff/questions/filters/teacher",
            params={"page": page, "per_page": per_page},
        )
        items = data.get("data", []) if isinstance(data, dict) else data
        if not isinstance(items, list) or not items:
            break
        all_teachers.extend(items)

        pagination = data.get("pagination", {}) if isinstance(data, dict) else {}
        total = pagination.get("total", 0)
        if len(all_teachers) >= total or len(items) < per_page:
            break
        page += 1

    return all_teachers


def fetch_regions(session: requests.Session) -> list[dict]:
    """Busca regioes do JSON estatico no S3 (request limpo, sem headers de auth)."""
    try:
        resp = requests.get(
            "https://questions-production-config.s3-sa-east-1.amazonaws.com/locations-v2.json"
        )
        resp.raise_for_status()
        locations = resp.json()
        if isinstance(locations, list):
            return locations
    except Exception as e:
        print(f"    Aviso: erro ao buscar regioes: {e}")
    return []


def generate_years(start: int = 2003, end: int = 2026) -> list[int]:
    """Gera lista de anos disponiveis."""
    return list(range(end, start - 1, -1))


def fetch_all_filter_options(session: requests.Session, catalogs: list[dict]) -> dict:
    """Busca todas as opcoes de filtro disponiveis."""
    from src.api_client import get
    options = {}

    topic_catalog_id = None
    for catalog in catalogs:
        if catalog.get("key") == "topic":
            topic_catalog_id = catalog.get("id")
            break

    if topic_catalog_id:
        print("  Buscando especialidades/assuntos (arvore completa, paralelo)...")
        try:
            options["topics"] = fetch_topics_full_tree(session, topic_catalog_id)
            print(f"    Total: {len(options['topics'])} topicos/subtopicos.")
        except Exception as e:
            print(f"    Aviso: erro ao buscar topicos: {e}")
            options["topics"] = []
    else:
        print("  Aviso: catalog de topicos nao encontrado na config.")
        options["topics"] = []

    print("  Buscando anos...")
    options["years"] = generate_years()

    print("  Buscando professores...")
    try:
        options["teachers"] = fetch_teachers(session)
    except Exception as e:
        print(f"    Aviso: nao foi possivel buscar professores: {e}")
        options["teachers"] = []

    print("  Buscando regioes (com subregioes)...")
    try:
        options["regions"] = fetch_regions(session)
        print(f"    {len(options['regions'])} regioes encontradas.")
    except Exception as e:
        print(f"    Aviso: nao foi possivel buscar regioes: {e}")
        options["regions"] = []

    for catalog in catalogs:
        key = catalog.get("key", "")
        name = catalog.get("name", key)
        origin = catalog.get("origin", "")
        catalog_id = catalog.get("id", "")

        if origin == "catalogs" and catalog_id:
            print(f"  Buscando {name}...")
            try:
                options[key] = fetch_catalog_options(session, catalog_id)
                print(f"    Encontrados {len(options[key])} itens.")
            except Exception as e:
                print(f"    Aviso: nao foi possivel buscar {name}: {e}")
                options[key] = []

    return options

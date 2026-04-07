import requests

from src.api_client import get


def fetch_classifications(session: requests.Session, parent_id: str, per_page: int = 100) -> list[dict]:
    """Busca opcoes de classificacao paginadas para um dado parent_id."""
    all_items = []
    page = 1

    while True:
        data = get(
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


def fetch_classifications_recursive(
    session: requests.Session,
    parent_id: str,
    depth: int = 0,
    max_depth: int = 10,
) -> list[dict]:
    """Busca classificacoes recursivamente, descendo em items com has_children=True."""
    if depth >= max_depth:
        return []

    items = fetch_classifications(session, parent_id)
    all_items = []

    for item in items:
        item["_depth"] = depth
        all_items.append(item)

        if item.get("has_children"):
            children = fetch_classifications_recursive(
                session, item["id"], depth + 1, max_depth
            )
            all_items.extend(children)

    return all_items


def fetch_topics(session: requests.Session) -> list[dict]:
    """Busca lista de especialidades/assuntos (nivel raiz)."""
    data = get(session, "/questions/topics")
    return data.get("data", data) if isinstance(data, dict) else data


def fetch_topics_full_tree(session: requests.Session, topics: list[dict]) -> list[dict]:
    """Busca arvore completa de topicos com todos os subtopicos."""
    all_topics = []

    for topic in topics:
        topic["_depth"] = 0
        all_topics.append(topic)

        topic_id = topic.get("id", "")
        if not topic_id:
            continue

        print(f"    Buscando subtopicos de {topic.get('name', topic_id)}...")
        try:
            children = fetch_classifications_recursive(session, topic_id, depth=1)
            all_topics.extend(children)
            if children:
                print(f"      {len(children)} subtopicos encontrados.")
        except Exception as e:
            print(f"      Aviso: erro ao buscar subtopicos: {e}")

    return all_topics


def fetch_catalog_options(session: requests.Session, catalog_id: str) -> list[dict]:
    """Busca todas as opcoes de um catalogo paginado (instituicao, banca, finalidade)."""
    return fetch_classifications(session, catalog_id)


def fetch_teachers(session: requests.Session) -> list[dict]:
    """Busca lista de professores."""
    data = get(session, "/questions/filters/teacher")
    return data.get("data", data) if isinstance(data, dict) else data


def fetch_regions(session: requests.Session) -> dict:
    """Busca regioes (estados e municipios)."""
    regions = {}
    for region_type in ["STATE", "MUNICIPAL", "TYPES"]:
        try:
            data = get(session, f"/questions/filters/region/{region_type}")
            regions[region_type] = data.get("data", data) if isinstance(data, dict) else data
        except Exception:
            regions[region_type] = []
    return regions


def generate_years(start: int = 2003, end: int = 2026) -> list[int]:
    """Gera lista de anos disponiveis."""
    return list(range(end, start - 1, -1))


def fetch_all_filter_options(session: requests.Session, catalogs: list[dict]) -> dict:
    """Busca todas as opcoes de filtro disponíveis."""
    options = {}

    print("  Buscando especialidades/assuntos...")
    root_topics = fetch_topics(session)
    print(f"    {len(root_topics)} especialidades raiz encontradas.")
    print("  Buscando arvore completa de subtopicos (pode demorar)...")
    options["topics"] = fetch_topics_full_tree(session, root_topics)

    print("  Buscando anos...")
    options["years"] = generate_years()

    print("  Buscando professores...")
    try:
        options["teachers"] = fetch_teachers(session)
    except Exception as e:
        print(f"    Aviso: nao foi possivel buscar professores: {e}")
        options["teachers"] = []

    print("  Buscando regioes...")
    try:
        options["regions"] = fetch_regions(session)
    except Exception as e:
        print(f"    Aviso: nao foi possivel buscar regioes: {e}")
        options["regions"] = {}

    for catalog in catalogs:
        key = catalog.get("key", "")
        name = catalog.get("name", key)
        origin = catalog.get("origin", "")
        catalog_id = catalog.get("id", "")

        if origin == "catalogs" and catalog_id:
            print(f"  Buscando {name} ({catalog_id})...")
            try:
                options[key] = fetch_catalog_options(session, catalog_id)
                print(f"    Encontrados {len(options[key])} itens.")
            except Exception as e:
                print(f"    Aviso: nao foi possivel buscar {name}: {e}")
                options[key] = []

    return options

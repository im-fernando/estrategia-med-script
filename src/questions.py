import json
import math
import os

import requests
from tqdm import tqdm

from src.api_client import post


CACHE_FILE = "data/questions.json"
PER_PAGE = 100


def build_search_filters(
    catalogs: list[dict],
    topic_ids: list[str] = None,
    filter_options: dict = None,
) -> list[dict]:
    """Monta payload de busca no formato exato da API.

    Ordem: topic (se houver) -> goal_id -> answer_types -> situacao -> solucoes
    """
    filters = []

    # 1. Topic filter (se especificado)
    if topic_ids:
        filters.append({
            "add": True,
            "entity": "topic",
            "entity_ids": topic_ids,
            "origin": "questions",
        })

    # 2. Goal_id - usar TODAS as finalidades se disponiveis, senao preselected
    for catalog in catalogs:
        preselected = catalog.get("preselected_values", [])
        if not preselected:
            continue
        key = catalog.get("key", "")
        all_ids = []
        if filter_options and key in filter_options:
            all_ids = [item["id"] for item in filter_options[key] if item.get("id")]
        if not all_ids:
            all_ids = preselected
        filters.append({
            "add": True,
            "entity": key,
            "entity_ids": all_ids,
            "origin": catalog.get("origin", "catalogs"),
        })

    # 3. Tipos de questao - todos
    filters.append({"add": True, "entity": "answer_type", "entity_ids": ["TRUE_OR_FALSE"], "filtro_includente": True})
    filters.append({"add": True, "entity": "answer_type", "entity_ids": ["MULTIPLE_CHOICE"], "filtro_includente": True})
    filters.append({"add": True, "entity": "answer_type", "entity_ids": ["DISCURSIVE"], "filtro_includente": True})

    # 4. Situacao
    filters.append({"add": True, "entity": "already_answered", "entity_ids": [], "filtro_includente": True})
    filters.append({"add": True, "entity": "not_answered", "entity_ids": [], "filtro_includente": True})

    # 5. Solucoes
    filters.append({"add": True, "entity": "include_with_text_solution", "entity_ids": [], "filtro_includente": True})
    filters.append({"add": True, "entity": "include_without_text_solution", "entity_ids": [], "filtro_includente": True})
    filters.append({"add": True, "entity": "include_with_video_solution", "entity_ids": [], "filtro_includente": True})
    filters.append({"add": True, "entity": "include_without_video_solution", "entity_ids": [], "filtro_includente": True})
    filters.append({"add": True, "entity": "include_with_video_and_text_solution", "entity_ids": [], "filtro_includente": True})

    # 6. Vigencia - incluir anuladas e desatualizadas para pegar tudo
    filters.append({"add": True, "entity": "label", "entity_ids": ["CANCELED"], "filtro_includente": True})
    filters.append({"add": True, "entity": "label", "entity_ids": ["OUTDATED"], "filtro_includente": True})

    return filters


def fetch_total_count(session: requests.Session, filters: list[dict]) -> int:
    """Busca contagem total de questoes via batch endpoint."""
    data = post(session, "/bff/questions/search/batch", json_data={"batch": [filters]})
    counts = data.get("data", [0])
    return counts[0] if counts else 0


def load_cache() -> list[dict]:
    """Carrega questoes do cache local."""
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_cache(questions: list[dict]):
    """Salva questoes no cache local."""
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False)


def _paginate_topic(session, catalogs, topic_id, topic_name, seen_ids, pbar, filter_options=None):
    """Busca todas as questoes de um topico com paginacao."""
    filters = build_search_filters(catalogs, topic_ids=[topic_id], filter_options=filter_options)
    questions = []
    page = 1

    while True:
        payload = {"filters": filters}
        data = post(
            session,
            "/bff/questions/search",
            json_data=payload,
            params={
                "page": page,
                "perPage": PER_PAGE,
                "order": "ASC",
                "sort": "key_pedagogical_order",
            },
        )

        raw = data.get("data", [])
        page_questions = raw if isinstance(raw, list) else []

        if not page_questions:
            break

        new_count = 0
        for q in page_questions:
            qid = q.get("id")
            if qid and qid not in seen_ids:
                questions.append(q)
                seen_ids.add(qid)
                new_count += 1

        pbar.update(new_count)

        if len(page_questions) < PER_PAGE:
            break

        page += 1

    return questions


def fetch_all_questions(
    session: requests.Session,
    config: dict,
    catalogs: list[dict],
    filter_options: dict,
    resume: bool = True,
) -> list[dict]:
    """Busca todas as questoes sem filtro de topico (pega tudo)."""
    # Contar total SEM filtro de topico (como o browser faz)
    filters_no_topic = build_search_filters(catalogs, topic_ids=None, filter_options=filter_options)
    print("\nContando questoes...")
    total = fetch_total_count(session, filters_no_topic)
    print(f"  Total: {total} questoes")
    pages_estimate = math.ceil(total / PER_PAGE)
    print(f"  Estimativa: {pages_estimate} paginas de {PER_PAGE} questoes")

    if total == 0:
        return []

    input("\nPressione Enter para iniciar o download (Ctrl+C para cancelar)...")

    cached = load_cache() if resume else []
    if cached:
        print(f"Cache encontrado com {len(cached)} questoes.")

    seen_ids = {q.get("id") for q in cached if q.get("id")}
    questions = list(cached)

    if cached and len(cached) >= total:
        print("Todas as questoes ja estao no cache.")
        return questions

    print(f"\nBaixando questoes...")

    # Carregar token de paginacao do cache se existir
    token_file = CACHE_FILE.replace(".json", "_token.txt")
    next_token = None
    if cached and os.path.exists(token_file):
        with open(token_file, "r") as f:
            next_token = f.read().strip() or None
        if next_token:
            print(f"Retomando do token de paginacao salvo...")

    page = 1
    with tqdm(total=total, initial=len(cached), unit="q") as pbar:
        while True:
            try:
                payload = {"filters": filters_no_topic}
                params = {
                    "perPage": PER_PAGE,
                    "order": "ASC",
                    "sort": "key_pedagogical_order",
                }

                # Usar token pagination apos 10k resultados
                if next_token:
                    params["token"] = next_token
                else:
                    params["page"] = page

                data = post(
                    session,
                    "/bff/questions/search",
                    json_data=payload,
                    params=params,
                )

                raw = data.get("data", [])
                page_questions = raw if isinstance(raw, list) else []

                if not page_questions:
                    break

                new_count = 0
                for q in page_questions:
                    qid = q.get("id")
                    if qid and qid not in seen_ids:
                        questions.append(q)
                        seen_ids.add(qid)
                        new_count += 1

                pbar.update(new_count)

                # Extrair next token para proxima pagina
                token_pag = data.get("token_pagination", {})
                next_token = token_pag.get("next_page_token", None) if isinstance(token_pag, dict) else None

                # Salvar cache periodicamente
                if page % 10 == 0:
                    save_cache(questions)
                    if next_token:
                        with open(token_file, "w") as f:
                            f.write(next_token)

                if len(page_questions) < PER_PAGE:
                    break

                page += 1

            except Exception as e:
                print(f"\nErro na pagina {page}: {e}")
                save_cache(questions)
                if next_token:
                    with open(token_file, "w") as f:
                        f.write(next_token)
                print("Cache salvo. Voce pode retomar depois.")
                raise

            save_cache(questions)

    print(f"\nTotal de questoes baixadas: {len(questions)}")
    return questions


def _fetch_page(session, filters, page, per_page, debug=False):
    """Busca uma pagina de questoes."""
    # Search usa {"filters": [...]} e perPage (camelCase)
    payload = {"filters": filters}

    if debug:
        import json as _json
        print(f"  [DEBUG] POST /bff/questions/search?page={page}&per_page={per_page}")
        print(f"  [DEBUG] Payload: {_json.dumps(payload, ensure_ascii=False)[:500]}")

    data = post(
        session,
        "/bff/questions/search",
        json_data=payload,
        params={
            "page": page,
            "perPage": per_page,
            "order": "ASC",
            "sort": "key_pedagogical_order",
        },
    )

    if debug:
        import json as _json
        print(f"  [DEBUG] Response keys: {list(data.keys()) if isinstance(data, dict) else type(data)}")
        print(f"  [DEBUG] Response: {_json.dumps(data, ensure_ascii=False)[:500]}")

    raw = data.get("data", [])
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        return raw.get("questions", raw.get("items", []))
    return []


def fetch_test_questions(
    session: requests.Session,
    config: dict,
    catalogs: list[dict],
    filter_options: dict,
    per_topic: int = 15,
) -> list[dict]:
    """Busca N questoes por topico raiz para teste rapido.

    A API aceita busca pelos IDs dos topicos raiz (de /bff/questions/topics).
    Os IDs da arvore de classifications sao diferentes e nao funcionam na busca.
    """
    topics = filter_options.get("topics", [])
    if not topics:
        print("Nenhum topico encontrado.")
        return []

    # Usar SOMENTE os topicos raiz (depth 0, vindos de /bff/questions/topics)
    test_topics = [t for t in topics if t.get("_depth", 0) == 0]
    if not test_topics:
        test_topics = topics[:7]

    all_questions = []
    seen_ids = set()

    print(f"Buscando ate {per_topic} questoes de {len(test_topics)} topicos raiz...\n")

    for i, topic in enumerate(test_topics):
        name = topic.get("name", "?")
        topic_id = topic.get("id", "")

        if not topic_id:
            continue

        filters = build_search_filters(catalogs, topic_ids=[topic_id], filter_options=filter_options)

        try:
            page_questions = _fetch_page(session, filters, 1, per_topic)
            new = 0
            for q in page_questions:
                qid = q.get("id")
                if qid and qid not in seen_ids:
                    all_questions.append(q)
                    seen_ids.add(qid)
                    new += 1

            print(f"  [{i+1}/{len(test_topics)}] {name}: {new} novas")

        except Exception as e:
            print(f"  [{i+1}/{len(test_topics)}] {name}: ERRO - {e}")

    print(f"\nTotal de questoes de teste: {len(all_questions)}")

    # Salvar amostra pra debug da estrutura
    if all_questions:
        sample_path = "data/question_sample.json"
        os.makedirs("data", exist_ok=True)
        with open(sample_path, "w", encoding="utf-8") as f:
            json.dump(all_questions[0], f, ensure_ascii=False, indent=2)
        print(f"Amostra salva em {sample_path}")

    return all_questions

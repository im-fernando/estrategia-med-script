import json
import math
import os

import requests
from tqdm import tqdm

from src.api_client import post


CACHE_FILE = "data/questions.jsonl"  # Uma questao por linha (append-friendly)
TOKEN_FILE = "data/questions_token.txt"
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


def load_cache_ids() -> set:
    """Carrega apenas os IDs das questoes do cache JSONL."""
    ids = set()
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    q = json.loads(line)
                    qid = q.get("id")
                    if qid:
                        ids.add(qid)
                except json.JSONDecodeError:
                    continue
    return ids


def append_questions(questions: list[dict]):
    """Append questoes ao cache JSONL (uma por linha)."""
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, "a", encoding="utf-8") as f:
        for q in questions:
            f.write(json.dumps(q, ensure_ascii=False) + "\n")


def load_cache() -> list[dict]:
    """Carrega todas as questoes do cache JSONL."""
    questions = []
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    questions.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return questions


def save_token(token: str):
    """Salva token de paginacao."""
    os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
    with open(TOKEN_FILE, "w") as f:
        f.write(token)


def load_token() -> str:
    """Carrega token de paginacao."""
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as f:
            return f.read().strip()
    return ""


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
) -> None:
    """Baixa todas as questoes direto pro disco (JSONL). Nao acumula na RAM."""
    filters_no_topic = build_search_filters(catalogs, topic_ids=None, filter_options=filter_options)
    print("\nContando questoes...")
    total = fetch_total_count(session, filters_no_topic)
    print(f"  Total: {total} questoes")
    pages_estimate = math.ceil(total / PER_PAGE)
    print(f"  Estimativa: {pages_estimate} paginas de {PER_PAGE} questoes")

    if total == 0:
        return

    input("\nPressione Enter para iniciar o download (Ctrl+C para cancelar)...")

    # Carregar IDs ja baixados (so IDs, nao as questoes inteiras)
    seen_ids = load_cache_ids() if resume else set()
    cached_count = len(seen_ids)
    if cached_count:
        print(f"Cache encontrado com {cached_count} questoes.")

    if cached_count >= total:
        print("Todas as questoes ja estao no cache.")
        return

    # Carregar token de retomada
    next_token = load_token() if resume else ""
    if next_token and cached_count > 0:
        print(f"Retomando do token de paginacao salvo...")

    # Se tem cache mas nao tem token, limpar pra comecar do zero
    if cached_count > 0 and not next_token and cached_count >= 10000:
        print(f"Cache tem {cached_count} questoes mas sem token. Recomeçando...")
        seen_ids = set()
        cached_count = 0
        os.remove(CACHE_FILE)

    page = 1
    if cached_count > 0 and not next_token:
        page = (cached_count // PER_PAGE) + 1

    print(f"\nBaixando questoes...")
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)

    with tqdm(total=total, initial=cached_count, unit="q") as pbar:
        while True:
            try:
                payload = {"filters": filters_no_topic}
                params = {
                    "perPage": PER_PAGE,
                    "order": "ASC",
                    "sort": "key_pedagogical_order",
                }

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

                # Filtrar duplicatas e gravar direto no disco
                new_questions = []
                for q in page_questions:
                    qid = q.get("id")
                    if qid and qid not in seen_ids:
                        new_questions.append(q)
                        seen_ids.add(qid)

                if new_questions:
                    append_questions(new_questions)

                pbar.update(len(new_questions))

                # Extrair next token
                token_pag = data.get("token_pagination", {})
                next_token = token_pag.get("next_page_token", None) if isinstance(token_pag, dict) else None

                # Salvar token periodicamente
                if next_token and page % 20 == 0:
                    save_token(next_token)

                if len(page_questions) < PER_PAGE:
                    break

                page += 1

            except Exception as e:
                print(f"\nErro na pagina {page}: {e}")
                if next_token:
                    save_token(next_token)
                print(f"Cache salvo ({len(seen_ids)} questoes). Voce pode retomar depois.")
                raise

    if next_token:
        save_token(next_token)

    print(f"\nTotal de questoes baixadas: {len(seen_ids)}")


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

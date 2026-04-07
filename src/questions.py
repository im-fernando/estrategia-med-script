import json
import math
import os

import requests
from tqdm import tqdm

from src.api_client import post


CACHE_FILE = "data/questions.json"
PER_PAGE = 100


def build_max_inclusive_payload() -> list[dict]:
    """Monta payload maximamente inclusivo para baixar TODAS as questoes."""
    return [
        # Tipos de questao - todos
        {"add": True, "entity": "answer_type", "entity_ids": ["TRUE_OR_FALSE"], "filtro_includente": True},
        {"add": True, "entity": "answer_type", "entity_ids": ["MULTIPLE_CHOICE"], "filtro_includente": True},
        {"add": True, "entity": "answer_type", "entity_ids": ["DISCURSIVE"], "filtro_includente": True},
        # Situacao - todas
        {"add": True, "entity": "already_answered", "entity_ids": [], "filtro_includente": True},
        {"add": True, "entity": "not_answered", "entity_ids": [], "filtro_includente": True},
        # Solucoes - todas
        {"add": True, "entity": "include_with_text_solution", "entity_ids": [], "filtro_includente": True},
        {"add": True, "entity": "include_without_text_solution", "entity_ids": [], "filtro_includente": True},
        {"add": True, "entity": "include_with_video_solution", "entity_ids": [], "filtro_includente": True},
        {"add": True, "entity": "include_without_video_solution", "entity_ids": [], "filtro_includente": True},
        {"add": True, "entity": "include_with_video_and_text_solution", "entity_ids": [], "filtro_includente": True},
        # Vigencia - incluir desatualizadas e anuladas
        {"add": True, "entity": "label", "entity_ids": ["OUTDATED"], "filtro_includente": True},
        {"add": True, "entity": "label", "entity_ids": ["CANCELED"], "filtro_includente": True},
    ]


def add_preselected_filters(filters: list[dict], catalogs: list[dict]) -> list[dict]:
    """Adiciona filtros pre-selecionados dos catalogs (ex: goal_id)."""
    result = list(filters)
    for catalog in catalogs:
        preselected = catalog.get("preselected_values", [])
        if preselected:
            result.append({
                "add": True,
                "entity": catalog["key"],
                "entity_ids": preselected,
                "origin": catalog.get("origin", "catalogs"),
            })
    return result


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


def fetch_all_questions(
    session: requests.Session,
    config: dict,
    catalogs: list[dict],
    resume: bool = True,
) -> list[dict]:
    """Busca todas as questoes com paginacao e cache."""
    filters = build_max_inclusive_payload()
    filters = add_preselected_filters(filters, catalogs)

    print("\nContando questoes...")
    total = fetch_total_count(session, filters)
    print(f"Total de questoes: {total}")

    if total == 0:
        return []

    cached = load_cache() if resume else []
    if cached:
        print(f"Cache encontrado com {len(cached)} questoes.")

    seen_ids = {q.get("id") for q in cached if q.get("id")}
    questions = list(cached)

    total_pages = math.ceil(total / PER_PAGE)
    start_page = (len(cached) // PER_PAGE) + 1 if cached else 1

    if start_page > total_pages:
        print("Todas as questoes ja estao no cache.")
        return questions

    print(f"Buscando questoes (pagina {start_page} a {total_pages})...")

    with tqdm(total=total, initial=len(cached), unit="q") as pbar:
        for page in range(start_page, total_pages + 1):
            try:
                data = post(
                    session,
                    "/bff/questions/search",
                    json_data=filters,
                    params={
                        "page": page,
                        "per_page": PER_PAGE,
                        "order": "ASC",
                        "sort": "key_pedagogical_order",
                    },
                )

                page_questions = data.get("data", {}).get("questions", [])
                if not page_questions:
                    page_questions = data.get("data", [])
                    if isinstance(page_questions, dict):
                        page_questions = page_questions.get("items", [])

                new_count = 0
                for q in page_questions:
                    qid = q.get("id")
                    if qid and qid not in seen_ids:
                        questions.append(q)
                        seen_ids.add(qid)
                        new_count += 1

                pbar.update(new_count or len(page_questions))

                if page % 10 == 0:
                    save_cache(questions)

                if not page_questions:
                    break

            except Exception as e:
                print(f"\nErro na pagina {page}: {e}")
                save_cache(questions)
                print("Cache salvo. Voce pode retomar depois.")
                raise

    save_cache(questions)
    print(f"\nTotal de questoes baixadas: {len(questions)}")
    return questions

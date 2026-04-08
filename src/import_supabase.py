"""Importa questoes do JSONL para o Supabase."""
import json
import os
import sys

from tqdm import tqdm

try:
    from supabase import create_client
except ImportError:
    print("Instale: pip install supabase")
    sys.exit(1)

# Reutiliza logica de transform do database.py
CATALOG_INSTITUTION = "63b07b3e-c200-4b3d-b9e6-742a096ae26e"
CATALOG_BANCA = "5d401e50-47cf-4d06-9a2f-19997cd0f258"
CATALOG_FINALIDADE = "4383bd62-e829-491e-8bb5-b40bd649817f"

JSONL_PATH = "data/questions.jsonl"
BATCH_SIZE = 500


def _catalog_name(exam: dict, catalog_id: str) -> str:
    catalogs = exam.get("catalogs", {})
    entry = catalogs.get(catalog_id, {})
    return entry.get("name", "") if isinstance(entry, dict) else ""


def transform_question(q: dict) -> tuple[dict, list[dict]]:
    """Transforma questao raw da API em rows para Supabase."""
    exam = q.get("exams", [{}])[0] if q.get("exams") else {}
    inst = _catalog_name(exam, CATALOG_INSTITUTION)
    banca = _catalog_name(exam, CATALOG_BANCA)
    finalidade = _catalog_name(exam, CATALOG_FINALIDADE)
    year = exam.get("year", None)

    region = ""
    if inst and len(inst) >= 2 and inst[2:3] in (" ", "-"):
        region = inst[:2]

    topics = []
    for t in q.get("topics", []):
        name = t.get("name", "")
        path = t.get("path", "")
        if name:
            topics.append({"n": name, "p": path})

    labels = q.get("labels", [])

    alternatives = q.get("alternatives", [])
    correct_letter = ""
    for a in alternatives:
        if isinstance(a, dict) and a.get("correct"):
            pos = int(a.get("position", 0))
            correct_letter = chr(65 + pos)
            break

    sol = q.get("solution", {})
    sol_text = ""
    if isinstance(sol, dict):
        sol_text = sol.get("complete", "") or sol.get("brief", "")

    question_row = {
        "id": q.get("id", ""),
        "statement": q.get("statement", ""),
        "answer_type": q.get("answer_type", "MULTIPLE_CHOICE"),
        "year": year,
        "institution": inst,
        "banca": banca,
        "finalidade": finalidade,
        "region": region,
        "labels": labels,  # Supabase serializa JSONB automaticamente
        "topics": topics,
        "correct_letter": correct_letter,
        "solution": sol_text,
        "has_video": bool(q.get("has_video_solution")),
        "video_url": q.get("solution_video_url", "") or "",
    }

    alt_rows = []
    for a in alternatives:
        if not isinstance(a, dict):
            continue
        pos = int(a.get("position", 0))
        alt_rows.append({
            "question_id": q.get("id", ""),
            "letter": chr(65 + pos),
            "body": a.get("body", ""),
            "correct": bool(a.get("correct")),
            "answer_pct": a.get("answer_percentage", 0),
        })

    return question_row, alt_rows


def count_lines(path: str) -> int:
    count = 0
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                count += 1
    return count


def main():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")

    if not url or not key:
        print("Defina as env vars: SUPABASE_URL e SUPABASE_SERVICE_KEY")
        print("  export SUPABASE_URL=https://xxx.supabase.co")
        print("  export SUPABASE_SERVICE_KEY=eyJ...")
        sys.exit(1)

    if not os.path.exists(JSONL_PATH):
        print(f"Arquivo {JSONL_PATH} nao encontrado. Rode main.py primeiro.")
        sys.exit(1)

    sb = create_client(url, key)

    # Contar linhas
    print("Contando questoes no JSONL...")
    total = count_lines(JSONL_PATH)
    print(f"  {total} questoes encontradas.")

    # Buscar IDs existentes para resume
    print("Verificando questoes ja importadas...")
    existing_ids = set()
    page = 0
    while True:
        result = sb.table("questions").select("id").range(page * 1000, (page + 1) * 1000 - 1).execute()
        if not result.data:
            break
        for row in result.data:
            existing_ids.add(row["id"])
        if len(result.data) < 1000:
            break
        page += 1
    print(f"  {len(existing_ids)} questoes ja importadas (serao puladas).")

    if len(existing_ids) >= total:
        print("Todas as questoes ja estao no Supabase!")
        return

    # Importar
    q_batch = []
    a_batch = []
    specialties = set()
    imported = 0
    skipped = 0

    print(f"\nImportando questoes...")
    with open(JSONL_PATH, "r", encoding="utf-8") as f, \
         tqdm(total=total, unit="q") as pbar:
        for line in f:
            line = line.strip()
            if not line:
                continue

            try:
                raw = json.loads(line)
            except json.JSONDecodeError:
                pbar.update(1)
                continue

            qid = raw.get("id", "")
            if qid in existing_ids:
                skipped += 1
                pbar.update(1)
                continue

            q_row, alt_rows = transform_question(raw)
            q_batch.append(q_row)
            a_batch.extend(alt_rows)

            # Coletar especialidades
            for t in q_row["topics"]:
                if t.get("n"):
                    specialties.add(t["n"])

            if len(q_batch) >= BATCH_SIZE:
                try:
                    sb.table("questions").upsert(q_batch).execute()
                    sb.table("alternatives").upsert(a_batch, on_conflict="question_id,letter").execute()
                except Exception as e:
                    # Tentar inserir um por um pra nao perder o batch inteiro
                    for qr in q_batch:
                        try:
                            sb.table("questions").upsert([qr]).execute()
                        except Exception:
                            pass
                    for ar in a_batch:
                        try:
                            sb.table("alternatives").upsert([ar], on_conflict="question_id,letter").execute()
                        except Exception:
                            pass

                imported += len(q_batch)
                pbar.update(len(q_batch))
                q_batch = []
                a_batch = []

        # Flush remaining
        if q_batch:
            try:
                sb.table("questions").upsert(q_batch).execute()
                sb.table("alternatives").upsert(a_batch, on_conflict="question_id,letter").execute()
            except Exception:
                for qr in q_batch:
                    try:
                        sb.table("questions").upsert([qr]).execute()
                    except Exception:
                        pass
            imported += len(q_batch)
            pbar.update(len(q_batch))

    # Importar especialidades
    print(f"\nImportando {len(specialties)} especialidades...")
    spec_batch = [{"name": s} for s in sorted(specialties)]
    for i in range(0, len(spec_batch), BATCH_SIZE):
        chunk = spec_batch[i:i + BATCH_SIZE]
        try:
            sb.table("specialties").upsert(chunk).execute()
        except Exception:
            pass

    print(f"\nConcluido!")
    print(f"  Importadas: {imported}")
    print(f"  Puladas (ja existiam): {skipped}")
    print(f"  Especialidades: {len(specialties)}")


if __name__ == "__main__":
    main()

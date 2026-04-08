import json
import os
import sqlite3

# Catalog IDs conhecidos
CATALOG_INSTITUTION = "63b07b3e-c200-4b3d-b9e6-742a096ae26e"
CATALOG_BANCA = "5d401e50-47cf-4d06-9a2f-19997cd0f258"
CATALOG_FINALIDADE = "4383bd62-e829-491e-8bb5-b40bd649817f"

DB_PATH = "data/questoes.db"


def _catalog_name(exam: dict, catalog_id: str) -> str:
    catalogs = exam.get("catalogs", {})
    entry = catalogs.get(catalog_id, {})
    return entry.get("name", "") if isinstance(entry, dict) else ""


def create_db(db_path: str = DB_PATH) -> sqlite3.Connection:
    """Cria banco SQLite com schema otimizado."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")

    conn.executescript("""
        CREATE TABLE questions (
            id TEXT PRIMARY KEY,
            statement TEXT,
            answer_type TEXT,
            year INTEGER,
            institution TEXT,
            banca TEXT,
            finalidade TEXT,
            region TEXT,
            labels TEXT,
            topics TEXT,
            correct_letter TEXT,
            solution TEXT,
            has_video INTEGER,
            video_url TEXT
        );

        CREATE TABLE alternatives (
            question_id TEXT,
            letter TEXT,
            body TEXT,
            correct INTEGER,
            answer_pct INTEGER,
            FOREIGN KEY (question_id) REFERENCES questions(id)
        );

        CREATE TABLE specialties (
            name TEXT PRIMARY KEY
        );

        CREATE TABLE topics (
            path TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            parent_path TEXT,
            depth INTEGER NOT NULL
        );

        CREATE INDEX idx_topics_parent ON topics(parent_path);
        CREATE INDEX idx_topics_depth ON topics(depth);

        CREATE INDEX idx_q_type ON questions(answer_type);
        CREATE INDEX idx_q_year ON questions(year);
        CREATE INDEX idx_q_institution ON questions(institution);
        CREATE INDEX idx_q_region ON questions(region);
        CREATE INDEX idx_q_finalidade ON questions(finalidade);
        CREATE INDEX idx_q_banca ON questions(banca);
        CREATE INDEX idx_alt_qid ON alternatives(question_id);
    """)
    return conn


def insert_question(conn: sqlite3.Connection, q: dict):
    """Insere uma questao e suas alternativas no banco."""
    exam = q.get("exams", [{}])[0] if q.get("exams") else {}
    inst = _catalog_name(exam, CATALOG_INSTITUTION)
    banca = _catalog_name(exam, CATALOG_BANCA)
    finalidade = _catalog_name(exam, CATALOG_FINALIDADE)
    year = exam.get("year", 0)

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

    conn.execute(
        """INSERT OR IGNORE INTO questions
        (id, statement, answer_type, year, institution, banca, finalidade,
         region, labels, topics, correct_letter, solution, has_video, video_url)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            q.get("id", ""),
            q.get("statement", ""),
            q.get("answer_type", ""),
            year,
            inst,
            banca,
            finalidade,
            region,
            json.dumps(labels, ensure_ascii=False),
            json.dumps(topics, ensure_ascii=False),
            correct_letter,
            sol_text,
            1 if q.get("has_video_solution") else 0,
            q.get("solution_video_url", "") or "",
        ),
    )

    for a in alternatives:
        if not isinstance(a, dict):
            continue
        pos = int(a.get("position", 0))
        conn.execute(
            "INSERT INTO alternatives (question_id, letter, body, correct, answer_pct) VALUES (?,?,?,?,?)",
            (
                q.get("id", ""),
                chr(65 + pos),
                a.get("body", ""),
                1 if a.get("correct") else 0,
                a.get("answer_percentage", 0),
            ),
        )


def build_from_jsonl(jsonl_path: str, db_path: str = DB_PATH) -> int:
    """Constroi banco SQLite a partir do JSONL. Retorna contagem."""
    conn = create_db(db_path)
    count = 0

    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                q = json.loads(line)
                insert_question(conn, q)
                count += 1
                if count % 10000 == 0:
                    conn.commit()
                    print(f"  {count} questoes inseridas...", end="\r")
            except (json.JSONDecodeError, Exception) as e:
                if count < 5:
                    print(f"  Aviso: erro na questao {count}: {e}")
                continue

    conn.commit()

    # Popular tabela de especialidades
    print(f"\n  Extraindo especialidades...")
    rows = conn.execute("SELECT DISTINCT topics FROM questions WHERE topics != '[]'").fetchall()
    specs = set()
    topic_rows = []
    for r in rows:
        try:
            for t in json.loads(r[0]):
                name = (t.get("n") or "").strip()
                path = (t.get("p") or "").strip()
                if name:
                    specs.add(name)
                if name and path:
                    depth = path.count("[$$]")
                    parent = path.rsplit("[$$]", 1)[0] if "[$$]" in path else None
                    topic_rows.append((path, name, parent, depth))
        except json.JSONDecodeError:
            pass
    for name in specs:
        conn.execute("INSERT OR IGNORE INTO specialties (name) VALUES (?)", (name,))
    if topic_rows:
        conn.executemany(
            "INSERT OR IGNORE INTO topics (path, name, parent_path, depth) VALUES (?,?,?,?)",
            topic_rows,
        )
    conn.commit()
    print(f"  {len(specs)} especialidades inseridas.")

    # Otimizar pra leitura
    conn.execute("ANALYZE")
    conn.execute("VACUUM")
    conn.close()

    size_mb = os.path.getsize(db_path) / (1024 * 1024)
    print(f"  {count} questoes -> {db_path} ({size_mb:.1f} MB)")
    return count


def get_filter_values(db_path: str = DB_PATH) -> dict:
    """Extrai valores unicos dos filtros do banco."""
    conn = sqlite3.connect(db_path)
    vals = {}
    for col in ["answer_type", "year", "institution", "banca", "finalidade", "region"]:
        rows = conn.execute(f"SELECT DISTINCT {col} FROM questions WHERE {col} != '' ORDER BY {col}").fetchall()
        vals[col] = [r[0] for r in rows]

    # Topics do JSON
    rows = conn.execute("SELECT DISTINCT topics FROM questions WHERE topics != '[]'").fetchall()
    specs = set()
    for r in rows:
        try:
            for t in json.loads(r[0]):
                if t.get("n"):
                    specs.add(t["n"])
        except json.JSONDecodeError:
            pass
    vals["specialties"] = sorted(specs)
    conn.close()
    return vals

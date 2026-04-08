import { getDb } from "./db";
import type { Filters, Question, Alternative, FilterValues, TopicNode } from "./types";

export const PER_PAGE = 50;

interface QuestionRow {
  id: string;
  statement: string;
  answer_type: string;
  year: number | null;
  institution: string;
  banca: string;
  finalidade: string;
  region: string;
  labels: string;
  topics: string;
  correct_letter: string;
  solution: string;
  has_video: number;
  video_url: string;
}

interface AltRow {
  question_id: string;
  letter: string;
  body: string;
  correct: number;
  answer_pct: number;
}

function buildWhere(filters: Filters): { where: string; params: unknown[] } {
  const clauses: string[] = [];
  const params: unknown[] = [];

  if (filters.search) {
    clauses.push("statement LIKE ?");
    params.push(`%${filters.search}%`);
  }
  if (filters.years?.length) {
    clauses.push(`year IN (${filters.years.map(() => "?").join(",")})`);
    params.push(...filters.years);
  }
  if (filters.institutions?.length) {
    clauses.push(
      `institution IN (${filters.institutions.map(() => "?").join(",")})`
    );
    params.push(...filters.institutions);
  }
  if (filters.finalidades?.length) {
    clauses.push(
      `finalidade IN (${filters.finalidades.map(() => "?").join(",")})`
    );
    params.push(...filters.finalidades);
  }
  if (filters.bancas?.length) {
    clauses.push(`banca IN (${filters.bancas.map(() => "?").join(",")})`);
    params.push(...filters.bancas);
  }
  if (filters.regions?.length) {
    clauses.push(`region IN (${filters.regions.map(() => "?").join(",")})`);
    params.push(...filters.regions);
  }
  if (filters.types?.length) {
    clauses.push(
      `answer_type IN (${filters.types.map(() => "?").join(",")})`
    );
    params.push(...filters.types);
  }
  if (filters.specialties?.length) {
    const specClauses = filters.specialties.map(() => "topics LIKE ?");
    clauses.push(`(${specClauses.join(" OR ")})`);
    filters.specialties.forEach((s) => params.push(`%"n":"${s}"%`));
  }
  if (filters.showOutdated === false) {
    clauses.push("labels NOT LIKE '%OUTDATED%'");
  }
  if (filters.showCanceled === false) {
    clauses.push("labels NOT LIKE '%CANCELED%'");
  }

  const where = clauses.length ? "WHERE " + clauses.join(" AND ") : "";
  return { where, params };
}

export function fetchQuestions(
  filters: Filters
): { data: Question[]; count: number } {
  const db = getDb();
  const page = filters.page || 1;
  const offset = (page - 1) * PER_PAGE;
  const { where, params } = buildWhere(filters);

  // Count
  const countRow = db
    .prepare(`SELECT COUNT(*) as cnt FROM questions ${where}`)
    .get(...params) as { cnt: number };
  const count = countRow?.cnt || 0;

  // Fetch questions
  const rows = db
    .prepare(
      `SELECT * FROM questions ${where} ORDER BY ROWID LIMIT ? OFFSET ?`
    )
    .all(...params, PER_PAGE, offset) as QuestionRow[];

  if (rows.length === 0) {
    return { data: [], count };
  }

  // Fetch alternatives for all questions in one query
  const ids = rows.map((r) => r.id);
  const placeholders = ids.map(() => "?").join(",");
  const altRows = db
    .prepare(
      `SELECT * FROM alternatives WHERE question_id IN (${placeholders}) ORDER BY letter`
    )
    .all(...ids) as AltRow[];

  // Group alternatives by question
  const altMap = new Map<string, Alternative[]>();
  for (const a of altRows) {
    const list = altMap.get(a.question_id) || [];
    list.push({
      id: 0,
      question_id: a.question_id,
      letter: a.letter,
      body: a.body,
      correct: !!a.correct,
      answer_pct: a.answer_pct,
    });
    altMap.set(a.question_id, list);
  }

  const data: Question[] = rows.map((r) => ({
    id: r.id,
    statement: r.statement,
    answer_type: r.answer_type,
    year: r.year,
    institution: r.institution,
    banca: r.banca,
    finalidade: r.finalidade,
    region: r.region,
    labels: JSON.parse(r.labels || "[]"),
    topics: JSON.parse(r.topics || "[]"),
    correct_letter: r.correct_letter,
    solution: r.solution,
    has_video: !!r.has_video,
    video_url: r.video_url,
    alternatives: altMap.get(r.id) || [],
  }));

  return { data, count };
}

export function fetchFilterValues(): FilterValues {
  const db = getDb();

  const distinct = (col: string) =>
    (
      db
        .prepare(
          `SELECT DISTINCT ${col} FROM questions WHERE ${col} != '' AND ${col} IS NOT NULL ORDER BY ${col}`
        )
        .all() as Record<string, string>[]
    ).map((r) => r[col]);

  const years = (
    db
      .prepare(
        "SELECT DISTINCT year FROM questions WHERE year IS NOT NULL ORDER BY year DESC"
      )
      .all() as { year: number }[]
  ).map((r) => r.year);

  // Specialties from dedicated table (fast!)
  const specialties = (
    db.prepare("SELECT name FROM specialties ORDER BY name").all() as {
      name: string;
    }[]
  ).map((r) => r.name);

  let topicsTree: TopicNode[] | undefined = undefined;
  try {
    const rows = db
      .prepare(
        "SELECT path, name, parent_path, depth FROM topics ORDER BY depth, name"
      )
      .all() as { path: string; name: string; parent_path: string | null; depth: number }[];

    const byPath = new Map<string, TopicNode & { parent_path: string | null }>();
    for (const r of rows) {
      byPath.set(r.path, { name: r.name, path: r.path, children: [], parent_path: r.parent_path });
    }

    const roots: TopicNode[] = [];
    for (const node of byPath.values()) {
      if (node.parent_path && byPath.has(node.parent_path)) {
        byPath.get(node.parent_path)!.children.push(node);
      } else {
        roots.push(node);
      }
    }

    const sort = (nodes: TopicNode[]) => {
      nodes.sort((a, b) => a.name.localeCompare(b.name, "pt-BR"));
      nodes.forEach((n) => sort(n.children));
    };
    sort(roots);
    topicsTree = roots;
  } catch {
    topicsTree = undefined;
  }

  return {
    specialties,
    topicsTree,
    institutions: distinct("institution"),
    years,
    finalidades: distinct("finalidade"),
    bancas: distinct("banca"),
    regions: distinct("region"),
  };
}

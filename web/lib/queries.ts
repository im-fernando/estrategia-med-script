import { supabase } from "./supabase";
import type { Filters, Question, FilterValues } from "./types";

const PER_PAGE = 50;

export async function fetchQuestions(
  filters: Filters
): Promise<{ data: Question[]; count: number }> {
  const page = filters.page || 1;
  const offset = (page - 1) * PER_PAGE;

  let query = supabase
    .from("questions")
    .select("*, alternatives(*)", { count: "exact" })
    .order("id")
    .range(offset, offset + PER_PAGE - 1);

  if (filters.search) {
    query = query.ilike("statement", `%${filters.search}%`);
  }
  if (filters.years?.length) {
    query = query.in("year", filters.years);
  }
  if (filters.institutions?.length) {
    query = query.in("institution", filters.institutions);
  }
  if (filters.finalidades?.length) {
    query = query.in("finalidade", filters.finalidades);
  }
  if (filters.bancas?.length) {
    query = query.in("banca", filters.bancas);
  }
  if (filters.regions?.length) {
    query = query.in("region", filters.regions);
  }
  if (filters.types?.length) {
    query = query.in("answer_type", filters.types);
  }
  if (filters.specialties?.length) {
    const conditions = filters.specialties
      .map((s) => `topics.cs.[{"n":"${s}"}]`)
      .join(",");
    query = query.or(conditions);
  }
  if (filters.showOutdated === false) {
    query = query.not("labels", "cs", '["OUTDATED"]');
  }
  if (filters.showCanceled === false) {
    query = query.not("labels", "cs", '["CANCELED"]');
  }

  const { data, count, error } = await query;
  if (error) throw error;

  // Sort alternatives by letter
  const questions = (data || []).map((q: Question) => ({
    ...q,
    alternatives: (q.alternatives || []).sort((a, b) =>
      a.letter.localeCompare(b.letter)
    ),
  }));

  return { data: questions, count: count || 0 };
}

export async function fetchFilterValues(): Promise<FilterValues> {
  const [specRes, instRes, yearRes, finRes, bancaRes, regRes] =
    await Promise.all([
      supabase.from("specialties").select("name").order("name"),
      supabase.from("questions").select("institution").neq("institution", ""),
      supabase.from("questions").select("year").not("year", "is", null),
      supabase.from("questions").select("finalidade").neq("finalidade", ""),
      supabase.from("questions").select("banca").neq("banca", ""),
      supabase.from("questions").select("region").neq("region", ""),
    ]);

  const unique = (rows: { [key: string]: string }[] | null, key: string) =>
    [...new Set((rows || []).map((r) => r[key]))].sort();

  const uniqueNums = (rows: { [key: string]: number }[] | null, key: string) =>
    [...new Set((rows || []).map((r) => r[key]))]
      .sort((a, b) => b - a);

  return {
    specialties: (specRes.data || []).map((r) => r.name),
    institutions: unique(instRes.data, "institution"),
    years: uniqueNums(yearRes.data, "year"),
    finalidades: unique(finRes.data, "finalidade"),
    bancas: unique(bancaRes.data, "banca"),
    regions: unique(regRes.data, "region"),
  };
}

export { PER_PAGE };

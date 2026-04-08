"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { Header } from "@/components/Header";
import { Filters } from "@/components/Filters";
import { QuestionCard } from "@/components/QuestionCard";
import { Pagination } from "@/components/Pagination";
import { useAnswers } from "@/hooks/useAnswers";
import type { Question, FilterValues, Filters as FiltersType } from "@/lib/types";

const PER_PAGE = 50;

function filtersToParams(filters: FiltersType): string {
  const sp = new URLSearchParams();
  sp.set("page", String(filters.page || 1));
  if (filters.search) sp.set("search", filters.search);
  if (filters.specialties?.length) sp.set("specialties", filters.specialties.join(","));
  if (filters.institutions?.length) sp.set("institutions", filters.institutions.join(","));
  if (filters.years?.length) sp.set("years", filters.years.join(","));
  if (filters.finalidades?.length) sp.set("finalidades", filters.finalidades.join(","));
  if (filters.bancas?.length) sp.set("bancas", filters.bancas.join(","));
  if (filters.regions?.length) sp.set("regions", filters.regions.join(","));
  if (filters.types?.length) sp.set("types", filters.types.join(","));
  if (filters.showOutdated === false) sp.set("showOutdated", "false");
  if (filters.showCanceled === false) sp.set("showCanceled", "false");
  return sp.toString();
}

export default function Home() {
  const [mounted, setMounted] = useState(false);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [filterValues, setFilterValues] = useState<FilterValues | null>(null);
  const [filters, setFilters] = useState<FiltersType>({
    page: 1,
    types: ["MULTIPLE_CHOICE", "MULTIPLE_CHOICE_FOUR", "TRUE_OR_FALSE", "DISCURSIVE"],
  });
  const [loading, setLoading] = useState(true);
  const { answers, save, clear, stats } = useAnswers();
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  useEffect(() => setMounted(true), []);

  // Load filter values once
  useEffect(() => {
    fetch("/api/filters")
      .then((r) => r.json())
      .then(setFilterValues)
      .catch(console.error);
  }, []);

  // Load questions when filters change
  useEffect(() => {
    let cancelled = false;
    fetch(`/api/questions?${filtersToParams(filters)}`)
      .then((r) => r.json())
      .then(({ data, count }: { data: Question[]; count: number }) => {
        if (cancelled) return;
        setQuestions(data);
        setTotalCount(count);
        setLoading(false);
      })
      .catch((err) => {
        if (cancelled) return;
        console.error(err);
        setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [filters]);

  const handleFilterChange = useCallback((newFilters: FiltersType) => {
    if (debounceRef.current) clearTimeout(debounceRef.current);

    if (newFilters.search !== undefined) {
      debounceRef.current = setTimeout(() => {
        setLoading(true);
        setFilters(newFilters);
      }, 400);
    } else {
      setLoading(true);
      setFilters(newFilters);
    }
  }, []);

  const handlePageChange = useCallback((page: number) => {
    setLoading(true);
    setFilters((prev) => ({ ...prev, page }));
    window.scrollTo(0, 0);
  }, []);

  const totalPages = Math.ceil(totalCount / PER_PAGE);
  const currentPage = filters.page || 1;

  if (!mounted) {
    return (
      <div className="container" style={{ textAlign: "center", paddingTop: "100px", color: "#888" }}>
        Carregando...
      </div>
    );
  }

  return (
    <div className="container">
      <Header total={totalCount} filtered={totalCount} stats={stats} />

      {filterValues && (
        <Filters
          filterValues={filterValues}
          filters={filters}
          onChange={handleFilterChange}
        />
      )}

      <Pagination
        currentPage={currentPage}
        totalPages={totalPages}
        onPageChange={handlePageChange}
      />

      <div className="min-h-[200px]">
        {loading ? (
          <div className="text-center py-16 text-muted">
            Carregando questoes...
          </div>
        ) : questions.length === 0 ? (
          <div className="text-center py-16 text-muted">
            Nenhuma questao encontrada com esses filtros.
          </div>
        ) : (
          questions.map((q, i) => (
            <QuestionCard
              key={q.id}
              question={q}
              index={(currentPage - 1) * PER_PAGE + i}
              savedAnswer={answers[q.id]}
              onAnswer={save}
              onClear={clear}
            />
          ))
        )}
      </div>

      <Pagination
        currentPage={currentPage}
        totalPages={totalPages}
        onPageChange={handlePageChange}
      />
    </div>
  );
}

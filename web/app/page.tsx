"use client";

export const dynamic = "force-dynamic";

import { useEffect, useState, useCallback, useRef } from "react";
import { Header } from "@/components/Header";
import { Filters } from "@/components/Filters";
import { QuestionCard } from "@/components/QuestionCard";
import { Pagination } from "@/components/Pagination";
import { useAnswers } from "@/hooks/useAnswers";
import { fetchQuestions, fetchFilterValues, PER_PAGE } from "@/lib/queries";
import type { Question, FilterValues, Filters as FiltersType } from "@/lib/types";

export default function Home() {
  const [questions, setQuestions] = useState<Question[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [filterValues, setFilterValues] = useState<FilterValues | null>(null);
  const [filters, setFilters] = useState<FiltersType>({
    page: 1,
    types: ["MULTIPLE_CHOICE", "TRUE_OR_FALSE", "DISCURSIVE"],
  });
  const [loading, setLoading] = useState(true);
  const { answers, save, clear, stats } = useAnswers();
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  // Load filter values once
  useEffect(() => {
    fetchFilterValues().then(setFilterValues).catch(console.error);
  }, []);

  // Load questions when filters change
  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    fetchQuestions(filters)
      .then(({ data, count }) => {
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
    // Debounce text search
    if (debounceRef.current) clearTimeout(debounceRef.current);

    if (newFilters.search !== undefined) {
      debounceRef.current = setTimeout(() => {
        setFilters(newFilters);
      }, 400);
    } else {
      setFilters(newFilters);
    }
  }, []);

  const handlePageChange = useCallback(
    (page: number) => {
      setFilters((prev) => ({ ...prev, page }));
      window.scrollTo(0, 0);
    },
    []
  );

  const totalPages = Math.ceil(totalCount / PER_PAGE);
  const currentPage = filters.page || 1;

  return (
    <div className="max-w-[1100px] mx-auto p-5">
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

"use client";
import { useState, useEffect, useCallback } from "react";
import type { SavedAnswer } from "@/lib/types";

const STORAGE_KEY = "em_ans";

type Answers = Record<string, SavedAnswer>;

export function useAnswers() {
  const [answers, setAnswers] = useState<Answers>({});

  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) setAnswers(JSON.parse(raw));
    } catch {}
  }, []);

  const save = useCallback((id: string, letter: string, correct: boolean) => {
    setAnswers((prev) => {
      const next = { ...prev, [id]: { s: letter, c: correct } };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      return next;
    });
  }, []);

  const clear = useCallback((id: string) => {
    setAnswers((prev) => {
      const next = { ...prev };
      delete next[id];
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      return next;
    });
  }, []);

  const clearAll = useCallback(() => {
    setAnswers({});
    localStorage.removeItem(STORAGE_KEY);
  }, []);

  const stats = {
    correct: Object.values(answers).filter((a) => a.c).length,
    wrong: Object.values(answers).filter((a) => !a.c).length,
  };
  const total = stats.correct + stats.wrong;
  const pct = total > 0 ? Math.round((stats.correct / total) * 100) : 0;

  return { answers, save, clear, clearAll, stats: { ...stats, total, pct } };
}

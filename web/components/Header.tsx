"use client";

interface HeaderProps {
  total: number;
  filtered: number;
  stats: { correct: number; wrong: number; pct: number };
}

export function Header({ total, filtered, stats }: HeaderProps) {
  return (
    <div className="text-center mb-7 p-7 bg-gradient-to-br from-card to-[#1f2937] rounded-2xl border border-border">
      <h1 className="text-2xl font-bold mb-2 bg-gradient-to-r from-accent to-accent-light bg-clip-text text-transparent">
        Estrategia Med
      </h1>
      <p className="text-muted text-sm">
        {total.toLocaleString()} questoes no banco
      </p>
      <div className="flex justify-center gap-7 mt-5 flex-wrap">
        <div className="text-center">
          <div className="text-2xl font-bold text-accent">
            {filtered.toLocaleString()}
          </div>
          <div className="text-xs text-muted">Exibindo</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-correct">
            {stats.correct}
          </div>
          <div className="text-xs text-muted">Acertos</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-incorrect">
            {stats.wrong}
          </div>
          <div className="text-xs text-muted">Erros</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-yellow-400">
            {stats.pct > 0 ? `${stats.pct}%` : "-"}
          </div>
          <div className="text-xs text-muted">Aproveit.</div>
        </div>
      </div>
    </div>
  );
}

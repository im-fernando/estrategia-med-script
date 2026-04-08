"use client";

interface HeaderProps {
  total: number;
  filtered: number;
  stats: { correct: number; wrong: number; pct: number };
}

export function Header({ total, filtered, stats }: HeaderProps) {
  return (
    <header className="header">
      <h1>📚 Estrategia Med — Questoes</h1>
      <p>{total.toLocaleString()} questoes no banco</p>
      <div className="stats">
        <div className="stat">
          <div className="stat-value">{filtered.toLocaleString()}</div>
          <div className="stat-label">Exibindo</div>
        </div>
        <div className="stat">
          <div className="stat-value" style={{ color: "var(--color-correct)" }}>
            {stats.correct}
          </div>
          <div className="stat-label">Acertos</div>
        </div>
        <div className="stat">
          <div
            className="stat-value"
            style={{ color: "var(--color-incorrect)" }}
          >
            {stats.wrong}
          </div>
          <div className="stat-label">Erros</div>
        </div>
        <div className="stat">
          <div className="stat-value" style={{ color: "#fbbf24" }}>
            {stats.pct > 0 ? `${stats.pct}%` : "-"}
          </div>
          <div className="stat-label">Aproveitamento</div>
        </div>
      </div>
    </header>
  );
}

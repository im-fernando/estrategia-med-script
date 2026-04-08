"use client";

interface PaginationProps {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}

export function Pagination({
  currentPage,
  totalPages,
  onPageChange,
}: PaginationProps) {
  if (totalPages <= 1) return null;

  const maxButtons = 7;
  let start = Math.max(1, currentPage - Math.floor(maxButtons / 2));
  let end = Math.min(totalPages, start + maxButtons - 1);
  if (end - start < maxButtons - 1)
    start = Math.max(1, end - maxButtons + 1);

  const pages = [];
  for (let i = start; i <= end; i++) pages.push(i);

  const btn =
    "px-3 py-1.5 border border-border bg-card rounded-lg cursor-pointer text-xs transition-all hover:bg-hover";
  const active = "bg-accent text-dark border-accent font-bold";

  return (
    <div className="flex justify-center gap-1 my-4 flex-wrap">
      {currentPage > 1 && (
        <>
          <button onClick={() => onPageChange(1)} className={btn}>
            &laquo;
          </button>
          <button
            onClick={() => onPageChange(currentPage - 1)}
            className={btn}
          >
            &lsaquo;
          </button>
        </>
      )}
      {pages.map((p) => (
        <button
          key={p}
          onClick={() => onPageChange(p)}
          className={`${btn} ${p === currentPage ? active : ""}`}
        >
          {p}
        </button>
      ))}
      {currentPage < totalPages && (
        <>
          <button
            onClick={() => onPageChange(currentPage + 1)}
            className={btn}
          >
            &rsaquo;
          </button>
          <button onClick={() => onPageChange(totalPages)} className={btn}>
            &raquo;
          </button>
        </>
      )}
    </div>
  );
}

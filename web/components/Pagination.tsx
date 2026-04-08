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
  const end = Math.min(totalPages, start + maxButtons - 1);
  if (end - start < maxButtons - 1)
    start = Math.max(1, end - maxButtons + 1);

  const pages = [];
  for (let i = start; i <= end; i++) pages.push(i);

  return (
    <div className="pagination">
      {currentPage > 1 && (
        <>
          <button
            type="button"
            onClick={() => onPageChange(1)}
            className="page-btn"
          >
            &laquo;
          </button>
          <button
            type="button"
            onClick={() => onPageChange(currentPage - 1)}
            className="page-btn"
          >
            &lsaquo;
          </button>
        </>
      )}
      {pages.map((p) => (
        <button
          type="button"
          key={p}
          onClick={() => onPageChange(p)}
          className={`page-btn ${p === currentPage ? "active" : ""}`}
        >
          {p}
        </button>
      ))}
      {currentPage < totalPages && (
        <>
          <button
            type="button"
            onClick={() => onPageChange(currentPage + 1)}
            className="page-btn"
          >
            &rsaquo;
          </button>
          <button
            type="button"
            onClick={() => onPageChange(totalPages)}
            className="page-btn"
          >
            &raquo;
          </button>
        </>
      )}
    </div>
  );
}

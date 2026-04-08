"use client";
import { useCallback, useState } from "react";
import type { FilterValues, Filters } from "@/lib/types";

interface FiltersProps {
  filterValues: FilterValues;
  filters: Filters;
  onChange: (f: Filters) => void;
}

function CheckboxList({
  items,
  selected,
  onToggle,
  label,
}: {
  items: string[];
  selected: string[];
  onToggle: (items: string[]) => void;
  label: string;
}) {
  const [search, setSearch] = useState("");
  const filtered = search
    ? items.filter((i) => i.toLowerCase().includes(search.toLowerCase()))
    : items;

  return (
    <div className="filter-group" style={{ gridColumn: "1 / -1" }}>
      <label>{label}</label>
      <div className="tree-filter-scroll">
        {items.length > 10 && (
          <div style={{ padding: "0 0 6px 0" }}>
            <div className="search-box">
              <span className="search-icon">🔎</span>
              <input
                type="text"
                placeholder="Buscar..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="search-input"
              />
            </div>
          </div>
        )}
        {filtered.map((item) => (
          <div className="tree-leaf" key={item}>
            <label className="tree-label">
              <input
                type="checkbox"
                checked={selected.includes(item)}
                onChange={() => {
                  const next = selected.includes(item)
                    ? selected.filter((s) => s !== item)
                    : [...selected, item];
                  onToggle(next);
                }}
                className="em-checkbox"
              />
              <span className="tree-name">{item}</span>
            </label>
          </div>
        ))}
        {filtered.length === 0 && (
          <div className="tree-leaf">
            <span className="tree-label" style={{ cursor: "default" }}>
              <span className="tree-name" style={{ color: "var(--color-muted)" }}>
                Nenhum item encontrado
              </span>
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

export function Filters({ filterValues, filters, onChange }: FiltersProps) {
  const [open, setOpen] = useState(false);

  const update = useCallback(
    (partial: Partial<Filters>) => {
      onChange({ ...filters, ...partial, page: 1 });
    },
    [filters, onChange]
  );

  const types = filters.types || [
    "MULTIPLE_CHOICE",
    "MULTIPLE_CHOICE_FOUR",
    "TRUE_OR_FALSE",
    "DISCURSIVE",
  ];

  return (
    <section className="filters-section">
      <div className="filters-header" onClick={() => setOpen(!open)}>
        <h3>🔍 Filtros e busca</h3>
        <span className="filters-toggle">
          {open ? "▲ Recolher" : "▼ Expandir"}
        </span>
      </div>

      <div className={`filters-content ${open ? "is-open" : ""}`}>
        <div className="filter-group" style={{ gridColumn: "1 / -1" }}>
          <label>Buscar no enunciado</label>
          <div className="search-box">
            <span className="search-icon">🔎</span>
            <input
              type="text"
              className="search-input"
              placeholder="Digite palavras-chave..."
              value={filters.search || ""}
              onChange={(e) => update({ search: e.target.value })}
            />
          </div>
        </div>

        <CheckboxList
          label="Especialidade"
          items={filterValues.specialties}
          selected={filters.specialties || []}
          onToggle={(v) => update({ specialties: v })}
        />
        <CheckboxList
          label="Instituicao"
          items={filterValues.institutions}
          selected={filters.institutions || []}
          onToggle={(v) => update({ institutions: v })}
        />
        <CheckboxList
          label="Ano"
          items={filterValues.years.map(String)}
          selected={(filters.years || []).map(String)}
          onToggle={(v) => update({ years: v.map(Number) })}
        />
        <CheckboxList
          label="Finalidade"
          items={filterValues.finalidades}
          selected={filters.finalidades || []}
          onToggle={(v) => update({ finalidades: v })}
        />
        <CheckboxList
          label="Banca"
          items={filterValues.bancas}
          selected={filters.bancas || []}
          onToggle={(v) => update({ bancas: v })}
        />
        <CheckboxList
          label="Regiao"
          items={filterValues.regions}
          selected={filters.regions || []}
          onToggle={(v) => update({ regions: v })}
        />

        <div className="filter-group">
          <label>Tipo de questao</label>
          <div className="tree-filter-scroll">
            {[
              { value: "MULTIPLE_CHOICE", label: "Multipla Escolha (5)" },
              { value: "MULTIPLE_CHOICE_FOUR", label: "Multipla Escolha (4)" },
              { value: "TRUE_OR_FALSE", label: "Certo/Errado" },
              { value: "DISCURSIVE", label: "Discursiva" },
            ].map((t) => (
              <div className="tree-leaf" key={t.value}>
                <label className="tree-label">
                  <input
                    type="checkbox"
                    checked={types.includes(t.value)}
                    onChange={() => {
                      const next = types.includes(t.value)
                        ? types.filter((x) => x !== t.value)
                        : [...types, t.value];
                      update({ types: next });
                    }}
                    className="em-checkbox"
                  />
                  <span className="tree-name">{t.label}</span>
                </label>
              </div>
            ))}
          </div>
        </div>

        <div className="filter-group">
          <label>Vigencia</label>
          <div className="tree-filter-scroll">
            <div className="tree-leaf">
              <label className="tree-label">
                <input
                  type="checkbox"
                  checked={filters.showOutdated !== false}
                  onChange={() =>
                    update({ showOutdated: filters.showOutdated === false })
                  }
                  className="em-checkbox"
                />
                <span className="tree-name">Desatualizadas</span>
              </label>
            </div>
            <div className="tree-leaf">
              <label className="tree-label">
                <input
                  type="checkbox"
                  checked={filters.showCanceled !== false}
                  onChange={() =>
                    update({ showCanceled: filters.showCanceled === false })
                  }
                  className="em-checkbox"
                />
                <span className="tree-name">Anuladas</span>
              </label>
            </div>
          </div>
        </div>

        <div className="filter-actions" style={{ gridColumn: "1 / -1" }}>
          <button
            type="button"
            className="clear-filters"
            onClick={() =>
              onChange({
                page: 1,
                types: [
                  "MULTIPLE_CHOICE",
                  "MULTIPLE_CHOICE_FOUR",
                  "TRUE_OR_FALSE",
                  "DISCURSIVE",
                ],
              })
            }
          >
            Limpar filtros
          </button>
        </div>
      </div>

    </section>
  );
}

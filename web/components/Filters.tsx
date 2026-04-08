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
    <details className="group">
      <summary className="text-xs font-semibold text-muted cursor-pointer py-1.5 select-none flex items-center gap-1">
        <span className="group-open:rotate-90 transition-transform text-[10px]">
          &#9654;
        </span>
        {label}
        {selected.length > 0 && (
          <span className="ml-1 px-1.5 py-0.5 rounded-full bg-accent/20 text-accent text-[10px]">
            {selected.length}
          </span>
        )}
      </summary>
      <div className="mt-1">
        {items.length > 10 && (
          <input
            type="text"
            placeholder="Buscar..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full mb-1 px-2 py-1.5 bg-dark border border-border rounded-lg text-xs text-white placeholder:text-muted/60 focus:border-accent focus:outline-none"
          />
        )}
        <div className="max-h-40 overflow-y-auto border border-border rounded-lg p-1.5 bg-dark">
          {filtered.map((item) => (
            <label
              key={item}
              className="flex items-start gap-2 px-1.5 py-1 rounded-lg hover:bg-white/[.04] cursor-pointer text-xs"
            >
              <input
                type="checkbox"
                checked={selected.includes(item)}
                onChange={() => {
                  const next = selected.includes(item)
                    ? selected.filter((s) => s !== item)
                    : [...selected, item];
                  onToggle(next);
                }}
                className="accent-accent mt-0.5 w-3.5 h-3.5 flex-shrink-0"
              />
              <span className="text-white leading-tight">{item}</span>
            </label>
          ))}
          {filtered.length === 0 && (
            <p className="text-muted text-xs p-2">Nenhum item encontrado</p>
          )}
        </div>
      </div>
    </details>
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
    <div className="bg-card rounded-2xl p-5 mb-5 border border-border">
      <div
        className="flex justify-between items-center cursor-pointer select-none"
        onClick={() => setOpen(!open)}
      >
        <h3 className="text-accent font-semibold text-sm flex items-center gap-2">
          <span>&#9881;</span> Filtros
        </h3>
        <span className="text-muted text-xs">
          {open ? "▲ Recolher" : "▼ Expandir"}
        </span>
      </div>

      {open && (
        <div className="mt-5 space-y-4">
          {/* Busca */}
          <div>
            <input
              type="text"
              placeholder="🔎 Buscar no enunciado..."
              value={filters.search || ""}
              onChange={(e) => update({ search: e.target.value })}
              className="w-full px-4 py-3 bg-hover border border-border rounded-xl text-sm text-white placeholder:text-muted/60 focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/20"
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
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
          </div>

          {/* Tipo de questao */}
          <div>
            <p className="text-xs font-semibold text-muted mb-2">
              Tipo de questao
            </p>
            <div className="flex flex-wrap gap-3">
              {[
                { value: "MULTIPLE_CHOICE", label: "Multipla Escolha (5)" },
                { value: "MULTIPLE_CHOICE_FOUR", label: "Multipla Escolha (4)" },
                { value: "TRUE_OR_FALSE", label: "Certo/Errado" },
                { value: "DISCURSIVE", label: "Discursiva" },
              ].map((t) => (
                <label
                  key={t.value}
                  className="flex items-center gap-2 text-xs cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={types.includes(t.value)}
                    onChange={() => {
                      const next = types.includes(t.value)
                        ? types.filter((x) => x !== t.value)
                        : [...types, t.value];
                      update({ types: next });
                    }}
                    className="accent-accent w-3.5 h-3.5"
                  />
                  <span className="text-white">{t.label}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Vigencia */}
          <div className="flex flex-wrap gap-4">
            <label className="flex items-center gap-2 text-xs cursor-pointer">
              <input
                type="checkbox"
                checked={filters.showOutdated !== false}
                onChange={() =>
                  update({ showOutdated: filters.showOutdated === false })
                }
                className="accent-accent w-3.5 h-3.5"
              />
              <span className="text-white">Desatualizadas</span>
            </label>
            <label className="flex items-center gap-2 text-xs cursor-pointer">
              <input
                type="checkbox"
                checked={filters.showCanceled !== false}
                onChange={() =>
                  update({ showCanceled: filters.showCanceled === false })
                }
                className="accent-accent w-3.5 h-3.5"
              />
              <span className="text-white">Anuladas</span>
            </label>
          </div>

          <button
            onClick={() =>
              onChange({
                page: 1,
                types: ["MULTIPLE_CHOICE", "MULTIPLE_CHOICE_FOUR", "TRUE_OR_FALSE", "DISCURSIVE"],
              })
            }
            className="w-full mt-2 py-2 rounded-xl bg-incorrect/20 text-incorrect text-xs font-semibold hover:bg-incorrect/30 transition-colors"
          >
            Limpar Filtros
          </button>
        </div>
      )}
    </div>
  );
}

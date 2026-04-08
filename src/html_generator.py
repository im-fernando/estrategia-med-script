import html
import json
import os


def _escape(text):
    if not text:
        return ""
    return html.escape(str(text))


def _flat_has_parent_links(items: list[dict]) -> bool:
    return any(isinstance(t, dict) and t.get("_parent_id") is not None for t in items)


def _build_nested_tree(flat_items: list[dict]) -> list[dict]:
    """Monta arvore a partir de lista plana com id e _parent_id."""
    by_id: dict[str, dict] = {}
    for item in flat_items:
        tid = item.get("id")
        if not tid:
            continue
        tid_s = str(tid)
        by_id[tid_s] = {**item, "children": []}

    roots: list[dict] = []
    for item in flat_items:
        tid = item.get("id")
        if not tid or str(tid) not in by_id:
            continue
        node = by_id[str(tid)]
        pid = item.get("_parent_id")
        if pid is not None and str(pid) in by_id:
            by_id[str(pid)]["children"].append(node)
        else:
            roots.append(node)

    return roots


def _sort_tree_nodes(nodes: list[dict]) -> None:
    nodes.sort(key=lambda x: (x.get("name") or "").lower())
    for n in nodes:
        ch = n.get("children")
        if ch:
            _sort_tree_nodes(ch)


def _render_flat_topic_checkboxes(flat_items: list[dict], cb_class: str) -> str:
    rows = []
    for t in flat_items:
        name = t.get("name", "")
        if not name:
            continue
        depth = int(t.get("_depth", 0) or 0)
        esc = _escape(name)
        pad = min(depth, 12) * 10
        rows.append(
            f'<div class="tree-leaf tree-leaf-flat" style="padding-left:{pad}px">'
            f'<label class="tree-label"><input type="checkbox" class="{cb_class}" '
            f'value="{esc}" onchange="applyFilters()"><span class="tree-name">{esc}</span></label></div>'
        )
    return f'<div class="tree-flat-fallback">{"".join(rows)}</div>'


def _render_tree_accordion(nodes: list[dict], cb_class: str) -> str:
    """Renderiza nos como <details> aninhados (acordeao) com checkbox em cada nivel."""
    parts = []
    for node in nodes:
        name = node.get("name", "")
        if not name:
            continue
        esc = _escape(name)
        children = node.get("children") or []
        if children:
            inner = _render_tree_accordion(children, cb_class)
            parts.append(
                f'<details class="tree-node tree-branch">'
                f'<summary class="tree-summary" onclick="if(event.target.closest(\'.tree-label\')) event.preventDefault()">'
                f'<span class="tree-chevron" aria-hidden="true"></span>'
                f'<label class="tree-label" onclick="event.stopPropagation()">'
                f'<input type="checkbox" class="{cb_class}" value="{esc}" '
                f'onchange="event.stopPropagation(); applyFilters()">'
                f'<span class="tree-name">{esc}</span></label>'
                f"</summary>"
                f'<div class="tree-children">{inner}</div>'
                f"</details>"
            )
        else:
            parts.append(
                f'<div class="tree-node tree-leaf">'
                f'<label class="tree-label">'
                f'<input type="checkbox" class="{cb_class}" value="{esc}" onchange="applyFilters()">'
                f'<span class="tree-name">{esc}</span></label></div>'
            )
    return "".join(parts)


def _specialty_filter_markup(topics_tree: list[dict], specialty_names_fallback: list[str]) -> str:
    if topics_tree:
        if _flat_has_parent_links(topics_tree):
            nested = _build_nested_tree(topics_tree)
            _sort_tree_nodes(nested)
            body = _render_tree_accordion(nested, "filter-topic-cb")
        else:
            body = _render_flat_topic_checkboxes(topics_tree, "filter-topic-cb")
        return f'<div id="filter-specialty-tree" class="tree-filter-scroll" role="group" aria-label="Especialidades">{body}</div>'

    opts = "".join(
        f'<div class="tree-leaf"><label class="tree-label"><input type="checkbox" class="filter-topic-cb" '
        f'value="{_escape(s)}" onchange="applyFilters()"><span class="tree-name">{_escape(s)}</span></label></div>'
        for s in specialty_names_fallback
    )
    return f'<div id="filter-specialty-tree" class="tree-filter-scroll" role="group" aria-label="Especialidades">{opts}</div>'


def _region_filter_markup(region_items: list[dict], region_codes_fallback: list[str]) -> str:
    """Gera checkboxes de regiao. Cada item tem 'code' (sigla UF) e 'name' (ex: 'AC - Acre')."""
    items = region_items
    if not items:
        items = [{"code": c, "name": c} for c in region_codes_fallback]

    opts = "".join(
        f'<div class="tree-leaf"><label class="tree-label"><input type="checkbox" class="filter-region-cb" '
        f'value="{_escape(r.get("code", r.get("name", "")))}" onchange="applyFilters()">'
        f'<span class="tree-name">{_escape(r.get("name", r.get("code", "")))}</span></label></div>'
        for r in items
    )
    return f'<div id="filter-region-tree" class="tree-filter-scroll" role="group" aria-label="Regioes">{opts}</div>'


def _simple_checkbox_filter(names: list[str], tree_id: str, cb_class: str, aria_label: str) -> str:
    """Lista plana de checkboxes no mesmo bloco visual da arvore de regiao."""
    rows = []
    for s in names:
        esc = _escape(s)
        rows.append(
            f'<div class="tree-leaf"><label class="tree-label"><input type="checkbox" class="{cb_class}" '
            f'value="{esc}" onchange="applyFilters()"><span class="tree-name">{esc}</span></label></div>'
        )
    al = _escape(aria_label)
    return f'<div id="{tree_id}" class="tree-filter-scroll" role="group" aria-label="{al}">{"".join(rows)}</div>'


# Catalog IDs conhecidos (da config)
CATALOG_INSTITUTION = "63b07b3e-c200-4b3d-b9e6-742a096ae26e"
CATALOG_BANCA = "5d401e50-47cf-4d06-9a2f-19997cd0f258"
CATALOG_FINALIDADE = "4383bd62-e829-491e-8bb5-b40bd649817f"


def _exam_data(q: dict) -> dict:
    """Extrai dados do primeiro exam da questao."""
    exams = q.get("exams", [])
    if not exams:
        return {}
    return exams[0]


def _catalog_name(exam: dict, catalog_id: str) -> str:
    """Extrai nome de um catalogo do exam."""
    catalogs = exam.get("catalogs", {})
    entry = catalogs.get(catalog_id, {})
    return entry.get("name", "") if isinstance(entry, dict) else ""


def _extract_filter_values(questions: list[dict]) -> dict:
    """Extrai valores unicos de cada campo filtravel das questoes."""
    values = {
        "specialties": set(),
        "institutions": set(),
        "years": set(),
        "answer_types": set(),
        "jurys": set(),
        "regions": set(),
        "finalidades": set(),
    }
    for q in questions:
        for topic in q.get("topics", []):
            name = topic.get("name") or ""
            if name:
                values["specialties"].add(name)

        exam = _exam_data(q)
        inst = _catalog_name(exam, CATALOG_INSTITUTION)
        if inst:
            values["institutions"].add(inst)
            # Extrair estado da sigla no nome (ex: "PR - Hospital..." -> "PR")
            if len(inst) >= 2 and inst[2:3] in (" ", "-"):
                values["regions"].add(inst[:2])

        year = exam.get("year")
        if year:
            values["years"].add(str(year))

        atype = q.get("answer_type", "")
        if atype:
            values["answer_types"].add(atype)

        banca = _catalog_name(exam, CATALOG_BANCA)
        if banca:
            values["jurys"].add(banca)

        finalidade = _catalog_name(exam, CATALOG_FINALIDADE)
        if finalidade:
            values["finalidades"].add(finalidade)

    return {k: sorted(v) for k, v in values.items()}


def _answer_type_label(atype: str) -> str:
    labels = {
        "MULTIPLE_CHOICE": "Multipla Escolha",
        "TRUE_OR_FALSE": "Certo/Errado",
        "DISCURSIVE": "Discursiva",
    }
    return labels.get(atype, atype)


def _get_solution_info(q: dict) -> dict:
    """Extrai info sobre solucao (texto e video) da questao."""
    solution = q.get("solution", {})
    text_content = ""
    video_url = q.get("solution_video_url", "") or ""
    has_video = q.get("has_video_solution", False) or bool(video_url)

    if isinstance(solution, dict):
        text_content = solution.get("complete", "") or solution.get("brief", "")

    return {
        "has_text": bool(text_content),
        "has_video": has_video,
        "video_url": video_url,
        "text": text_content,
    }


def _get_labels(q: dict) -> list[str]:
    """Extrai labels (CANCELED, OUTDATED, etc) da questao."""
    labels = q.get("labels", [])
    result = []
    for lbl in labels:
        if isinstance(lbl, str):
            result.append(lbl)
        elif isinstance(lbl, dict):
            name = lbl.get("name", "") or lbl.get("key", "")
            if name:
                result.append(name)
    return result


def _render_question(q: dict, idx: int) -> str:
    """Renderiza uma questao em HTML."""
    qid = _escape(q.get("id", ""))

    topics = q.get("topics", [])
    specialty_names = [t.get("name") or t.get("title") or "" for t in topics]
    specialty_str = ", ".join(s for s in specialty_names if s) or "Sem especialidade"

    # Dados do exam (instituicao, ano, banca)
    exam = _exam_data(q)
    inst_name = _catalog_name(exam, CATALOG_INSTITUTION)
    jury_name = _catalog_name(exam, CATALOG_BANCA)
    finalidade_name = _catalog_name(exam, CATALOG_FINALIDADE)
    year = exam.get("year", "")

    answer_type = q.get("answer_type", "")
    answer_type_label = _answer_type_label(answer_type)

    # Extrair estado da sigla da instituicao (ex: "PR - Hospital..." -> "PR")
    region_name = ""
    if inst_name and len(inst_name) >= 2 and inst_name[2:3] in (" ", "-"):
        region_name = inst_name[:2]

    statement = q.get("statement", "") or ""
    if not statement:
        statement = q.get("statement_text", "") or json.dumps(q, ensure_ascii=False)[:500]

    alternatives = q.get("alternatives", [])

    sol_info = _get_solution_info(q)
    labels = _get_labels(q)
    labels_str = ",".join(labels).upper()

    label_tags = ""
    for lbl in labels:
        lbl_lower = lbl.lower()
        lbl_display = "Anulada" if "cancel" in lbl_lower else "Desatualizada" if "outdat" in lbl_lower else lbl
        if "cancel" in lbl_lower:
            label_tags += f'<span class="badge badge-anulada">{_escape(lbl_display)}</span>'
        elif "outdat" in lbl_lower:
            label_tags += f'<span class="badge badge-outdated">{_escape(lbl_display)}</span>'

    # Letra correta (position 0=A, 1=B, 2=C...)
    correct_letter = ""
    for alt in alternatives:
        if isinstance(alt, dict) and alt.get("correct"):
            pos = int(alt.get("position", 0))
            correct_letter = chr(65 + pos)  # 0->A, 1->B, 2->C
            break

    data_attrs = (
        f'data-qid="{qid}" '
        f'data-specialty="{_escape(specialty_str)}" '
        f'data-institution="{_escape(inst_name)}" '
        f'data-year="{_escape(str(year))}" '
        f'data-type="{_escape(answer_type)}" '
        f'data-jury="{_escape(jury_name)}" '
        f'data-finalidade="{_escape(finalidade_name)}" '
        f'data-region="{_escape(region_name)}" '
        f'data-has-text-solution="{str(sol_info["has_text"]).lower()}" '
        f'data-has-video-solution="{str(sol_info["has_video"]).lower()}" '
        f'data-labels="{_escape(labels_str)}" '
        f'data-correct="{_escape(correct_letter)}"'
    )

    alts_html = ""
    if alternatives:
        alts_html = '<div class="alternativas">'
        for alt in alternatives:
            if isinstance(alt, dict):
                pos = int(alt.get("position", 0))
                letter = chr(65 + pos)  # A, B, C, D, E
                text = alt.get("body", "")
                is_correct = alt.get("correct", False)
                alts_html += (
                    f'<div class="alternativa alt" data-letter="{letter}" data-correct="{str(is_correct).lower()}" '
                    f'onclick="selectAlt(this)">'
                    f'<div class="letra">{letter}</div>'
                    f'<div class="texto-alt">{text}</div>'
                    f'</div>'
                )
            else:
                alts_html += f'<div class="alternativa alt">{alt}</div>'
        alts_html += "</div>"

    cab = " · ".join(p for p in [inst_name, str(year) if year else ""] if p)
    meta_parts = []
    if cab:
        meta_parts.append(f'<span class="badge badge-year">{_escape(cab)}</span>')
    meta_parts.append(f'<span class="badge badge-type">{_escape(answer_type_label)}</span>')
    meta_parts.append(f'<span class="badge badge-topic">{_escape(specialty_str)}</span>')
    if jury_name:
        meta_parts.append(f'<span class="badge badge-specialty">{_escape(jury_name)}</span>')
    meta_parts.append(label_tags)
    meta_html = "".join(meta_parts)

    # Gabarito
    correct_html = ""
    if correct_letter:
        correct_html = f'<div class="gabarito"><strong>Gabarito:</strong> {_escape(correct_letter)}</div>'

    # Solucao texto
    solution_text_html = ""
    if sol_info["text"]:
        solution_text_html = f'<div class="solution-text-content">{sol_info["text"]}</div>'

    # Solucao video
    video_html = ""
    if sol_info["video_url"]:
        vid = sol_info["video_url"]
        # Tentar extrair embed do YouTube/Vimeo
        embed_url = ""
        if "youtube.com/watch" in vid:
            vid_id = vid.split("v=")[-1].split("&")[0]
            embed_url = f"https://www.youtube.com/embed/{vid_id}"
        elif "youtu.be/" in vid:
            vid_id = vid.split("youtu.be/")[-1].split("?")[0]
            embed_url = f"https://www.youtube.com/embed/{vid_id}"
        elif "vimeo.com/" in vid:
            vid_id = vid.split("vimeo.com/")[-1].split("?")[0]
            embed_url = f"https://player.vimeo.com/video/{vid_id}"

        if embed_url:
            video_html = (
                f'<div class="video-solution">'
                f'<strong>Correcao em Video:</strong>'
                f'<iframe src="{_escape(embed_url)}" frameborder="0" allowfullscreen loading="lazy"></iframe>'
                f'</div>'
            )
        else:
            video_html = (
                f'<div class="video-solution">'
                f'<strong>Correcao em Video:</strong> '
                f'<a href="{_escape(vid)}" target="_blank" rel="noopener">Assistir video</a>'
                f'</div>'
            )

    return f"""
    <div class="question-card question" {data_attrs}>
        <div class="question-header">
            <span class="question-number">#{idx + 1}</span>
            <div class="question-meta">{meta_html}</div>
        </div>
        <div class="enunciado">{statement}</div>
        {alts_html}
        <div class="q-actions">
            <button type="button" class="btn btn-confirm" onclick="confirmAnswer(this)">Confirmar resposta</button>
            <button type="button" class="btn btn-show" onclick="toggleAnswer(this)">Ver gabarito</button>
            <button type="button" class="btn btn-reset" onclick="resetQuestion(this)" style="display:none">Refazer</button>
        </div>
        <div class="answer-section comentario" style="display:none;">
            {correct_html}
            {solution_text_html}
            {video_html}
        </div>
    </div>
    """


def generate_html(questions: list[dict], filter_options: dict, output_path: str = "questoes.html"):
    """Gera arquivo HTML com todas as questoes e filtros interativos."""
    print(f"\nGerando HTML com {len(questions)} questoes...")

    fv = _extract_filter_values(questions)

    topics_tree = filter_options.get("topics", [])
    specialty_filter_html = _specialty_filter_markup(topics_tree, fv["specialties"])

    # Instituicoes: usar filter_options se disponivel (343 itens), senao fallback das questoes
    inst_names = sorted(
        {item["name"] for item in filter_options.get("institution_id", []) if item.get("name")}
    ) or fv["institutions"]
    institution_filter_html = _simple_checkbox_filter(
        inst_names, "filter-institution-tree", "filter-institution-cb", "Instituicoes"
    )

    year_filter_html = _simple_checkbox_filter(fv["years"], "filter-year-tree", "filter-year-cb", "Anos")

    # Banca: usar filter_options se disponivel (47 itens)
    banca_names = sorted(
        {item["name"] for item in filter_options.get("jury_id", []) if item.get("name")}
    ) or fv["jurys"]
    jury_filter_html = _simple_checkbox_filter(
        banca_names, "filter-jury-tree", "filter-jury-cb", "Bancas"
    )

    # Finalidade: usar filter_options (24 itens)
    finalidade_names = sorted(
        {item["name"] for item in filter_options.get("goal_id", []) if item.get("name")}
    ) or fv["finalidades"]
    finalidade_filter_html = _simple_checkbox_filter(
        finalidade_names, "filter-finalidade-tree", "filter-finalidade-cb", "Finalidades"
    )

    # Regioes: extrair estados unicos do S3 locations + das questoes
    regions_data = filter_options.get("regions", [])
    state_names = {}
    if isinstance(regions_data, list):
        for loc in regions_data:
            if loc.get("type") == "STATE" and loc.get("code") and loc.get("state"):
                state_names[loc["code"]] = loc["state"]

    # Combinar com estados extraidos das questoes (fallback)
    all_states = set(fv.get("regions", []))
    # Criar lista de estados com nome completo
    region_items = []
    for code in sorted(all_states | set(state_names.keys())):
        full_name = state_names.get(code, code)
        region_items.append({"name": f"{code} - {full_name}" if full_name != code else code, "_depth": 0, "code": code})

    region_filter_html = _region_filter_markup(region_items if region_items else [], list(fv.get("regions", [])))

    questions_html = ""
    for i, q in enumerate(questions):
        questions_html += _render_question(q, i)

    total = len(questions)

    page_html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Estrategia Med - {total} Questoes</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root {{
    --bg-dark: #0f0f0f;
    --bg-card: #1a1a1a;
    --bg-hover: #252525;
    --accent: #00d4aa;
    --accent-light: #00f5c4;
    --accent-dim: rgba(0, 212, 170, 0.12);
    --correct: #22c55e;
    --incorrect: #ef4444;
    --text: #ffffff;
    --text-muted: #888888;
    --border: #333333;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    background: var(--bg-dark);
    color: var(--text);
    line-height: 1.6;
    padding: 20px;
    min-height: 100vh;
}}
.container {{ max-width: 1100px; margin: 0 auto; }}

.header {{
    text-align: center;
    margin-bottom: 28px;
    padding: 28px 24px;
    background: linear-gradient(135deg, var(--bg-card) 0%, #1f2937 100%);
    border-radius: 16px;
    border: 1px solid var(--border);
}}
.header h1 {{
    font-size: 1.75rem;
    margin-bottom: 10px;
    font-weight: 700;
    background: linear-gradient(90deg, var(--accent), var(--accent-light));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}}
.header p {{ color: var(--text-muted); font-size: 0.95rem; }}
.stats {{
    display: flex;
    justify-content: center;
    gap: 28px;
    margin-top: 22px;
    flex-wrap: wrap;
}}
.stat {{ text-align: center; }}
.stat-value {{
    font-size: 1.75rem;
    font-weight: 700;
    color: var(--accent);
}}
.stat-label {{ font-size: 0.85rem; color: var(--text-muted); }}

.filters-section {{
    background: var(--bg-card);
    border-radius: 16px;
    padding: 22px;
    margin-bottom: 22px;
    border: 1px solid var(--border);
}}
.filters-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    cursor: pointer;
    user-select: none;
}}
.filters-header h3 {{
    color: var(--accent);
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 1rem;
    font-weight: 600;
}}
.filters-toggle {{ color: var(--text-muted); font-size: 0.9rem; }}
.filters-content {{
    display: none;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 18px;
    margin-top: 20px;
}}
.filters-content.is-open {{ display: grid; }}
.filter-group {{
    display: flex;
    flex-direction: column;
    gap: 8px;
}}
.filter-group > label {{
    font-weight: 600;
    color: var(--text-muted);
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}
.filter-group select {{
    padding: 12px;
    background: var(--bg-hover);
    border: 1px solid var(--border);
    border-radius: 8px;
    color: var(--text);
    font-size: 0.9rem;
    min-height: 48px;
    cursor: pointer;
    transition: all 0.2s ease;
}}
.filter-group select:hover {{ border-color: var(--accent); }}
.filter-group select:focus {{
    outline: none;
    border-color: var(--accent);
    box-shadow: 0 0 0 3px rgba(0, 212, 170, 0.2);
}}

.search-box {{ position: relative; }}
.search-input {{
    width: 100%;
    padding: 14px 20px 14px 48px;
    background: var(--bg-hover);
    border: 1px solid var(--border);
    border-radius: 12px;
    color: var(--text);
    font-size: 0.95rem;
    transition: all 0.2s ease;
}}
.search-input:focus {{
    outline: none;
    border-color: var(--accent);
    box-shadow: 0 0 0 3px rgba(0, 212, 170, 0.2);
}}
.search-icon {{
    position: absolute;
    left: 18px;
    top: 50%;
    transform: translateY(-50%);
    color: var(--text-muted);
    pointer-events: none;
}}

.cb-group {{ display: flex; flex-direction: column; gap: 8px; }}
.cb-group label {{
    display: flex;
    align-items: flex-start;
    gap: 10px;
    font-size: 0.88rem;
    color: var(--text-muted);
    cursor: pointer;
    font-weight: 500;
    text-transform: none;
    letter-spacing: 0;
}}
.required-tag {{ font-size: 0.65rem; color: var(--incorrect); font-weight: 700; margin-left: 6px; }}

/* Checkboxes — identidade (fundo escuro + acento teal) */
.filters-section input[type="checkbox"] {{
    appearance: none;
    -webkit-appearance: none;
    width: 18px;
    height: 18px;
    margin: 0;
    margin-top: 2px;
    flex-shrink: 0;
    border: 2px solid var(--border);
    border-radius: 5px;
    background: var(--bg-hover);
    cursor: pointer;
    transition: border-color 0.2s, background 0.2s, box-shadow 0.2s;
    position: relative;
    box-sizing: border-box;
}}
.filters-section input[type="checkbox"]:hover {{
    border-color: rgba(0, 212, 170, 0.55);
    box-shadow: 0 0 0 3px var(--accent-dim);
}}
.filters-section input[type="checkbox"]:checked {{
    background: var(--accent);
    border-color: var(--accent);
}}
.filters-section input[type="checkbox"]:checked::after {{
    content: '';
    position: absolute;
    left: 5px;
    top: 2px;
    width: 4px;
    height: 8px;
    border: solid var(--bg-dark);
    border-width: 0 2px 2px 0;
    transform: rotate(45deg);
}}
.filters-section input[type="checkbox"]:focus-visible {{
    outline: none;
    box-shadow: 0 0 0 3px rgba(0, 212, 170, 0.45);
}}
.filters-section input[type="checkbox"]:checked:focus-visible {{
    box-shadow: 0 0 0 3px rgba(0, 212, 170, 0.35), 0 0 0 1px var(--accent-light);
}}

.filter-actions {{
    margin-top: 18px;
    padding-top: 16px;
    border-top: 1px solid var(--border);
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    justify-content: flex-end;
}}
.clear-filters {{
    padding: 8px 16px;
    background: transparent;
    border: 1px solid var(--border);
    border-radius: 8px;
    color: var(--text-muted);
    cursor: pointer;
    font-size: 0.85rem;
    transition: all 0.2s ease;
    font-weight: 500;
}}
.clear-filters:hover {{
    border-color: var(--incorrect);
    color: var(--incorrect);
}}
.clear-filters.accent-outline {{
    border-color: var(--accent);
    color: var(--accent);
    background: var(--accent-dim);
}}
.clear-filters.accent-outline:hover {{
    background: rgba(0, 212, 170, 0.22);
    color: var(--accent-light);
}}

.tree-filter-scroll {{
    max-height: 280px;
    overflow-y: auto;
    overflow-x: hidden;
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 8px;
    background: var(--bg-dark);
    scrollbar-width: thin;
    scrollbar-color: var(--border) transparent;
}}
.tree-branch {{
    border-radius: 10px;
    background: var(--bg-hover);
    border: 1px solid var(--border);
    margin-bottom: 5px;
    overflow: hidden;
}}
.tree-branch[open] {{ border-color: var(--accent); box-shadow: 0 0 16px rgba(0, 212, 170, 0.08); }}
.tree-summary {{
    list-style: none;
    display: flex;
    align-items: flex-start;
    gap: 8px;
    padding: 8px 10px;
    cursor: pointer;
    font-size: 0.85rem;
    font-weight: 500;
    color: var(--text);
}}
.tree-summary::-webkit-details-marker {{ display: none; }}
.tree-chevron {{
    flex-shrink: 0;
    width: 22px;
    height: 22px;
    margin-top: 1px;
    border-radius: 6px;
    background: var(--accent-dim);
    display: grid;
    place-items: center;
}}
.tree-chevron::after {{
    content: '';
    width: 6px;
    height: 6px;
    border-right: 2px solid var(--accent);
    border-bottom: 2px solid var(--accent);
    transform: rotate(-45deg);
    margin-top: -2px;
    transition: transform 0.2s ease;
}}
.tree-branch[open] > .tree-summary .tree-chevron::after {{ transform: rotate(45deg); margin-top: 0; }}
.tree-children {{
    padding: 4px 8px 10px 14px;
    border-top: 1px solid var(--border);
    border-left: 3px solid rgba(0, 212, 170, 0.35);
    margin: 0 0 6px 10px;
    border-radius: 0 0 0 8px;
    background: linear-gradient(90deg, rgba(0, 212, 170, 0.06), transparent);
}}
.tree-leaf {{ padding: 5px 6px; border-radius: 8px; margin: 2px 0; }}
.tree-leaf:hover {{ background: rgba(255,255,255,0.04); }}
.tree-leaf-flat {{ border-bottom: 1px solid var(--border); border-radius: 6px; }}
.tree-flat-fallback {{ padding: 2px 0; }}
.tree-label {{
    display: flex;
    align-items: flex-start;
    gap: 10px;
    cursor: pointer;
    font-size: 0.85rem;
    color: var(--text-muted);
    width: 100%;
    line-height: 1.45;
}}
.tree-name {{ flex: 1; color: var(--text); }}
.tree-branch .tree-label .tree-name {{ font-weight: 500; }}

.questions-container {{ min-height: 200px; }}
.question-card.question {{
    background: var(--bg-card);
    border-radius: 16px;
    padding: 28px;
    margin-bottom: 22px;
    border: 1px solid var(--border);
    transition: all 0.25s ease;
}}
.question-card.question:hover {{
    border-color: var(--accent);
    box-shadow: 0 0 28px rgba(0, 212, 170, 0.08);
}}
.question.answered-correct {{ border-color: rgba(34, 197, 94, 0.5); }}
.question.answered-wrong {{ border-color: rgba(239, 68, 68, 0.5); }}

.question-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 18px;
    padding-bottom: 14px;
    border-bottom: 1px solid var(--border);
    flex-wrap: wrap;
    gap: 10px;
}}
.question-number {{ font-weight: 700; font-size: 1.05rem; color: var(--accent); }}
.question-meta {{ display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }}
.badge {{
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 600;
}}
.badge-type, .badge-year {{
    background: rgba(0, 212, 170, 0.12);
    color: var(--accent);
}}
.badge-topic {{
    background: rgba(99, 102, 241, 0.15);
    color: #a5b4fc;
}}
.badge-specialty {{ background: rgba(255,255,255,0.08); color: var(--text-muted); }}
.badge-anulada {{ background: rgba(239, 68, 68, 0.12); color: var(--incorrect); }}
.badge-outdated {{ background: rgba(245, 158, 11, 0.15); color: #fbbf24; }}

.enunciado {{
    font-size: 1.02rem;
    margin-bottom: 22px;
    line-height: 1.8;
    color: var(--text);
}}
.enunciado img {{ max-width: 100%; height: auto; border-radius: 8px; margin: 10px 0; }}

.alternativas {{
    display: flex;
    flex-direction: column;
    gap: 12px;
    margin-bottom: 18px;
}}
.alternativa.alt {{
    display: flex;
    align-items: flex-start;
    gap: 14px;
    padding: 16px 18px;
    background: var(--bg-hover);
    border-radius: 12px;
    cursor: pointer;
    transition: all 0.2s ease;
    border: 2px solid transparent;
    font-size: 0.95rem;
    line-height: 1.55;
    color: var(--text);
}}
.alternativa.alt:hover {{
    background: #2a2a2a;
    transform: translateX(4px);
}}
.alternativa.alt.selected {{
    border-color: var(--accent);
    background: rgba(0, 212, 170, 0.1);
}}
.alternativa.alt.correct-reveal {{
    border-color: var(--correct);
    background: rgba(34, 197, 94, 0.1);
}}
.alternativa.alt.wrong-reveal {{
    border-color: var(--incorrect);
    background: rgba(239, 68, 68, 0.1);
}}
.alternativa.alt.dimmed {{ opacity: 0.42; }}
.alternativa.alt.locked {{ pointer-events: none; cursor: default; }}

.letra {{
    width: 36px;
    height: 36px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--border);
    border-radius: 8px;
    font-weight: 700;
    flex-shrink: 0;
    font-size: 0.9rem;
    color: var(--text);
    transition: all 0.2s ease;
}}
.alternativa.selected .letra {{
    background: var(--accent);
    color: var(--bg-dark);
}}
.alternativa.correct-reveal .letra {{
    background: var(--correct);
    color: #fff;
}}
.alternativa.wrong-reveal .letra {{
    background: var(--incorrect);
    color: #fff;
}}
.texto-alt {{ flex: 1; padding-top: 5px; }}
.texto-alt img {{ max-width: 100%; height: auto; }}

.q-actions {{ display: flex; gap: 10px; flex-wrap: wrap; margin-top: 4px; }}
.btn {{
    border: none;
    padding: 10px 18px;
    border-radius: 10px;
    font-size: 0.88rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s ease;
}}
.btn-confirm {{ background: var(--accent); color: var(--bg-dark); }}
.btn-confirm:hover {{ filter: brightness(1.08); }}
.btn-confirm:disabled {{ opacity: 0.35; cursor: not-allowed; filter: none; }}
.btn-show {{
    background: var(--bg-hover);
    border: 1px solid var(--border);
    color: var(--text);
}}
.btn-show:hover {{ border-color: var(--accent); color: var(--accent); }}
.btn-reset {{
    background: rgba(245, 158, 11, 0.15);
    border: 1px solid rgba(245, 158, 11, 0.35);
    color: #fbbf24;
}}

.answer-section {{
    margin-top: 22px;
    padding: 22px;
    background: linear-gradient(135deg, #1f2937 0%, var(--bg-card) 100%);
    border-radius: 12px;
    border-left: 4px solid var(--accent);
}}
.gabarito {{ font-size: 1rem; margin-bottom: 12px; color: var(--text); }}
.gabarito strong {{ color: var(--correct); }}
.solution-text-content {{ line-height: 1.75; font-size: 0.92rem; color: var(--text-muted); }}
.solution-text-content img {{ max-width: 100%; border-radius: 8px; margin: 8px 0; }}
.video-solution {{ margin-top: 16px; }}
.video-solution strong {{ display: block; margin-bottom: 8px; color: var(--accent); }}
.video-solution iframe {{ width: 100%; height: 340px; border-radius: 10px; border: none; }}
.video-solution a {{ color: var(--accent); font-weight: 600; }}

.result-banner {{
    display: none;
    padding: 12px 16px;
    border-radius: 10px;
    margin-bottom: 12px;
    font-weight: 600;
    font-size: 0.9rem;
}}
.result-banner.show {{ display: flex; align-items: center; }}
.result-banner.correct {{ background: rgba(34, 197, 94, 0.15); color: var(--correct); }}
.result-banner.wrong {{ background: rgba(239, 68, 68, 0.15); color: var(--incorrect); }}

.pagination {{
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 8px;
    margin: 26px 0;
    flex-wrap: wrap;
}}
.page-btn {{
    padding: 10px 14px;
    background: var(--bg-hover);
    border: 1px solid var(--border);
    border-radius: 8px;
    color: var(--text);
    cursor: pointer;
    font-weight: 500;
    font-size: 0.88rem;
    transition: all 0.2s ease;
}}
.page-btn:hover:not(:disabled) {{
    background: var(--accent);
    color: var(--bg-dark);
    border-color: var(--accent);
}}
.page-btn.active {{
    background: var(--accent);
    color: var(--bg-dark);
    border-color: var(--accent);
}}
.page-btn:disabled {{ opacity: 0.35; cursor: not-allowed; }}

.no-results {{
    text-align: center;
    padding: 48px 20px;
    color: var(--text-muted);
}}
.no-results h3 {{ font-size: 1.25rem; margin-bottom: 10px; color: var(--text); }}

@media (max-width: 768px) {{
    body {{ padding: 12px; }}
    .question-card.question {{ padding: 20px; }}
    .stats {{ gap: 16px; }}
    .filters-content.is-open {{ grid-template-columns: 1fr; }}
    .video-solution iframe {{ height: 220px; }}
}}

</style>
</head>
<body>
<div class="container">
<header class="header">
    <h1>📚 Estrategia Med — Questoes</h1>
    <p id="questions-count">{total} questoes no arquivo</p>
    <div class="stats">
        <div class="stat">
            <div class="stat-value" id="st-answered">0</div>
            <div class="stat-label">Respondidas</div>
        </div>
        <div class="stat">
            <div class="stat-value" id="st-correct">0</div>
            <div class="stat-label">Acertos</div>
        </div>
        <div class="stat">
            <div class="stat-value" id="st-wrong">0</div>
            <div class="stat-label">Erros</div>
        </div>
        <div class="stat">
            <div class="stat-value" id="st-pct">0%</div>
            <div class="stat-label">Aproveitamento</div>
        </div>
        <div class="stat">
            <div class="stat-value" id="st-total">{total}</div>
            <div class="stat-label">Exibindo</div>
        </div>
    </div>
</header>

<section class="filters-section">
    <div class="filters-header" onclick="toggleFilters()">
        <h3>🔍 Filtros e busca</h3>
        <span class="filters-toggle" id="filters-toggle-text">▼ Expandir</span>
    </div>
    <div class="filters-content" id="filters-content">
        <div class="filter-group" style="grid-column: 1 / -1;">
            <label>Buscar no enunciado</label>
            <div class="search-box">
                <span class="search-icon">🔎</span>
                <input type="text" class="search-input" id="filter-text" placeholder="Digite palavras-chave..." oninput="debounceFilter()">
            </div>
        </div>
        <div class="filter-group" style="grid-column: 1 / -1;">
            <label>Especialidade e assuntos</label>
            {specialty_filter_html}
        </div>
        <div class="filter-group" style="grid-column: 1 / -1;">
            <label>Instituicao</label>
            {institution_filter_html}
        </div>
        <div class="filter-group" style="grid-column: 1 / -1;">
            <label>Ano</label>
            {year_filter_html}
        </div>
        <div class="filter-group" style="grid-column: 1 / -1;">
            <label>Finalidade</label>
            {finalidade_filter_html}
        </div>
        <div class="filter-group" style="grid-column: 1 / -1;">
            <label>Banca</label>
            {jury_filter_html}
        </div>
        <div class="filter-group" style="grid-column: 1 / -1;">
            <label>Regiao</label>
            {region_filter_html}
        </div>
        <div class="filter-group">
            <label>Tipo de questao <span class="required-tag">obrig.</span></label>
            <div class="cb-group">
                <label><input type="checkbox" id="ft-true-or-false" checked onchange="applyFilters()"> Certo/Errado</label>
                <label><input type="checkbox" id="ft-multiple-choice" checked onchange="applyFilters()"> Multipla escolha</label>
                <label><input type="checkbox" id="ft-discursive" checked onchange="applyFilters()"> Discursiva</label>
            </div>
        </div>
        <div class="filter-group">
            <label>Solucoes</label>
            <div class="cb-group">
                <label><input type="checkbox" id="fs-with-text" checked onchange="applyFilters()"> Com solucao em texto</label>
                <label><input type="checkbox" id="fs-without-text" checked onchange="applyFilters()"> Sem solucao em texto</label>
                <label><input type="checkbox" id="fs-with-video" checked onchange="applyFilters()"> Com solucao em video</label>
                <label><input type="checkbox" id="fs-without-video" checked onchange="applyFilters()"> Sem solucao em video</label>
            </div>
        </div>
        <div class="filter-group">
            <label>Vigencia</label>
            <div class="cb-group">
                <label><input type="checkbox" id="fv-outdated" checked onchange="applyFilters()"> Desatualizadas</label>
                <label><input type="checkbox" id="fv-canceled" checked onchange="applyFilters()"> Anuladas</label>
            </div>
        </div>
        <div class="filter-group">
            <label>Situacao</label>
            <div class="cb-group">
                <label><input type="checkbox" id="fst-all" checked onchange="applyFilters()"> Nao respondidas</label>
                <label><input type="checkbox" id="fst-correct" checked onchange="applyFilters()"> Que acertei</label>
                <label><input type="checkbox" id="fst-wrong" checked onchange="applyFilters()"> Que errei</label>
            </div>
        </div>
    </div>
    <div class="filter-actions">
        <button type="button" class="clear-filters" onclick="clearFilters()">Limpar filtros</button>
        <button type="button" class="clear-filters accent-outline" onclick="clearAllAnswers()">Limpar respostas salvas</button>
    </div>
</section>

<div id="pagination-top" class="pagination"></div>
<div id="questions-container" class="questions-container">
    {questions_html}
</div>
<div id="pagination-bottom" class="pagination"></div>

<div class="no-results" id="no-results" style="display: none;">
    <h3>Nenhuma questao encontrada</h3>
    <p>Tente ajustar os filtros ou limpar a busca.</p>
</div>
</div>

<script>
const PER_PAGE = 50;
let currentPage = 1;
let filtered = [];
let debounceTimer = null;
const STORAGE_KEY = 'estrategia_med_answers';

// ---- LocalStorage ----
function loadAnswers() {{
    try {{ return JSON.parse(localStorage.getItem(STORAGE_KEY)) || {{}}; }}
    catch {{ return {{}}; }}
}}
function saveAnswers(answers) {{
    localStorage.setItem(STORAGE_KEY, JSON.stringify(answers));
}}
function clearAllAnswers() {{
    if (!confirm('Tem certeza que quer apagar todas as respostas salvas?')) return;
    localStorage.removeItem(STORAGE_KEY);
    document.querySelectorAll('.question').forEach(q => {{
        q.classList.remove('answered-correct', 'answered-wrong');
        q.querySelectorAll('.alt').forEach(a => {{
            a.classList.remove('selected', 'correct-reveal', 'wrong-reveal', 'dimmed', 'locked');
        }});
        const banner = q.querySelector('.result-banner');
        if (banner) banner.remove();
        const ans = q.querySelector('.answer-section');
        if (ans) ans.style.display = 'none';
        const btnConfirm = q.querySelector('.btn-confirm');
        const btnReset = q.querySelector('.btn-reset');
        if (btnConfirm) {{ btnConfirm.style.display = ''; btnConfirm.disabled = true; }}
        if (btnReset) btnReset.style.display = 'none';
    }});
    updateStats();
}}

// ---- Restore saved state ----
function restoreSavedAnswers() {{
    const answers = loadAnswers();
    for (const [qid, data] of Object.entries(answers)) {{
        const q = document.querySelector(`.question[data-qid="${{qid}}"]`);
        if (!q) continue;
        const alts = q.querySelectorAll('.alt');
        const correctLetter = q.dataset.correct;

        alts.forEach(a => {{
            a.classList.add('locked');
            if (a.dataset.letter === data.selected) {{
                a.classList.add('selected');
                if (a.dataset.correct === 'true') a.classList.add('correct-reveal');
                else a.classList.add('wrong-reveal');
            }} else if (a.dataset.correct === 'true') {{
                a.classList.add('correct-reveal');
            }} else {{
                a.classList.add('dimmed');
            }}
        }});

        if (data.correct) q.classList.add('answered-correct');
        else q.classList.add('answered-wrong');

        // Banner
        const actions = q.querySelector('.q-actions');
        const banner = document.createElement('div');
        banner.className = 'result-banner show ' + (data.correct ? 'correct' : 'wrong');
        banner.textContent = data.correct ? 'Voce acertou!' : 'Voce errou. Gabarito: ' + correctLetter;
        actions.parentNode.insertBefore(banner, actions);

        // Buttons
        const btnConfirm = q.querySelector('.btn-confirm');
        const btnReset = q.querySelector('.btn-reset');
        if (btnConfirm) btnConfirm.style.display = 'none';
        if (btnReset) btnReset.style.display = '';
    }}
    updateStats();
}}

// ---- Stats ----
function updateStats() {{
    const answers = loadAnswers();
    let correct = 0, wrong = 0;
    for (const v of Object.values(answers)) {{
        if (v.correct) correct++; else wrong++;
    }}
    const answered = correct + wrong;
    const pct = answered ? Math.round(100 * correct / answered) : 0;
    document.getElementById('st-correct').textContent = correct;
    document.getElementById('st-wrong').textContent = wrong;
    const elA = document.getElementById('st-answered');
    const elP = document.getElementById('st-pct');
    if (elA) elA.textContent = answered;
    if (elP) elP.textContent = pct + '%';
}}

// ---- Interaction ----
function selectAlt(el) {{
    if (el.classList.contains('locked')) return;
    const q = el.closest('.question');
    q.querySelectorAll('.alt').forEach(a => a.classList.remove('selected'));
    el.classList.add('selected');
    const btn = q.querySelector('.btn-confirm');
    if (btn) btn.disabled = false;
}}

function confirmAnswer(btn) {{
    const q = btn.closest('.question');
    const selected = q.querySelector('.alt.selected');
    if (!selected) return;

    const qid = q.dataset.qid;
    const correctLetter = q.dataset.correct;
    const selectedLetter = selected.dataset.letter;
    const isCorrect = selected.dataset.correct === 'true';

    // Lock & reveal
    q.querySelectorAll('.alt').forEach(a => {{
        a.classList.add('locked');
        if (a.dataset.correct === 'true') a.classList.add('correct-reveal');
        else if (a === selected && !isCorrect) a.classList.add('wrong-reveal');
        else if (a !== selected) a.classList.add('dimmed');
    }});

    q.classList.add(isCorrect ? 'answered-correct' : 'answered-wrong');

    // Banner
    const banner = document.createElement('div');
    banner.className = 'result-banner show ' + (isCorrect ? 'correct' : 'wrong');
    banner.textContent = isCorrect ? 'Voce acertou!' : 'Voce errou. Gabarito: ' + correctLetter;
    const actions = q.querySelector('.q-actions');
    actions.parentNode.insertBefore(banner, actions);

    // Buttons
    btn.style.display = 'none';
    q.querySelector('.btn-reset').style.display = '';

    // Save
    const answers = loadAnswers();
    answers[qid] = {{ selected: selectedLetter, correct: isCorrect }};
    saveAnswers(answers);
    updateStats();
}}

function resetQuestion(btn) {{
    const q = btn.closest('.question');
    const qid = q.dataset.qid;

    q.classList.remove('answered-correct', 'answered-wrong');
    q.querySelectorAll('.alt').forEach(a => {{
        a.classList.remove('selected', 'correct-reveal', 'wrong-reveal', 'dimmed', 'locked');
    }});
    const banner = q.querySelector('.result-banner');
    if (banner) banner.remove();

    const ans = q.querySelector('.answer-section');
    if (ans) ans.style.display = 'none';

    btn.style.display = 'none';
    const btnConfirm = q.querySelector('.btn-confirm');
    if (btnConfirm) {{ btnConfirm.style.display = ''; btnConfirm.disabled = true; }}

    const answers = loadAnswers();
    delete answers[qid];
    saveAnswers(answers);
    updateStats();
}}

function toggleAnswer(btn) {{
    const section = btn.closest('.question').querySelector('.answer-section');
    if (section.style.display === 'none') {{
        section.style.display = 'block';
        btn.textContent = 'Ocultar Gabarito';
    }} else {{
        section.style.display = 'none';
        btn.textContent = 'Ver Gabarito';
    }}
}}

// ---- Filters ----
function getTreeCheckboxValues(treeId, checkedSelector) {{
    const root = document.getElementById(treeId);
    if (!root) return [];
    return Array.from(root.querySelectorAll(checkedSelector)).map(cb => cb.value).filter(Boolean);
}}

function debounceFilter() {{
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(applyFilters, 300);
}}

function toggleFilters() {{
    const box = document.getElementById('filters-content');
    const t = document.getElementById('filters-toggle-text');
    if (!box || !t) return;
    const open = box.classList.toggle('is-open');
    t.textContent = open ? '▲ Recolher' : '▼ Expandir';
}}

function applyFilters() {{
    const text = document.getElementById('filter-text').value.toLowerCase();
    const specialties = getTreeCheckboxValues('filter-specialty-tree', '.filter-topic-cb:checked');
    const institutions = getTreeCheckboxValues('filter-institution-tree', '.filter-institution-cb:checked');
    const years = getTreeCheckboxValues('filter-year-tree', '.filter-year-cb:checked');
    const jurys = getTreeCheckboxValues('filter-jury-tree', '.filter-jury-cb:checked');
    const finalidades = getTreeCheckboxValues('filter-finalidade-tree', '.filter-finalidade-cb:checked');
    const regions = getTreeCheckboxValues('filter-region-tree', '.filter-region-cb:checked');

    const allowTypes = [];
    if (document.getElementById('ft-true-or-false').checked) allowTypes.push('TRUE_OR_FALSE');
    if (document.getElementById('ft-multiple-choice').checked) allowTypes.push('MULTIPLE_CHOICE');
    if (document.getElementById('ft-discursive').checked) allowTypes.push('DISCURSIVE');

    const wText = document.getElementById('fs-with-text').checked;
    const woText = document.getElementById('fs-without-text').checked;
    const wVideo = document.getElementById('fs-with-video').checked;
    const woVideo = document.getElementById('fs-without-video').checked;
    const showOutdated = document.getElementById('fv-outdated').checked;
    const showCanceled = document.getElementById('fv-canceled').checked;

    const showUnanswered = document.getElementById('fst-all').checked;
    const showCorrect = document.getElementById('fst-correct').checked;
    const showWrong = document.getElementById('fst-wrong').checked;
    const answers = loadAnswers();

    const all = Array.from(document.querySelectorAll('.question'));
    filtered = all.filter(q => {{
        if (text && !q.textContent.toLowerCase().includes(text)) return false;
        if (specialties.length && !specialties.some(s => q.dataset.specialty.includes(s))) return false;
        if (institutions.length && !institutions.includes(q.dataset.institution)) return false;
        if (years.length && !years.includes(q.dataset.year)) return false;
        if (jurys.length && !jurys.includes(q.dataset.jury)) return false;
        if (finalidades.length && !finalidades.includes(q.dataset.finalidade)) return false;
        if (regions.length && !regions.includes(q.dataset.region)) return false;
        if (!allowTypes.length || !allowTypes.includes(q.dataset.type)) return false;

        const ht = q.dataset.hasTextSolution === 'true';
        const hv = q.dataset.hasVideoSolution === 'true';
        if (ht && !wText) return false;
        if (!ht && !woText) return false;
        if (hv && !wVideo) return false;
        if (!hv && !woVideo) return false;

        const lbl = (q.dataset.labels || '').toUpperCase();
        if (lbl.includes('OUTDATED') && !showOutdated) return false;
        if (lbl.includes('CANCELED') && !showCanceled) return false;

        // Situacao
        const qid = q.dataset.qid;
        const ans = answers[qid];
        if (!ans && !showUnanswered) return false;
        if (ans && ans.correct && !showCorrect) return false;
        if (ans && !ans.correct && !showWrong) return false;

        return true;
    }});

    document.getElementById('st-total').textContent = filtered.length;
    const nr = document.getElementById('no-results');
    if (nr) nr.style.display = filtered.length === 0 ? 'block' : 'none';
    currentPage = 1;
    renderPage();
}}

function renderPage() {{
    const all = Array.from(document.querySelectorAll('.question'));
    all.forEach(q => q.style.display = 'none');
    const start = (currentPage - 1) * PER_PAGE;
    filtered.slice(start, start + PER_PAGE).forEach(q => q.style.display = 'block');
    renderPagination();
}}

function renderPagination() {{
    const total = Math.ceil(filtered.length / PER_PAGE);
    let h = '';
    if (total > 1) {{
        const max = 10;
        let s = Math.max(1, currentPage - Math.floor(max / 2));
        let e = Math.min(total, s + max - 1);
        if (e - s < max - 1) s = Math.max(1, e - max + 1);
        if (currentPage > 1) h += '<button type="button" class="page-btn" onclick="goTo(1)">&laquo;</button><button type="button" class="page-btn" onclick="goTo('+(currentPage-1)+')">&lsaquo;</button>';
        for (let i = s; i <= e; i++) h += '<button type="button" class="page-btn'+(i===currentPage?' active':'')+'" onclick="goTo('+i+')">'+i+'</button>';
        if (currentPage < total) h += '<button type="button" class="page-btn" onclick="goTo('+(currentPage+1)+')">&rsaquo;</button><button type="button" class="page-btn" onclick="goTo('+total+')">&raquo;</button>';
    }}
    document.getElementById('pagination-top').innerHTML = h;
    document.getElementById('pagination-bottom').innerHTML = h;
}}

function goTo(p) {{ currentPage = p; renderPage(); window.scrollTo(0,0); }}

function clearFilters() {{
    document.getElementById('filter-text').value = '';
    document.querySelectorAll(
        '#filter-specialty-tree .filter-topic-cb, #filter-region-tree .filter-region-cb, '
        + '#filter-institution-tree .filter-institution-cb, #filter-year-tree .filter-year-cb, '
        + '#filter-jury-tree .filter-jury-cb, #filter-finalidade-tree .filter-finalidade-cb'
    ).forEach(cb => {{ cb.checked = false; }});
    ['ft-true-or-false','ft-multiple-choice','ft-discursive',
     'fs-with-text','fs-without-text','fs-with-video','fs-without-video',
     'fv-outdated','fv-canceled','fst-all','fst-correct','fst-wrong'].forEach(id => {{
        document.getElementById(id).checked = true;
    }});
    applyFilters();
}}

// ---- Init ----
restoreSavedAnswers();
applyFilters();
</script>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(page_html)

    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"HTML gerado: {output_path} ({size_mb:.1f} MB)")


def _compact_question(q: dict) -> dict:
    """Extrai campos essenciais de uma questao pra JSON compacto."""
    exam = _exam_data(q)
    inst = _catalog_name(exam, CATALOG_INSTITUTION)
    banca = _catalog_name(exam, CATALOG_BANCA)
    finalidade = _catalog_name(exam, CATALOG_FINALIDADE)
    year = exam.get("year", "")

    # Região da sigla da instituicao
    region = ""
    if inst and len(inst) >= 2 and inst[2:3] in (" ", "-"):
        region = inst[:2]

    # Topicos
    topics = []
    for t in q.get("topics", []):
        name = t.get("name", "")
        path = t.get("path", "")
        if name:
            topics.append({"n": name, "p": path})

    # Alternativas compactas
    alts = []
    correct_pos = -1
    for a in q.get("alternatives", []):
        if not isinstance(a, dict):
            continue
        pos = int(a.get("position", 0))
        alts.append({
            "l": chr(65 + pos),
            "b": a.get("body", ""),
            "c": a.get("correct", False),
            "pct": a.get("answer_percentage", 0),
        })
        if a.get("correct"):
            correct_pos = pos

    # Solucao
    sol = q.get("solution", {})
    sol_text = ""
    if isinstance(sol, dict):
        sol_text = sol.get("complete", "") or sol.get("brief", "")

    return {
        "id": q.get("id", ""),
        "st": q.get("statement", ""),  # enunciado HTML
        "tp": q.get("answer_type", ""),
        "yr": year,
        "in": inst,
        "bk": banca,
        "fn": finalidade,
        "rg": region,
        "lb": q.get("labels", []),
        "to": topics,
        "al": alts,
        "cr": chr(65 + correct_pos) if correct_pos >= 0 else "",
        "sl": sol_text,
        "hv": q.get("has_video_solution", False),
        "vu": q.get("solution_video_url", "") or "",
    }


def generate_html_streaming(jsonl_path: str, filter_options: dict, output_path: str = "questoes.html"):
    """Gera HTML lendo JSONL em streaming. Nao carrega tudo na RAM.

    Estrategia:
    1. Le JSONL linha por linha, extrai versao compacta de cada questao
    2. Escreve um arquivo JSON separado (questoes_data.js)
    3. Gera HTML leve que carrega o JS e renderiza sob demanda
    """
    import sys

    data_path = output_path.replace(".html", "_data.js")
    print(f"Processando questoes de {jsonl_path}...")

    # Passada unica: extrair questoes compactas + valores de filtro
    filter_vals = {
        "specialties": set(), "institutions": set(), "years": set(),
        "answer_types": set(), "jurys": set(), "finalidades": set(), "regions": set(),
    }

    count = 0
    with open(data_path, "w", encoding="utf-8") as df:
        df.write("const Q=[\n")
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    q = json.loads(line)
                except json.JSONDecodeError:
                    continue

                cq = _compact_question(q)

                # Coletar valores de filtro
                for t in cq["to"]:
                    if t["n"]:
                        filter_vals["specialties"].add(t["n"])
                if cq["in"]:
                    filter_vals["institutions"].add(cq["in"])
                if cq["yr"]:
                    filter_vals["years"].add(str(cq["yr"]))
                if cq["tp"]:
                    filter_vals["answer_types"].add(cq["tp"])
                if cq["bk"]:
                    filter_vals["jurys"].add(cq["bk"])
                if cq["fn"]:
                    filter_vals["finalidades"].add(cq["fn"])
                if cq["rg"]:
                    filter_vals["regions"].add(cq["rg"])

                if count > 0:
                    df.write(",\n")
                df.write(json.dumps(cq, ensure_ascii=False, separators=(",", ":")))
                count += 1

                if count % 10000 == 0:
                    print(f"  {count} questoes processadas...", end="\r")

        df.write("\n];\n")

    data_size = os.path.getsize(data_path) / (1024 * 1024)
    print(f"  {count} questoes processadas -> {data_path} ({data_size:.1f} MB)")

    # Opcoes de filtro dos filter_options (completas) ou das questoes
    inst_names = sorted({item["name"] for item in filter_options.get("institution_id", []) if item.get("name")}) or sorted(filter_vals["institutions"])
    banca_names = sorted({item["name"] for item in filter_options.get("jury_id", []) if item.get("name")}) or sorted(filter_vals["jurys"])
    finalidade_names = sorted({item["name"] for item in filter_options.get("goal_id", []) if item.get("name")}) or sorted(filter_vals["finalidades"])

    # Regioes do S3
    regions_data = filter_options.get("regions", [])
    state_names = {}
    if isinstance(regions_data, list):
        for loc in regions_data:
            if loc.get("type") == "STATE" and loc.get("code") and loc.get("state"):
                state_names[loc["code"]] = loc["state"]
    all_states = sorted(filter_vals["regions"] | set(state_names.keys()))
    region_opts = [{"code": c, "label": f"{c} - {state_names.get(c, c)}"} for c in all_states]

    def _opts(items):
        return json.dumps(sorted(items), ensure_ascii=False)

    data_filename = os.path.basename(data_path)

    page_html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Estrategia Med — {count} Questoes</title>
<style>
:root {{--p:#2563eb;--pd:#1d4ed8;--pl:#dbeafe;--ok:#16a34a;--okl:#dcfce7;--okb:#86efac;--err:#dc2626;--errl:#fee2e2;--errb:#fca5a5;--w:#f59e0b;--wl:#fef3c7;--g1:#f9fafb;--g2:#e5e7eb;--g3:#d1d5db;--g5:#6b7280;--g7:#374151;--g8:#1f2937;--r:10px;}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:var(--g1);color:var(--g8);line-height:1.5}}
.wrap{{display:flex;min-height:100vh}}
.side{{width:340px;background:#fff;padding:20px;border-right:1px solid var(--g2);position:fixed;top:0;left:0;bottom:0;overflow-y:auto;z-index:10}}
.main{{margin-left:340px;padding:24px;flex:1;max-width:960px}}
.side h2{{font-size:18px;font-weight:700;color:var(--g8);margin-bottom:12px}}
.stats{{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:16px}}
.st{{flex:1;min-width:70px;text-align:center;padding:8px 4px;border-radius:var(--r);font-size:11px;font-weight:500}}
.st b{{font-size:18px;display:block}}.st-t{{background:var(--pl);color:var(--pd)}}.st-c{{background:var(--okl);color:var(--ok)}}.st-w{{background:var(--errl);color:var(--err)}}
.fg{{margin-bottom:12px}}.fg label{{display:block;font-weight:600;font-size:12px;color:var(--g5);margin-bottom:4px}}
.fg input[type=text]{{width:100%;padding:8px;border:1px solid var(--g3);border-radius:8px;font-size:13px}}
.fscroll{{max-height:160px;overflow-y:auto;border:1px solid var(--g2);border-radius:8px;padding:6px}}
.fscroll label{{display:flex;align-items:center;gap:6px;font-size:12px;color:var(--g7);padding:2px 0;cursor:pointer}}
.fscroll input{{accent-color:var(--p);width:14px;height:14px}}
.cbg{{display:flex;flex-direction:column;gap:3px}}.cbg label{{display:flex;align-items:center;gap:6px;font-size:12px;cursor:pointer}}
.cbg input{{accent-color:var(--p);width:15px;height:15px}}
details summary{{font-size:12px;font-weight:600;color:var(--g5);cursor:pointer;padding:6px 0;user-select:none}}
.btn{{border:none;padding:7px 14px;border-radius:8px;font-size:12px;font-weight:600;cursor:pointer}}
.btn-d{{background:var(--errl);color:var(--err);width:100%;margin-top:12px}}
.q{{background:#fff;border-radius:var(--r);padding:20px;margin-bottom:14px;box-shadow:0 1px 3px rgba(0,0,0,.08);border:2px solid var(--g2);transition:border-color .2s}}
.q.q-ok{{border-color:var(--okb)}}.q.q-err{{border-color:var(--errb)}}
.qh{{display:flex;justify-content:space-between;align-items:center;margin-bottom:4px}}
.qn{{font-weight:700;color:var(--p);font-size:14px}}
.badge{{display:inline-flex;padding:2px 8px;border-radius:20px;font-size:10px;font-weight:600}}
.badge-t{{background:var(--pl);color:var(--pd)}}.badge-cancel{{background:var(--errl);color:var(--err)}}.badge-outdat{{background:var(--wl);color:var(--w)}}
.qi{{font-size:11px;color:var(--g5);margin-bottom:4px}}.qs{{font-size:11px;color:var(--p);font-weight:600;margin-bottom:10px}}
.qb{{line-height:1.7;margin-bottom:14px;font-size:14px}}.qb img{{max-width:100%;height:auto;border-radius:6px}}
.alts{{display:flex;flex-direction:column;gap:6px;margin-bottom:14px}}
.alt{{display:flex;align-items:flex-start;gap:10px;padding:10px 14px;border-radius:8px;background:var(--g1);border:2px solid var(--g2);cursor:pointer;font-size:13px;line-height:1.6;transition:all .15s}}
.alt:hover{{border-color:var(--p);background:var(--pl)}}.alt.sel{{border-color:var(--p);background:var(--pl)}}
.alt.c-ok{{border-color:var(--ok)!important;background:var(--okl)!important}}.alt.c-err{{border-color:var(--err)!important;background:var(--errl)!important}}.alt.dim{{opacity:.45}}
.alt.lock{{pointer-events:none}}
.altl{{flex-shrink:0;width:26px;height:26px;border-radius:50%;background:var(--g2);display:flex;align-items:center;justify-content:center;font-weight:700;font-size:12px;color:var(--g5)}}
.alt.sel .altl{{background:var(--p);color:#fff}}.alt.c-ok .altl{{background:var(--ok);color:#fff}}.alt.c-err .altl{{background:var(--err);color:#fff}}
.altb{{flex:1}}.altb img{{max-width:100%;height:auto}}
.acts{{display:flex;gap:6px;flex-wrap:wrap}}
.btn-c{{background:var(--p);color:#fff}}.btn-c:disabled{{background:var(--g3)}}.btn-s{{background:var(--g1);color:var(--g7)}}.btn-r{{background:var(--wl);color:var(--g7)}}
.res{{padding:10px 14px;border-radius:8px;font-weight:600;font-size:13px;margin-bottom:10px;display:none}}.res.show{{display:flex;align-items:center;gap:6px}}
.res-ok{{background:var(--okl);color:var(--ok)}}.res-err{{background:var(--errl);color:var(--err)}}
.ans{{margin-top:14px;padding:16px;background:var(--g1);border-radius:var(--r);border:1px solid var(--g2);display:none}}
.ans h4{{margin-bottom:8px;color:var(--ok)}}.ans-txt{{line-height:1.7;font-size:13px}}.ans-txt img{{max-width:100%;height:auto;border-radius:6px}}
.vid{{margin-top:12px}}.vid iframe{{width:100%;height:340px;border-radius:8px;border:none}}
.pag{{display:flex;justify-content:center;gap:4px;margin:16px 0;flex-wrap:wrap}}
.pag button{{padding:6px 12px;border:1px solid var(--g2);background:#fff;border-radius:6px;cursor:pointer;font-size:12px}}
.pag button.act{{background:var(--p);color:#fff;border-color:var(--p)}}
@media(max-width:860px){{.side{{position:relative;width:100%;border-right:none;border-bottom:1px solid var(--g2)}}.main{{margin-left:0}}.wrap{{flex-direction:column}}}}
</style>
</head>
<body>
<div class="wrap">
<aside class="side">
<h2>Estrategia Med — Questoes</h2>
<p style="font-size:12px;color:var(--g5);margin-bottom:12px">{count} questoes no arquivo</p>
<div class="stats">
<div class="st st-t"><b id="st-t">{count}</b>Exibindo</div>
<div class="st st-c"><b id="st-c">0</b>Acertos</div>
<div class="st st-w"><b id="st-w">0</b>Erros</div>
</div>
<div class="fg"><label>Busca</label><input type="text" id="ftxt" placeholder="Buscar no enunciado..." oninput="df()"></div>

<details><summary>Especialidade</summary><div class="fscroll" id="f-spec"></div></details>
<details><summary>Instituicao</summary><div class="fscroll" id="f-inst"></div></details>
<details><summary>Ano</summary><div class="fscroll" id="f-year"></div></details>
<details><summary>Finalidade</summary><div class="fscroll" id="f-fin"></div></details>
<details><summary>Banca</summary><div class="fscroll" id="f-banca"></div></details>
<details><summary>Regiao</summary><div class="fscroll" id="f-reg"></div></details>

<details open><summary>Tipo de questao</summary><div class="cbg">
<label><input type="checkbox" class="ft" value="MULTIPLE_CHOICE" checked onchange="af()">Multipla escolha</label>
<label><input type="checkbox" class="ft" value="TRUE_OR_FALSE" checked onchange="af()">Certo/Errado</label>
<label><input type="checkbox" class="ft" value="DISCURSIVE" checked onchange="af()">Discursiva</label>
</div></details>

<details><summary>Vigencia</summary><div class="cbg">
<label><input type="checkbox" id="fv-out" checked onchange="af()">Desatualizadas</label>
<label><input type="checkbox" id="fv-can" checked onchange="af()">Anuladas</label>
</div></details>

<details><summary>Situacao</summary><div class="cbg">
<label><input type="checkbox" id="fs-na" checked onchange="af()">Nao respondidas</label>
<label><input type="checkbox" id="fs-ok" checked onchange="af()">Que acertei</label>
<label><input type="checkbox" id="fs-err" checked onchange="af()">Que errei</label>
</div></details>

<button class="btn btn-d" onclick="clr()">Limpar Filtros</button>
</aside>
<main class="main">
<div id="pag-t" class="pag"></div>
<div id="qc"></div>
<div id="pag-b" class="pag"></div>
</main>
</div>
<script src="{data_filename}"></script>
<script>
const PP=50;let cp=1,fq=[],SA=JSON.parse(localStorage.getItem('em_ans')||'{{}}');
const INST={_opts(inst_names)};
const BANCA={_opts(banca_names)};
const FIN={_opts(finalidade_names)};
const REG={json.dumps(region_opts, ensure_ascii=False)};
const YEARS={_opts(sorted(filter_vals["years"], reverse=True))};

function init(){{
  // Preencher filtros dinamicamente das questoes
  let specs=new Set();Q.forEach(q=>q.to.forEach(t=>specs.add(t.n)));
  fill('f-spec',Array.from(specs).sort(),'fs');
  fill('f-inst',INST,'fi');
  fill('f-year',YEARS,'fy');
  fill('f-fin',FIN,'ff');
  fill('f-banca',BANCA,'fb');
  fillReg();
  restoreAnswers();
  fq=[...Array(Q.length).keys()];
  rp();
}}
function fill(id,items,cls){{
  let h='';items.forEach(v=>h+='<label><input type=checkbox class="'+cls+'" value="'+esc(v)+'" onchange="af()"><span>'+esc(v)+'</span></label>');
  document.getElementById(id).innerHTML=h;
}}
function fillReg(){{
  let h='';REG.forEach(r=>h+='<label><input type=checkbox class="fr" value="'+esc(r.code)+'" onchange="af()"><span>'+esc(r.label)+'</span></label>');
  document.getElementById('f-reg').innerHTML=h;
}}
function esc(s){{return s?String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'):''}}
function gv(cls){{return Array.from(document.querySelectorAll('.'+cls+':checked')).map(c=>c.value)}}
let dt;function df(){{clearTimeout(dt);dt=setTimeout(af,300)}}

function af(){{
  const txt=document.getElementById('ftxt').value.toLowerCase();
  const sp=gv('fs'),ins=gv('fi'),yr=gv('fy'),fn=gv('ff'),bk=gv('fb'),rg=gv('fr');
  const tp=Array.from(document.querySelectorAll('.ft:checked')).map(c=>c.value);
  const vOut=document.getElementById('fv-out').checked,vCan=document.getElementById('fv-can').checked;
  const sNa=document.getElementById('fs-na').checked,sOk=document.getElementById('fs-ok').checked,sErr=document.getElementById('fs-err').checked;

  fq=[];
  for(let i=0;i<Q.length;i++){{
    const q=Q[i];
    if(tp.length&&!tp.includes(q.tp))continue;
    if(sp.length&&!q.to.some(t=>sp.includes(t.n)))continue;
    if(ins.length&&!ins.includes(q.in))continue;
    if(yr.length&&!yr.includes(String(q.yr)))continue;
    if(fn.length&&!fn.includes(q.fn))continue;
    if(bk.length&&!bk.includes(q.bk))continue;
    if(rg.length&&!rg.includes(q.rg))continue;
    const lb=(q.lb||[]).map(l=>l.toUpperCase());
    if(lb.includes('OUTDATED')&&!vOut)continue;
    if(lb.includes('CANCELED')&&!vCan)continue;
    const a=SA[q.id];
    if(!a&&!sNa)continue;
    if(a&&a.c&&!sOk)continue;
    if(a&&!a.c&&!sErr)continue;
    if(txt){{const s=(q.st||'').toLowerCase();if(!s.includes(txt))continue;}}
    fq.push(i);
  }}
  document.getElementById('st-t').textContent=fq.length;
  cp=1;rp();
}}

function rp(){{
  const c=document.getElementById('qc');
  const s=(cp-1)*PP,e=s+PP;
  let h='';
  for(let j=s;j<e&&j<fq.length;j++){{
    h+=rq(Q[fq[j]],fq[j]);
  }}
  c.innerHTML=h;
  rpag();
  updStats();
}}

function rq(q,idx){{
  const a=SA[q.id];const locked=!!a;
  const topStr=q.to.map(t=>t.n).join(', ')||'Sem especialidade';
  const tpLbl={{'MULTIPLE_CHOICE':'Multipla Escolha','TRUE_OR_FALSE':'Certo/Errado','DISCURSIVE':'Discursiva'}}[q.tp]||q.tp;
  let lblH='';
  (q.lb||[]).forEach(l=>{{
    if(l.toUpperCase().includes('CANCEL'))lblH+='<span class="badge badge-cancel">Anulada</span>';
    else if(l.toUpperCase().includes('OUTDAT'))lblH+='<span class="badge badge-outdat">Desatualizada</span>';
  }});
  let altH='<div class="alts">';
  q.al.forEach(al=>{{
    let cls='alt';
    if(locked){{
      cls+=' lock';
      if(a.s===al.l)cls+=al.c?' c-ok':' c-err';
      else if(al.c)cls+=' c-ok';
      else cls+=' dim';
    }}
    altH+=`<div class="${{cls}}" data-l="${{al.l}}" data-c="${{al.c}}" onclick="sa(this,'${{q.id}}')"><div class="altl">${{al.l}}</div><div class="altb">${{al.b}}</div></div>`;
  }});
  altH+='</div>';
  let resH='';
  if(locked){{
    const rc=a.c?'res-ok':'res-err';
    const rt=a.c?'Voce acertou!':'Voce errou. Gabarito: '+q.cr;
    resH=`<div class="res show ${{rc}}">${{rt}}</div>`;
  }}
  let solH='';
  if(q.sl)solH=`<div class="ans-txt">${{q.sl}}</div>`;
  let vidH='';
  if(q.vu){{
    let eu='';const v=q.vu;
    if(v.includes('youtube.com/watch'))eu='https://www.youtube.com/embed/'+v.split('v=')[1].split('&')[0];
    else if(v.includes('youtu.be/'))eu='https://www.youtube.com/embed/'+v.split('youtu.be/')[1].split('?')[0];
    else if(v.includes('vimeo.com/'))eu='https://player.vimeo.com/video/'+v.split('vimeo.com/')[1].split('?')[0];
    if(eu)vidH=`<div class="vid"><strong>Video:</strong><iframe src="${{eu}}" allowfullscreen loading="lazy"></iframe></div>`;
    else vidH=`<div class="vid"><a href="${{v}}" target="_blank">Assistir video</a></div>`;
  }}
  return `<div class="q ${{locked?(a.c?'q-ok':'q-err'):''}}" id="q-${{q.id}}">
    <div class="qh"><span class="qn">#${{idx+1}}</span><div><span class="badge badge-t">${{esc(tpLbl)}}</span>${{lblH}}</div></div>
    <div class="qi">${{esc(q.in)}} ${{q.yr}} | ${{esc(q.bk)}}</div>
    <div class="qs">${{esc(topStr)}}</div>
    <div class="qb">${{q.st}}</div>
    ${{altH}}
    ${{resH}}
    <div class="acts">
      <button class="btn btn-c" onclick="ca(this,'${{q.id}}')" ${{locked?'style="display:none"':'disabled'}}>Confirmar</button>
      <button class="btn btn-s" onclick="ta(this)">Ver Gabarito</button>
      ${{locked?`<button class="btn btn-r" onclick="ra('${{q.id}}')">Refazer</button>`:''}}
    </div>
    <div class="ans"><h4>Gabarito: ${{q.cr}}</h4>${{solH}}${{vidH}}</div>
  </div>`;
}}

function sa(el,qid){{if(el.classList.contains('lock'))return;const p=el.closest('.q');p.querySelectorAll('.alt').forEach(a=>a.classList.remove('sel'));el.classList.add('sel');p.querySelector('.btn-c').disabled=false;}}
function ca(btn,qid){{
  const p=btn.closest('.q');const sel=p.querySelector('.alt.sel');if(!sel)return;
  const l=sel.dataset.l,c=sel.dataset.c==='true';
  p.querySelectorAll('.alt').forEach(a=>{{a.classList.add('lock');if(a.dataset.c==='true')a.classList.add('c-ok');else if(a===sel&&!c)a.classList.add('c-err');else if(a!==sel)a.classList.add('dim');}});
  p.classList.add(c?'q-ok':'q-err');
  const q=Q.find(x=>x.id===qid);
  let r=document.createElement('div');r.className='res show '+(c?'res-ok':'res-err');r.textContent=c?'Voce acertou!':'Voce errou. Gabarito: '+(q?q.cr:'');
  btn.parentNode.before(r);btn.style.display='none';
  let rb=document.createElement('button');rb.className='btn btn-r';rb.textContent='Refazer';rb.onclick=()=>ra(qid);btn.parentNode.appendChild(rb);
  SA[qid]={{s:l,c:c}};localStorage.setItem('em_ans',JSON.stringify(SA));updStats();
}}
function ra(qid){{delete SA[qid];localStorage.setItem('em_ans',JSON.stringify(SA));rp();}}
function ta(btn){{const a=btn.closest('.q').querySelector('.ans');if(a.style.display==='block'){{a.style.display='none';btn.textContent='Ver Gabarito';}}else{{a.style.display='block';btn.textContent='Ocultar';}}}}
function updStats(){{let c=0,w=0;Object.values(SA).forEach(a=>{{if(a.c)c++;else w++;}});document.getElementById('st-c').textContent=c;document.getElementById('st-w').textContent=w;}}
function restoreAnswers(){{updStats();}}

function rpag(){{
  const t=Math.ceil(fq.length/PP);let h='';
  if(t>1){{
    const mx=10;let s=Math.max(1,cp-mx/2|0),e=Math.min(t,s+mx-1);if(e-s<mx-1)s=Math.max(1,e-mx+1);
    if(cp>1)h+='<button onclick="gp(1)">&laquo;</button><button onclick="gp('+(cp-1)+')">&lsaquo;</button>';
    for(let i=s;i<=e;i++)h+='<button class="'+(i===cp?'act':'')+'" onclick="gp('+i+')">'+i+'</button>';
    if(cp<t)h+='<button onclick="gp('+(cp+1)+')">&rsaquo;</button><button onclick="gp('+t+')">&raquo;</button>';
  }}
  document.getElementById('pag-t').innerHTML=h;document.getElementById('pag-b').innerHTML=h;
}}
function gp(p){{cp=p;rp();window.scrollTo(0,0);}}
function clr(){{
  document.getElementById('ftxt').value='';
  document.querySelectorAll('.fs,.fi,.fy,.ff,.fb,.fr').forEach(c=>c.checked=false);
  document.querySelectorAll('.ft').forEach(c=>c.checked=true);
  ['fv-out','fv-can','fs-na','fs-ok','fs-err'].forEach(id=>document.getElementById(id).checked=true);
  af();
}}
init();
</script>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(page_html)

    html_size = os.path.getsize(output_path) / (1024 * 1024)
    print(f"HTML gerado: {output_path} ({html_size:.1f} MB)")
    print(f"Dados: {data_path} ({data_size:.1f} MB)")
    print(f"Abra {output_path} no navegador (precisa dos 2 arquivos na mesma pasta).")

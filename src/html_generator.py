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


def _region_filter_markup(regions_tree: list[dict], region_names_fallback: list[str]) -> str:
    if regions_tree and isinstance(regions_tree, list):
        if _flat_has_parent_links(regions_tree):
            nested = _build_nested_tree(regions_tree)
            _sort_tree_nodes(nested)
            body = _render_tree_accordion(nested, "filter-region-cb")
        else:
            body = _render_flat_topic_checkboxes(regions_tree, "filter-region-cb")
        return f'<div id="filter-region-tree" class="tree-filter-scroll" role="group" aria-label="Regioes">{body}</div>'

    opts = "".join(
        f'<div class="tree-leaf"><label class="tree-label"><input type="checkbox" class="filter-region-cb" '
        f'value="{_escape(r)}" onchange="applyFilters()"><span class="tree-name">{_escape(r)}</span></label></div>'
        for r in region_names_fallback
    )
    return f'<div id="filter-region-tree" class="tree-filter-scroll" role="group" aria-label="Regioes">{opts}</div>'


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

        year = exam.get("year")
        if year:
            values["years"].add(str(year))

        atype = q.get("answer_type", "")
        if atype:
            values["answer_types"].add(atype)

        banca = _catalog_name(exam, CATALOG_BANCA)
        if banca:
            values["jurys"].add(banca)

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
    year = exam.get("year", "")

    answer_type = q.get("answer_type", "")
    answer_type_label = _answer_type_label(answer_type)

    region_name = ""  # Regioes nao vem na questao diretamente

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

    institution_options = "".join(
        f'<option value="{_escape(s)}">{_escape(s)}</option>' for s in fv["institutions"]
    )
    year_options = "".join(
        f'<option value="{_escape(s)}">{_escape(s)}</option>' for s in fv["years"]
    )
    jury_options = "".join(
        f'<option value="{_escape(s)}">{_escape(s)}</option>' for s in fv["jurys"]
    )

    regions_tree = filter_options.get("regions", [])
    region_filter_html = _region_filter_markup(regions_tree if isinstance(regions_tree, list) else [], fv["regions"])

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
    align-items: center;
    gap: 10px;
    font-size: 0.88rem;
    color: var(--text-muted);
    cursor: pointer;
    font-weight: 500;
    text-transform: none;
    letter-spacing: 0;
}}
.cb-group input {{ width: 16px; height: 16px; accent-color: var(--accent); cursor: pointer; }}
.required-tag {{ font-size: 0.65rem; color: var(--incorrect); font-weight: 700; margin-left: 6px; }}

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
.tree-label input {{ accent-color: var(--accent); }}
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
        <div class="filter-group">
            <label>Instituicao</label>
            <select id="filter-institution" multiple onchange="applyFilters()">{institution_options}</select>
        </div>
        <div class="filter-group">
            <label>Ano</label>
            <select id="filter-year" multiple onchange="applyFilters()">{year_options}</select>
        </div>
        <div class="filter-group">
            <label>Banca</label>
            <select id="filter-jury" multiple onchange="applyFilters()">{jury_options}</select>
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
function getSelectedValues(id) {{
    const sel = document.getElementById(id);
    if (!sel || !sel.selectedOptions) return [];
    return Array.from(sel.selectedOptions).filter(o => o.value).map(o => o.value);
}}

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
    const institutions = getSelectedValues('filter-institution');
    const years = getSelectedValues('filter-year');
    const jurys = getSelectedValues('filter-jury');
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
    document.querySelectorAll('#filter-specialty-tree .filter-topic-cb, #filter-region-tree .filter-region-cb').forEach(cb => {{ cb.checked = false; }});
    ['filter-institution','filter-year','filter-jury'].forEach(id => {{
        const sel = document.getElementById(id);
        if (!sel) return;
        for (const o of sel.options) o.selected = false;
    }});
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

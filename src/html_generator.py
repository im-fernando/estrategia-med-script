import html
import json
import os


def _escape(text):
    if not text:
        return ""
    return html.escape(str(text))


def _extract_filter_values(questions: list[dict]) -> dict:
    """Extrai valores unicos de cada campo filtravel das questoes."""
    values = {
        "specialties": set(),
        "institutions": set(),
        "years": set(),
        "answer_types": set(),
        "jurys": set(),
    }
    for q in questions:
        for topic in q.get("topics", []):
            name = topic.get("name") or topic.get("title") or ""
            if name:
                values["specialties"].add(name)

        inst = q.get("institution", {})
        if isinstance(inst, dict):
            name = inst.get("name", "")
            if name:
                values["institutions"].add(name)
        elif isinstance(inst, str) and inst:
            values["institutions"].add(inst)

        year = q.get("year")
        if year:
            values["years"].add(str(year))

        atype = q.get("answer_type", "")
        if atype:
            values["answer_types"].add(atype)

        jury = q.get("jury", {})
        if isinstance(jury, dict):
            name = jury.get("name", "")
            if name:
                values["jurys"].add(name)
        elif isinstance(jury, str) and jury:
            values["jurys"].add(jury)

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
    has_text = False
    has_video = False
    video_url = ""
    text_content = ""

    if isinstance(solution, dict):
        text_content = solution.get("text", "") or solution.get("body", "")
        has_text = bool(text_content)
        video_url = solution.get("video_url", "") or solution.get("video", "")
        has_video = bool(video_url) or bool(solution.get("has_video"))
    elif isinstance(solution, str) and solution:
        text_content = solution
        has_text = True

    if not has_video:
        has_video = bool(q.get("has_video_solution") or q.get("video_solution"))
    if not video_url:
        video_url = q.get("video_solution_url", "") or q.get("video_url", "")

    return {
        "has_text": has_text,
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

    inst = q.get("institution", {})
    inst_name = inst.get("name", "") if isinstance(inst, dict) else str(inst) if inst else ""

    year = q.get("year", "")
    answer_type = q.get("answer_type", "")
    answer_type_label = _answer_type_label(answer_type)

    jury = q.get("jury", {})
    jury_name = jury.get("name", "") if isinstance(jury, dict) else str(jury) if jury else ""

    statement = q.get("statement", "") or q.get("body", "") or q.get("question", "") or q.get("enunciado", "")
    if not statement:
        statement = q.get("text", "") or json.dumps(q, ensure_ascii=False)[:500]

    alternatives = q.get("alternatives", []) or q.get("options", [])
    correct_answer = q.get("correct_alternative", "") or q.get("answer", "") or q.get("gabarito", "")

    sol_info = _get_solution_info(q)
    labels = _get_labels(q)
    labels_str = ",".join(labels).upper()

    label_tags = ""
    for lbl in labels:
        lbl_lower = lbl.lower()
        lbl_display = "Anulada" if "cancel" in lbl_lower else "Desatualizada" if "outdat" in lbl_lower else lbl
        label_tags += f'<span class="badge badge-{_escape(lbl_lower)}">{_escape(lbl_display)}</span>'

    # Correct letter for data attr
    correct_letter = ""
    if alternatives:
        for alt in alternatives:
            if isinstance(alt, dict) and (alt.get("is_correct") or alt.get("correct")):
                correct_letter = alt.get("letter", "") or alt.get("label", "")
                break
    if not correct_letter and correct_answer:
        correct_letter = str(correct_answer)

    data_attrs = (
        f'data-qid="{qid}" '
        f'data-specialty="{_escape(specialty_str)}" '
        f'data-institution="{_escape(inst_name)}" '
        f'data-year="{_escape(str(year))}" '
        f'data-type="{_escape(answer_type)}" '
        f'data-jury="{_escape(jury_name)}" '
        f'data-has-text-solution="{str(sol_info["has_text"]).lower()}" '
        f'data-has-video-solution="{str(sol_info["has_video"]).lower()}" '
        f'data-labels="{_escape(labels_str)}" '
        f'data-correct="{_escape(correct_letter)}"'
    )

    alts_html = ""
    if alternatives:
        alts_html = '<div class="alternatives">'
        for alt in alternatives:
            if isinstance(alt, dict):
                letter = _escape(alt.get("letter", "") or alt.get("label", ""))
                text = alt.get("text", "") or alt.get("body", "") or alt.get("content", "")
                is_correct = alt.get("is_correct", False) or alt.get("correct", False)
                alts_html += (
                    f'<div class="alt" data-letter="{letter}" data-correct="{str(is_correct).lower()}" '
                    f'onclick="selectAlt(this)">'
                    f'<span class="alt-letter">{letter}</span>'
                    f'<span class="alt-text">{text}</span>'
                    f'</div>'
                )
            else:
                alts_html += f'<div class="alt">{alt}</div>'
        alts_html += "</div>"

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
    <div class="question" {data_attrs}>
        <div class="q-header">
            <span class="q-number">#{idx + 1}</span>
            <div class="q-badges">
                <span class="badge badge-type">{_escape(answer_type_label)}</span>
                {label_tags}
            </div>
        </div>
        <div class="q-info">
            <span class="q-institution">{_escape(inst_name)}</span>
            {f'<span class="q-sep">|</span><span class="q-year">{_escape(str(year))}</span>' if year else ''}
            {f'<span class="q-sep">|</span><span class="q-jury">{_escape(jury_name)}</span>' if jury_name else ''}
        </div>
        <div class="q-specialty">{_escape(specialty_str)}</div>
        <div class="q-statement">{statement}</div>
        {alts_html}
        <div class="q-actions">
            <button class="btn btn-confirm" onclick="confirmAnswer(this)">Confirmar Resposta</button>
            <button class="btn btn-show" onclick="toggleAnswer(this)">Ver Gabarito</button>
            <button class="btn btn-reset" onclick="resetQuestion(this)" style="display:none">Refazer</button>
        </div>
        <div class="answer-section" style="display:none;">
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

    # Topicos: usar arvore do filter_options se disponivel, senao fallback
    topics_tree = filter_options.get("topics", [])
    if topics_tree:
        specialty_options = ""
        for t in topics_tree:
            name = t.get("name", "")
            if not name:
                continue
            path = t.get("path", name)
            depth = t.get("_depth", path.count("[$$]"))
            indent = "\u00a0\u00a0\u00a0\u00a0" * depth  # non-breaking spaces
            display = f"{indent}{'└ ' if depth > 0 else ''}{_escape(name)}"
            # O value eh o path completo para match com os topicos da questao
            specialty_options += f'<option value="{_escape(name)}">{display}</option>\n'
    else:
        specialty_options = "".join(
            f'<option value="{_escape(s)}">{_escape(s)}</option>' for s in fv["specialties"]
        )

    institution_options = "".join(
        f'<option value="{_escape(s)}">{_escape(s)}</option>' for s in fv["institutions"]
    )
    year_options = "".join(
        f'<option value="{_escape(s)}">{_escape(s)}</option>' for s in fv["years"]
    )
    jury_options = "".join(
        f'<option value="{_escape(s)}">{_escape(s)}</option>' for s in fv["jurys"]
    )

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
<style>
:root {{
    --primary: #2563eb;
    --primary-dark: #1d4ed8;
    --primary-light: #dbeafe;
    --success: #16a34a;
    --success-light: #dcfce7;
    --success-border: #86efac;
    --danger: #dc2626;
    --danger-light: #fee2e2;
    --danger-border: #fca5a5;
    --warning: #f59e0b;
    --warning-light: #fef3c7;
    --gray-50: #f9fafb;
    --gray-100: #f3f4f6;
    --gray-200: #e5e7eb;
    --gray-300: #d1d5db;
    --gray-400: #9ca3af;
    --gray-500: #6b7280;
    --gray-600: #4b5563;
    --gray-700: #374151;
    --gray-800: #1f2937;
    --gray-900: #111827;
    --radius: 10px;
    --shadow: 0 1px 3px rgba(0,0,0,.08), 0 1px 2px rgba(0,0,0,.06);
    --shadow-md: 0 4px 6px rgba(0,0,0,.07), 0 2px 4px rgba(0,0,0,.06);
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: var(--gray-50); color: var(--gray-800); line-height: 1.5; }}

/* ---- Layout ---- */
.container {{ display: flex; min-height: 100vh; }}
.sidebar {{
    width: 340px; background: #fff; padding: 24px; border-right: 1px solid var(--gray-200);
    position: fixed; top: 0; left: 0; bottom: 0; overflow-y: auto; z-index: 10;
}}
.main {{ margin-left: 340px; padding: 24px; flex: 1; max-width: 960px; }}

/* ---- Sidebar ---- */
.sidebar-title {{ font-size: 20px; font-weight: 700; color: var(--gray-900); margin-bottom: 16px; }}
.stats-bar {{
    display: flex; gap: 8px; margin-bottom: 20px; flex-wrap: wrap;
}}
.stat-card {{
    flex: 1; min-width: 80px; text-align: center; padding: 10px 6px;
    border-radius: var(--radius); font-size: 12px; font-weight: 500;
}}
.stat-total {{ background: var(--primary-light); color: var(--primary-dark); }}
.stat-correct {{ background: var(--success-light); color: var(--success); }}
.stat-wrong {{ background: var(--danger-light); color: var(--danger); }}
.stat-card .stat-num {{ font-size: 20px; font-weight: 700; display: block; }}

.filter-section {{ margin-bottom: 16px; }}
.filter-section summary {{
    font-size: 13px; font-weight: 600; color: var(--gray-600); cursor: pointer;
    padding: 8px 0; user-select: none; list-style: none; display: flex; align-items: center; gap: 6px;
}}
.filter-section summary::before {{ content: '\\25B6'; font-size: 9px; transition: transform .15s; }}
.filter-section[open] summary::before {{ transform: rotate(90deg); }}
.filter-section .filter-body {{ padding: 8px 0; }}
.filter-section select {{
    width: 100%; padding: 8px 10px; border: 1px solid var(--gray-300); border-radius: 8px;
    font-size: 13px; background: #fff; max-height: 140px;
}}
.filter-section input[type="text"] {{
    width: 100%; padding: 9px 12px; border: 1px solid var(--gray-300); border-radius: 8px;
    font-size: 13px; background: #fff; transition: border-color .15s;
}}
.filter-section input[type="text"]:focus {{ border-color: var(--primary); outline: none; box-shadow: 0 0 0 3px rgba(37,99,235,.1); }}

.cb-group {{ display: flex; flex-direction: column; gap: 6px; }}
.cb-group label {{
    display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--gray-700);
    cursor: pointer; padding: 4px 0;
}}
.cb-group input[type="checkbox"] {{
    width: 16px; height: 16px; accent-color: var(--primary); cursor: pointer;
}}
.required-tag {{ font-size: 9px; color: var(--danger); font-weight: 700; text-transform: uppercase; letter-spacing: .5px; }}

.btn {{ border: none; padding: 8px 16px; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; transition: all .15s; }}
.btn-primary {{ background: var(--primary); color: #fff; }}
.btn-primary:hover {{ background: var(--primary-dark); }}
.btn-danger {{ background: var(--danger-light); color: var(--danger); }}
.btn-danger:hover {{ background: #fecaca; }}
.btn-clear {{ width: 100%; margin-top: 16px; }}

/* ---- Questions ---- */
.question {{
    background: #fff; border-radius: var(--radius); padding: 24px; margin-bottom: 16px;
    box-shadow: var(--shadow); border: 1px solid var(--gray-200); transition: border-color .2s;
}}
.question.answered-correct {{ border-color: var(--success-border); }}
.question.answered-wrong {{ border-color: var(--danger-border); }}

.q-header {{ display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; }}
.q-number {{ font-weight: 700; color: var(--primary); font-size: 15px; }}
.q-badges {{ display: flex; gap: 6px; flex-wrap: wrap; }}
.badge {{
    display: inline-flex; align-items: center; padding: 2px 10px; border-radius: 20px;
    font-size: 11px; font-weight: 600; letter-spacing: .3px;
}}
.badge-type {{ background: var(--primary-light); color: var(--primary-dark); }}
.badge-canceled {{ background: var(--danger-light); color: var(--danger); }}
.badge-outdated {{ background: var(--warning-light); color: var(--warning); }}

.q-info {{ display: flex; align-items: center; gap: 6px; margin-bottom: 4px; font-size: 12px; color: var(--gray-500); flex-wrap: wrap; }}
.q-sep {{ color: var(--gray-300); }}
.q-specialty {{ font-size: 12px; color: var(--primary); margin-bottom: 14px; font-weight: 600; }}
.q-statement {{ line-height: 1.7; margin-bottom: 16px; font-size: 15px; }}
.q-statement img {{ max-width: 100%; height: auto; border-radius: 6px; margin: 8px 0; }}

/* ---- Alternatives ---- */
.alternatives {{ display: flex; flex-direction: column; gap: 8px; margin-bottom: 16px; }}
.alt {{
    display: flex; align-items: flex-start; gap: 12px; padding: 12px 16px;
    border-radius: 8px; background: var(--gray-50); border: 2px solid var(--gray-200);
    cursor: pointer; transition: all .15s; font-size: 14px; line-height: 1.6;
}}
.alt:hover {{ border-color: var(--primary); background: var(--primary-light); }}
.alt.selected {{ border-color: var(--primary); background: var(--primary-light); }}
.alt.correct-reveal {{ border-color: var(--success) !important; background: var(--success-light) !important; }}
.alt.wrong-reveal {{ border-color: var(--danger) !important; background: var(--danger-light) !important; }}
.alt.dimmed {{ opacity: .5; }}
.alt-letter {{
    flex-shrink: 0; width: 28px; height: 28px; border-radius: 50%;
    background: var(--gray-200); display: flex; align-items: center; justify-content: center;
    font-weight: 700; font-size: 13px; color: var(--gray-600); transition: all .15s;
}}
.alt.selected .alt-letter {{ background: var(--primary); color: #fff; }}
.alt.correct-reveal .alt-letter {{ background: var(--success); color: #fff; }}
.alt.wrong-reveal .alt-letter {{ background: var(--danger); color: #fff; }}
.alt-text {{ flex: 1; }}
.alt-text img {{ max-width: 100%; height: auto; }}
.alt.locked {{ pointer-events: none; }}

/* ---- Actions / Answer ---- */
.q-actions {{ display: flex; gap: 8px; flex-wrap: wrap; }}
.btn-confirm {{ background: var(--primary); color: #fff; }}
.btn-confirm:hover {{ background: var(--primary-dark); }}
.btn-confirm:disabled {{ background: var(--gray-300); cursor: not-allowed; }}
.btn-show {{ background: var(--gray-100); color: var(--gray-700); }}
.btn-show:hover {{ background: var(--gray-200); }}
.btn-reset {{ background: var(--warning-light); color: var(--gray-700); }}
.btn-reset:hover {{ background: #fde68a; }}

.answer-section {{
    margin-top: 16px; padding: 20px; background: var(--gray-50);
    border-radius: var(--radius); border: 1px solid var(--gray-200);
}}
.gabarito {{ font-size: 15px; margin-bottom: 12px; }}
.gabarito strong {{ color: var(--success); }}
.solution-text-content {{ line-height: 1.7; font-size: 14px; color: var(--gray-700); }}
.solution-text-content img {{ max-width: 100%; height: auto; border-radius: 6px; margin: 8px 0; }}
.video-solution {{ margin-top: 16px; }}
.video-solution strong {{ display: block; margin-bottom: 8px; color: var(--gray-700); }}
.video-solution iframe {{ width: 100%; height: 360px; border-radius: 8px; }}
.video-solution a {{ color: var(--primary); text-decoration: none; font-weight: 600; }}
.video-solution a:hover {{ text-decoration: underline; }}

/* ---- Result banner ---- */
.result-banner {{
    display: none; padding: 12px 16px; border-radius: 8px; margin-bottom: 12px;
    font-weight: 600; font-size: 14px; align-items: center; gap: 8px;
}}
.result-banner.show {{ display: flex; }}
.result-banner.correct {{ background: var(--success-light); color: var(--success); }}
.result-banner.wrong {{ background: var(--danger-light); color: var(--danger); }}

/* ---- Pagination ---- */
.pagination {{ display: flex; justify-content: center; gap: 4px; margin: 20px 0; flex-wrap: wrap; }}
.pagination button {{
    padding: 8px 14px; border: 1px solid var(--gray-200); background: #fff;
    border-radius: 8px; cursor: pointer; font-size: 13px; font-weight: 500;
    transition: all .15s;
}}
.pagination button.active {{ background: var(--primary); color: #fff; border-color: var(--primary); }}
.pagination button:hover:not(.active) {{ background: var(--gray-100); }}

/* ---- Responsive ---- */
@media (max-width: 860px) {{
    .sidebar {{ position: relative; width: 100%; border-right: none; border-bottom: 1px solid var(--gray-200); }}
    .main {{ margin-left: 0; }}
    .container {{ flex-direction: column; }}
    .video-solution iframe {{ height: 220px; }}
}}
</style>
</head>
<body>
<div class="container">
<aside class="sidebar">
    <div class="sidebar-title">Questoes Estrategia Med</div>

    <div class="stats-bar">
        <div class="stat-card stat-total"><span class="stat-num" id="st-total">{total}</span>Exibidas</div>
        <div class="stat-card stat-correct"><span class="stat-num" id="st-correct">0</span>Acertos</div>
        <div class="stat-card stat-wrong"><span class="stat-num" id="st-wrong">0</span>Erros</div>
    </div>

    <details class="filter-section" open>
        <summary>Busca textual</summary>
        <div class="filter-body">
            <input type="text" id="filter-text" placeholder="Buscar no enunciado..." oninput="debounceFilter()">
        </div>
    </details>

    <details class="filter-section">
        <summary>Especialidade</summary>
        <div class="filter-body">
            <select id="filter-specialty" multiple onchange="applyFilters()">{specialty_options}</select>
        </div>
    </details>

    <details class="filter-section">
        <summary>Instituicao</summary>
        <div class="filter-body">
            <select id="filter-institution" multiple onchange="applyFilters()">{institution_options}</select>
        </div>
    </details>

    <details class="filter-section">
        <summary>Ano</summary>
        <div class="filter-body">
            <select id="filter-year" multiple onchange="applyFilters()">{year_options}</select>
        </div>
    </details>

    <details class="filter-section">
        <summary>Banca</summary>
        <div class="filter-body">
            <select id="filter-jury" multiple onchange="applyFilters()">{jury_options}</select>
        </div>
    </details>

    <details class="filter-section" open>
        <summary>Tipo de questao <span class="required-tag">Obrigatorio</span></summary>
        <div class="filter-body">
            <div class="cb-group">
                <label><input type="checkbox" id="ft-true-or-false" checked onchange="applyFilters()"> Certo/Errado</label>
                <label><input type="checkbox" id="ft-multiple-choice" checked onchange="applyFilters()"> Multipla Escolha</label>
                <label><input type="checkbox" id="ft-discursive" checked onchange="applyFilters()"> Discursiva</label>
            </div>
        </div>
    </details>

    <details class="filter-section">
        <summary>Solucoes</summary>
        <div class="filter-body">
            <div class="cb-group">
                <label><input type="checkbox" id="fs-with-text" checked onchange="applyFilters()"> Com solucao em texto</label>
                <label><input type="checkbox" id="fs-without-text" checked onchange="applyFilters()"> Sem solucao em texto</label>
                <label><input type="checkbox" id="fs-with-video" checked onchange="applyFilters()"> Com solucao em video</label>
                <label><input type="checkbox" id="fs-without-video" checked onchange="applyFilters()"> Sem solucao em video</label>
            </div>
        </div>
    </details>

    <details class="filter-section">
        <summary>Vigencia da questao</summary>
        <div class="filter-body">
            <div class="cb-group">
                <label><input type="checkbox" id="fv-outdated" checked onchange="applyFilters()"> Desatualizadas</label>
                <label><input type="checkbox" id="fv-canceled" checked onchange="applyFilters()"> Anuladas</label>
            </div>
        </div>
    </details>

    <details class="filter-section">
        <summary>Situacao</summary>
        <div class="filter-body">
            <div class="cb-group">
                <label><input type="checkbox" id="fst-all" checked onchange="applyFilters()"> Nao respondidas</label>
                <label><input type="checkbox" id="fst-correct" checked onchange="applyFilters()"> Que acertei</label>
                <label><input type="checkbox" id="fst-wrong" checked onchange="applyFilters()"> Que errei</label>
            </div>
        </div>
    </details>

    <button class="btn btn-danger btn-clear" onclick="clearFilters()">Limpar Filtros</button>
    <button class="btn btn-primary btn-clear" onclick="clearAllAnswers()" style="margin-top:8px">Limpar Respostas Salvas</button>
</aside>

<main class="main">
    <div id="pagination-top" class="pagination"></div>
    <div id="questions-container">
        {questions_html}
    </div>
    <div id="pagination-bottom" class="pagination"></div>
</main>
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
    document.getElementById('st-correct').textContent = correct;
    document.getElementById('st-wrong').textContent = wrong;
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
    return Array.from(sel.selectedOptions).filter(o => o.value).map(o => o.value);
}}

function debounceFilter() {{
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(applyFilters, 300);
}}

function applyFilters() {{
    const text = document.getElementById('filter-text').value.toLowerCase();
    const specialties = getSelectedValues('filter-specialty');
    const institutions = getSelectedValues('filter-institution');
    const years = getSelectedValues('filter-year');
    const jurys = getSelectedValues('filter-jury');

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
        if (currentPage > 1) h += '<button onclick="goTo(1)">&laquo;</button><button onclick="goTo('+(currentPage-1)+')">&lsaquo;</button>';
        for (let i = s; i <= e; i++) h += '<button class="'+(i===currentPage?'active':'')+'" onclick="goTo('+i+')">'+i+'</button>';
        if (currentPage < total) h += '<button onclick="goTo('+(currentPage+1)+')">&rsaquo;</button><button onclick="goTo('+total+')">&raquo;</button>';
    }}
    document.getElementById('pagination-top').innerHTML = h;
    document.getElementById('pagination-bottom').innerHTML = h;
}}

function goTo(p) {{ currentPage = p; renderPage(); window.scrollTo(0,0); }}

function clearFilters() {{
    document.getElementById('filter-text').value = '';
    ['filter-specialty','filter-institution','filter-year','filter-jury'].forEach(id => {{
        const sel = document.getElementById(id);
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
filtered = Array.from(document.querySelectorAll('.question'));
renderPage();
</script>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(page_html)

    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"HTML gerado: {output_path} ({size_mb:.1f} MB)")

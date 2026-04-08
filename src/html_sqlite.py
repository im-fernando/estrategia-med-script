import json
import os

from src.database import DB_PATH, get_filter_values


def generate_sqlite_html(
    db_path: str = DB_PATH,
    filter_options: dict = None,
    output_path: str = "questoes.html",
):
    """Gera HTML que carrega o SQLite com sql.js no browser."""
    filter_options = filter_options or {}

    print("Extraindo valores de filtro do banco...")
    fv = get_filter_values(db_path)

    # Usar filter_options completos se disponiveis
    inst_names = sorted(
        {item["name"] for item in filter_options.get("institution_id", []) if item.get("name")}
    ) or fv.get("institution", [])
    banca_names = sorted(
        {item["name"] for item in filter_options.get("jury_id", []) if item.get("name")}
    ) or fv.get("banca", [])
    finalidade_names = sorted(
        {item["name"] for item in filter_options.get("goal_id", []) if item.get("name")}
    ) or fv.get("finalidade", [])

    # Regioes do S3
    regions_data = filter_options.get("regions", [])
    state_map = {}
    if isinstance(regions_data, list):
        for loc in regions_data:
            if loc.get("type") == "STATE" and loc.get("code") and loc.get("state"):
                state_map[loc["code"]] = loc["state"]
    db_regions = fv.get("region", [])
    all_codes = sorted(set(db_regions) | set(state_map.keys()))
    region_opts = [{"c": c, "l": f"{c} - {state_map.get(c, c)}"} for c in all_codes if c]

    years = sorted(fv.get("year", []), reverse=True)
    specs = fv.get("specialties", [])

    db_filename = os.path.basename(db_path)

    def _js_arr(items):
        return json.dumps(items, ensure_ascii=False)

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Estrategia Med — Questoes</title>
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
  --r: 16px;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  background: var(--bg-dark);
  color: var(--text);
  line-height: 1.6;
  padding: 20px;
}}
.container {{ max-width: 1100px; margin: 0 auto; }}

.header {{
  text-align: center;
  margin-bottom: 28px;
  padding: 28px 24px;
  background: linear-gradient(135deg, var(--bg-card) 0%, #1f2937 100%);
  border-radius: var(--r);
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
.stats {{ display: flex; justify-content: center; gap: 28px; margin-top: 22px; flex-wrap: wrap; }}
.stat {{ text-align: center; }}
.stat-value {{ font-size: 1.75rem; font-weight: 700; color: var(--accent); }}
.stat-label {{ font-size: 0.85rem; color: var(--text-muted); }}

.filters-section {{
  background: var(--bg-card);
  border-radius: var(--r);
  padding: 22px;
  margin-bottom: 22px;
  border: 1px solid var(--border);
}}
.filters-header {{ display: flex; justify-content: space-between; align-items: center; cursor: pointer; user-select: none; }}
.filters-header h3 {{ color: var(--accent); display: flex; align-items: center; gap: 10px; font-size: 1rem; font-weight: 600; }}
.filters-toggle {{ color: var(--text-muted); font-size: 0.9rem; }}
.filters-content {{
  display: none;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 18px;
  margin-top: 20px;
}}
.filters-content.is-open {{ display: grid; }}
.filter-group {{ display: flex; flex-direction: column; gap: 8px; }}
.filter-group > label {{
  font-weight: 600;
  color: var(--text-muted);
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
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
.search-input:focus {{ outline: none; border-color: var(--accent); box-shadow: 0 0 0 3px rgba(0, 212, 170, 0.2); }}
.search-icon {{ position: absolute; left: 18px; top: 50%; transform: translateY(-50%); color: var(--text-muted); pointer-events: none; }}

.tree-filter-scroll {{
  max-height: 280px;
  overflow-y: auto;
  overflow-x: hidden;
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 8px;
  background: var(--bg-dark);
}}
.tree-leaf {{ padding: 5px 6px; border-radius: 8px; margin: 2px 0; }}
.tree-leaf:hover {{ background: rgba(255,255,255,0.04); }}
.tree-label {{ display: flex; align-items: flex-start; gap: 10px; cursor: pointer; font-size: 0.85rem; color: var(--text-muted); width: 100%; line-height: 1.45; }}
.tree-name {{ flex: 1; color: var(--text); }}

/* Checkboxes — identidade */
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

.questions-container {{ min-height: 200px; }}
#loading {{ text-align: center; padding: 60px 20px; font-size: 16px; color: var(--text-muted); }}
.q {{ background: var(--bg-card); border-radius: var(--r); padding: 28px; margin-bottom: 22px; border: 1px solid var(--border); transition: all 0.25s ease; }}
.q:hover {{ border-color: var(--accent); box-shadow: 0 0 28px rgba(0, 212, 170, 0.08); }}
.q.q-ok {{ border-color: rgba(34, 197, 94, 0.5); }}
.q.q-err {{ border-color: rgba(239, 68, 68, 0.5); }}
.qh {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px; padding-bottom: 14px; border-bottom: 1px solid var(--border); flex-wrap: wrap; gap: 10px; }}
.qn {{ font-weight: 700; font-size: 1.05rem; color: var(--accent); }}
.badge {{ padding: 4px 12px; border-radius: 20px; font-size: 0.72rem; font-weight: 600; margin-left: 6px; display: inline-flex; }}
.badge-t {{ background: rgba(0, 212, 170, 0.12); color: var(--accent); }}
.badge-c {{ background: rgba(239, 68, 68, 0.12); color: var(--incorrect); }}
.badge-o {{ background: rgba(245, 158, 11, 0.15); color: #fbbf24; }}
.qi {{ font-size: 0.9rem; color: var(--text-muted); margin-bottom: 10px; }}
.qs {{ font-size: 0.9rem; color: var(--accent); font-weight: 600; margin-bottom: 14px; }}
.qb {{ line-height: 1.8; margin-bottom: 22px; font-size: 1.02rem; color: var(--text); }}
.qb img {{ max-width: 100%; height: auto; border-radius: 8px; margin: 10px 0; }}
.alts {{ display: flex; flex-direction: column; gap: 12px; margin-bottom: 18px; }}
.alt {{ display: flex; align-items: flex-start; gap: 14px; padding: 16px 18px; background: var(--bg-hover); border-radius: 12px; cursor: pointer; transition: all 0.2s ease; border: 2px solid transparent; font-size: 0.95rem; line-height: 1.55; color: var(--text); }}
.alt:hover {{ background: #2a2a2a; transform: translateX(4px); }}
.alt.sel {{ border-color: var(--accent); background: rgba(0, 212, 170, 0.1); }}
.alt.c-ok {{ border-color: var(--correct)!important; background: rgba(34, 197, 94, 0.1)!important; }}
.alt.c-err {{ border-color: var(--incorrect)!important; background: rgba(239, 68, 68, 0.1)!important; }}
.alt.dim {{ opacity: 0.42; }}
.alt.lock {{ pointer-events: none; cursor: default; }}
.altl {{ width: 36px; height: 36px; display: flex; align-items: center; justify-content: center; background: var(--border); border-radius: 8px; font-weight: 700; flex-shrink: 0; font-size: 0.9rem; color: var(--text); transition: all 0.2s ease; }}
.alt.sel .altl {{ background: var(--accent); color: var(--bg-dark); }}
.alt.c-ok .altl {{ background: var(--correct); color: #fff; }}
.alt.c-err .altl {{ background: var(--incorrect); color: #fff; }}
.altb {{ flex: 1; padding-top: 5px; }}
.altb img {{ max-width: 100%; height: auto; }}
.acts {{ display: flex; gap: 10px; flex-wrap: wrap; margin-top: 4px; }}
.btn {{ border: none; padding: 10px 18px; border-radius: 10px; font-size: 0.88rem; font-weight: 600; cursor: pointer; transition: all 0.2s ease; }}
.btn-c {{ background: var(--accent); color: var(--bg-dark); }}
.btn-c:hover {{ filter: brightness(1.08); }}
.btn-c:disabled {{ opacity: 0.35; cursor: not-allowed; filter: none; }}
.btn-s {{ background: var(--bg-hover); border: 1px solid var(--border); color: var(--text); }}
.btn-s:hover {{ border-color: var(--accent); color: var(--accent); }}
.btn-r {{ background: rgba(245, 158, 11, 0.15); border: 1px solid rgba(245, 158, 11, 0.35); color: #fbbf24; }}
.res {{ display: none; padding: 12px 16px; border-radius: 10px; margin-bottom: 12px; font-weight: 600; font-size: 0.9rem; }}
.res.show {{ display: flex; align-items: center; }}
.res-ok {{ background: rgba(34, 197, 94, 0.15); color: var(--correct); }}
.res-err {{ background: rgba(239, 68, 68, 0.15); color: var(--incorrect); }}
.ans {{ margin-top: 22px; padding: 22px; background: linear-gradient(135deg, #1f2937 0%, var(--bg-card) 100%); border-radius: 12px; border-left: 4px solid var(--accent); display: none; }}
.ans h4 {{ margin-bottom: 12px; color: var(--correct); font-size: 1rem; }}
.ans-txt {{ line-height: 1.75; font-size: 0.92rem; color: var(--text-muted); }}
.ans-txt img {{ max-width: 100%; height: auto; border-radius: 8px; margin: 8px 0; }}
.vid {{ margin-top: 16px; }}
.vid iframe {{ width: 100%; height: 340px; border-radius: 10px; border: none; }}
.vid a {{ color: var(--accent); font-weight: 600; }}
.pag {{ display: flex; justify-content: center; align-items: center; gap: 8px; margin: 26px 0; flex-wrap: wrap; }}
.pag button {{ padding: 10px 14px; background: var(--bg-hover); border: 1px solid var(--border); border-radius: 8px; color: var(--text); cursor: pointer; font-weight: 500; font-size: 0.88rem; transition: all 0.2s ease; }}
.pag button:hover:not(:disabled) {{ background: var(--accent); color: var(--bg-dark); border-color: var(--accent); }}
.pag button.act {{ background: var(--accent); color: var(--bg-dark); border-color: var(--accent); }}
@media (max-width: 768px) {{ body {{ padding: 12px; }} .q {{ padding: 20px; }} .vid iframe {{ height: 220px; }} .filters-content.is-open {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>
<div class="container">
  <header class="header">
    <h1>📚 Estrategia Med — Questoes</h1>
    <p id="total-label">Carregando banco de dados...</p>
    <div class="stats">
      <div class="stat"><div class="stat-value" id="st-t">-</div><div class="stat-label">Exibindo</div></div>
      <div class="stat"><div class="stat-value" id="st-c">0</div><div class="stat-label">Acertos</div></div>
      <div class="stat"><div class="stat-value" id="st-w">0</div><div class="stat-label">Erros</div></div>
      <div class="stat"><div class="stat-value" id="st-pct">-</div><div class="stat-label">Aproveitamento</div></div>
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
          <input type="text" class="search-input" id="ftxt" placeholder="Digite palavras-chave..." oninput="df()">
        </div>
      </div>
      <div class="filter-group" style="grid-column: 1 / -1;">
        <label>Especialidade e assuntos</label>
        <div class="tree-filter-scroll" id="f-spec"></div>
      </div>
      <div class="filter-group" style="grid-column: 1 / -1;">
        <label>Instituicao</label>
        <div class="tree-filter-scroll" id="f-inst"></div>
      </div>
      <div class="filter-group" style="grid-column: 1 / -1;">
        <label>Ano</label>
        <div class="tree-filter-scroll" id="f-year"></div>
      </div>
      <div class="filter-group" style="grid-column: 1 / -1;">
        <label>Finalidade</label>
        <div class="tree-filter-scroll" id="f-fin"></div>
      </div>
      <div class="filter-group" style="grid-column: 1 / -1;">
        <label>Banca</label>
        <div class="tree-filter-scroll" id="f-banca"></div>
      </div>
      <div class="filter-group" style="grid-column: 1 / -1;">
        <label>Regiao</label>
        <div class="tree-filter-scroll" id="f-reg"></div>
      </div>
      <div class="filter-group">
        <label>Tipo de questao</label>
        <div class="tree-filter-scroll">
          <div class="tree-leaf"><label class="tree-label"><input type="checkbox" class="ft" value="MULTIPLE_CHOICE" checked onchange="af()"><span class="tree-name">Multipla escolha</span></label></div>
          <div class="tree-leaf"><label class="tree-label"><input type="checkbox" class="ft" value="TRUE_OR_FALSE" checked onchange="af()"><span class="tree-name">Certo/Errado</span></label></div>
          <div class="tree-leaf"><label class="tree-label"><input type="checkbox" class="ft" value="DISCURSIVE" checked onchange="af()"><span class="tree-name">Discursiva</span></label></div>
        </div>
      </div>
      <div class="filter-group">
        <label>Vigencia</label>
        <div class="tree-filter-scroll">
          <div class="tree-leaf"><label class="tree-label"><input type="checkbox" id="fv-out" checked onchange="af()"><span class="tree-name">Desatualizadas</span></label></div>
          <div class="tree-leaf"><label class="tree-label"><input type="checkbox" id="fv-can" checked onchange="af()"><span class="tree-name">Anuladas</span></label></div>
        </div>
      </div>
      <div class="filter-group">
        <label>Situacao</label>
        <div class="tree-filter-scroll">
          <div class="tree-leaf"><label class="tree-label"><input type="checkbox" id="fs-na" checked onchange="af()"><span class="tree-name">Nao respondidas</span></label></div>
          <div class="tree-leaf"><label class="tree-label"><input type="checkbox" id="fs-ok" checked onchange="af()"><span class="tree-name">Que acertei</span></label></div>
          <div class="tree-leaf"><label class="tree-label"><input type="checkbox" id="fs-err" checked onchange="af()"><span class="tree-name">Que errei</span></label></div>
        </div>
      </div>
    </div>
    <div style="margin-top: 18px; padding-top: 16px; border-top: 1px solid var(--border); display:flex; justify-content:flex-end;">
      <button class="btn btn-s" onclick="clr()">Limpar filtros</button>
    </div>
  </section>

  <div id="loading">Carregando banco de dados... Aguarde.</div>
  <div id="pag-t" class="pag"></div>
  <div id="qc" class="questions-container"></div>
  <div id="pag-b" class="pag"></div>
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.12.0/sql-wasm.js"></script>
<script>
const DB_FILE='{db_filename}';
const PP=50;
let db,cp=1,totalFiltered=0,SA=JSON.parse(localStorage.getItem('em_ans')||'{{}}'  );
const SPECS={_js_arr(specs)};
const INSTS={_js_arr(inst_names)};
const YEARS={_js_arr([str(y) for y in years])};
const FINS={_js_arr(finalidade_names)};
const BANCAS={_js_arr(banca_names)};
const REGS={_js_arr(region_opts)};
let dt;function df(){{clearTimeout(dt);dt=setTimeout(af,400)}}
function toggleFilters(){{const box=document.getElementById('filters-content');const t=document.getElementById('filters-toggle-text');if(!box||!t)return;const open=box.classList.toggle('is-open');t.textContent=open?'▲ Recolher':'▼ Expandir';}}
function esc(s){{return s?String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'):''}}
function fill(id,items,cls){{let h='';items.forEach(v=>h+=`<div class=\"tree-leaf\"><label class=\"tree-label\"><input type=\"checkbox\" class=\"${{cls}}\" value=\"${{esc(v)}}\" onchange=\"af()\"><span class=\"tree-name\">${{esc(v)}}</span></label></div>`);document.getElementById(id).innerHTML=h}}
function gv(cls){{return Array.from(document.querySelectorAll('.'+cls+':checked')).map(c=>c.value)}}

async function init(){{
  const SQL=await initSqlJs({{locateFile:f=>'https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.12.0/'+f}});
  const resp=await fetch(DB_FILE);
  const buf=await resp.arrayBuffer();
  db=new SQL.Database(new Uint8Array(buf));
  const tot=db.exec("SELECT COUNT(*) FROM questions")[0].values[0][0];
  document.getElementById('total-label').textContent=tot+' questoes no banco';
  document.getElementById('loading').style.display='none';
  fill('f-spec',SPECS,'fs');fill('f-inst',INSTS,'fi');fill('f-year',YEARS,'fy');
  fill('f-fin',FINS,'ff');fill('f-banca',BANCAS,'fb');
  let rh='';REGS.forEach(r=>rh+='<label><input type=checkbox class="fr" value="'+esc(r.c)+'" onchange="af()"><span>'+esc(r.l)+'</span></label>');
  document.getElementById('f-reg').innerHTML=rh;
  updStats();af();
}}

function buildWhere(){{
  let w=[],p=[];
  const txt=document.getElementById('ftxt').value.trim();
  if(txt){{w.push("statement LIKE ?");p.push('%'+txt+'%')}}
  const sp=gv('fs');if(sp.length){{let conds=sp.map(s=>"topics LIKE ?");w.push('('+conds.join(' OR ')+')');sp.forEach(s=>p.push('%'+JSON.stringify(s).slice(1,-1)+'%'))}}
  const ins=gv('fi');if(ins.length){{w.push("institution IN ("+ins.map(()=>'?').join(',')+")");p.push(...ins)}}
  const yr=gv('fy');if(yr.length){{w.push("year IN ("+yr.map(()=>'?').join(',')+")");yr.forEach(y=>p.push(parseInt(y)))}}
  const fn=gv('ff');if(fn.length){{w.push("finalidade IN ("+fn.map(()=>'?').join(',')+")");p.push(...fn)}}
  const bk=gv('fb');if(bk.length){{w.push("banca IN ("+bk.map(()=>'?').join(',')+")");p.push(...bk)}}
  const rg=gv('fr');if(rg.length){{w.push("region IN ("+rg.map(()=>'?').join(',')+")");p.push(...rg)}}
  const tp=Array.from(document.querySelectorAll('.ft:checked')).map(c=>c.value);
  if(tp.length&&tp.length<3){{w.push("answer_type IN ("+tp.map(()=>'?').join(',')+")");p.push(...tp)}}
  if(!document.getElementById('fv-out').checked)w.push("labels NOT LIKE '%OUTDATED%'");
  if(!document.getElementById('fv-can').checked)w.push("labels NOT LIKE '%CANCELED%'");
  return {{where:w.length?'WHERE '+w.join(' AND '):'',params:p}};
}}

function af(){{
  const {{where,params}}=buildWhere();
  // Count
  const cr=db.exec("SELECT COUNT(*) FROM questions "+where,params);
  totalFiltered=cr.length?cr[0].values[0][0]:0;
  document.getElementById('st-t').textContent=totalFiltered;
  cp=1;rp();
}}

function rp(){{
  const {{where,params}}=buildWhere();
  const offset=(cp-1)*PP;
  const rows=db.exec("SELECT id,statement,answer_type,year,institution,banca,finalidade,region,labels,topics,correct_letter,solution,has_video,video_url FROM questions "+where+" ORDER BY ROWID LIMIT "+PP+" OFFSET "+offset,params);
  let h='';
  if(rows.length&&rows[0].values.length){{
    rows[0].values.forEach((r,i)=>{{
      const q={{id:r[0],st:r[1],tp:r[2],yr:r[3],inst:r[4],bk:r[5],fn:r[6],rg:r[7],lb:JSON.parse(r[8]||'[]'),to:JSON.parse(r[9]||'[]'),cr:r[10],sl:r[11],hv:r[12],vu:r[13]}};
      // Load alternatives
      const ar=db.exec("SELECT letter,body,correct,answer_pct FROM alternatives WHERE question_id=? ORDER BY letter",[q.id]);
      q.al=ar.length?ar[0].values.map(a=>({{l:a[0],b:a[1],c:!!a[2],pct:a[3]}})):[];
      h+=rq(q,offset+i);
    }});
  }}
  document.getElementById('qc').innerHTML=h||'<p style="text-align:center;color:var(--g5);padding:40px">Nenhuma questao encontrada com esses filtros.</p>';
  rpag();
}}

function rq(q,idx){{
  const a=SA[q.id];const lk=!!a;
  const tops=q.to.map(t=>t.n).join(', ')||'Sem especialidade';
  const tl={{'MULTIPLE_CHOICE':'Multipla Escolha','TRUE_OR_FALSE':'Certo/Errado','DISCURSIVE':'Discursiva'}}[q.tp]||q.tp;
  let lbH='';(q.lb||[]).forEach(l=>{{if(l.toUpperCase().includes('CANCEL'))lbH+='<span class="badge badge-c">Anulada</span>';else if(l.toUpperCase().includes('OUTDAT'))lbH+='<span class="badge badge-o">Desatualizada</span>'}});
  let altH='<div class="alts">';
  q.al.forEach(al=>{{let cls='alt';if(lk){{cls+=' lock';if(a.s===al.l)cls+=al.c?' c-ok':' c-err';else if(al.c)cls+=' c-ok';else cls+=' dim'}};altH+=`<div class="${{cls}}" data-l="${{al.l}}" data-c="${{al.c}}" onclick="sa(this,'${{q.id}}')"><div class="altl">${{al.l}}</div><div class="altb">${{al.b}}</div></div>`}});
  altH+='</div>';
  let resH=lk?`<div class="res ${{a.c?'res-ok':'res-err'}}">${{a.c?'Voce acertou!':'Voce errou. Gabarito: '+q.cr}}</div>`:'';
  let solH=q.sl?`<div class="ans-txt">${{q.sl}}</div>`:'';
  let vidH='';
  if(q.vu){{let eu='';const v=q.vu;if(v.includes('youtube.com/watch'))eu='https://www.youtube.com/embed/'+v.split('v=')[1].split('&')[0];else if(v.includes('youtu.be/'))eu='https://www.youtube.com/embed/'+v.split('youtu.be/')[1].split('?')[0];if(eu)vidH=`<div class="vid"><iframe src="${{eu}}" allowfullscreen loading=lazy></iframe></div>`;else vidH=`<div class="vid"><a href="${{v}}" target=_blank>Assistir video</a></div>`}}
  return `<div class="q ${{lk?(a.c?'q-ok':'q-err'):''}}" id="q-${{q.id}}">
<div class="qh"><span class="qn">#${{idx+1}}</span><div><span class="badge badge-t">${{esc(tl)}}</span>${{lbH}}</div></div>
<div class="qi">${{esc(q.inst)}} ${{q.yr||''}} | ${{esc(q.bk)}}</div>
<div class="qs">${{esc(tops)}}</div>
<div class="qb">${{q.st}}</div>
${{altH}}${{resH}}
<div class="acts">
<button class="btn btn-c" onclick="ca(this,'${{q.id}}')" ${{lk?'style="display:none"':'disabled'}}>Confirmar</button>
<button class="btn btn-s" onclick="ta(this)">Ver Gabarito</button>
${{lk?`<button class="btn btn-r" onclick="ra('${{q.id}}')">Refazer</button>`:''}}
</div>
<div class="ans"><h4>Gabarito: ${{q.cr}}</h4>${{solH}}${{vidH}}</div>
</div>`;
}}

function sa(el,qid){{if(el.classList.contains('lock'))return;el.closest('.q').querySelectorAll('.alt').forEach(a=>a.classList.remove('sel'));el.classList.add('sel');el.closest('.q').querySelector('.btn-c').disabled=false}}
function ca(btn,qid){{
  const p=btn.closest('.q'),sel=p.querySelector('.alt.sel');if(!sel)return;
  const l=sel.dataset.l,c=sel.dataset.c==='true';
  p.querySelectorAll('.alt').forEach(a=>{{a.classList.add('lock');if(a.dataset.c==='true')a.classList.add('c-ok');else if(a===sel&&!c)a.classList.add('c-err');else if(a!==sel)a.classList.add('dim')}});
  p.classList.add(c?'q-ok':'q-err');
  const cr=p.querySelector('.ans h4').textContent.replace('Gabarito: ','');
  const r=document.createElement('div');r.className='res '+(c?'res-ok':'res-err');r.textContent=c?'Voce acertou!':'Voce errou. Gabarito: '+cr;
  btn.parentNode.before(r);btn.style.display='none';
  const rb=document.createElement('button');rb.className='btn btn-r';rb.textContent='Refazer';rb.onclick=()=>ra(qid);btn.parentNode.appendChild(rb);
  SA[qid]={{s:l,c:c}};localStorage.setItem('em_ans',JSON.stringify(SA));updStats();
}}
function ra(qid){{delete SA[qid];localStorage.setItem('em_ans',JSON.stringify(SA));rp();updStats()}}
function ta(btn){{const a=btn.closest('.q').querySelector('.ans');a.style.display=a.style.display==='block'?'none':'block';btn.textContent=a.style.display==='block'?'Ocultar':'Ver Gabarito'}}
function updStats(){{let c=0,w=0;Object.values(SA).forEach(a=>{{if(a.c)c++;else w++}});document.getElementById('st-c').textContent=c;document.getElementById('st-w').textContent=w;const t=c+w;document.getElementById('st-pct').textContent=t?Math.round(c/t*100)+'%':'-'}}
function rpag(){{
  const t=Math.ceil(totalFiltered/PP);let h='';
  if(t>1){{const mx=10;let s=Math.max(1,cp-mx/2|0),e=Math.min(t,s+mx-1);if(e-s<mx-1)s=Math.max(1,e-mx+1);
  if(cp>1)h+='<button onclick="gp(1)">&laquo;</button><button onclick="gp('+(cp-1)+')">&lsaquo;</button>';
  for(let i=s;i<=e;i++)h+='<button class="'+(i===cp?'act':'')+'" onclick="gp('+i+')">'+i+'</button>';
  if(cp<t)h+='<button onclick="gp('+(cp+1)+')">&rsaquo;</button><button onclick="gp('+t+')">&raquo;</button>'}}
  document.getElementById('pag-t').innerHTML=h;document.getElementById('pag-b').innerHTML=h;
}}
function gp(p){{cp=p;rp();window.scrollTo(0,0)}}
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
        f.write(html)

    html_size = os.path.getsize(output_path) / (1024 * 1024)
    db_size = os.path.getsize(db_path) / (1024 * 1024)
    print(f"HTML gerado: {output_path} ({html_size:.1f} MB)")
    print(f"Banco: {db_path} ({db_size:.1f} MB)")
    print(f"Abra {output_path} no navegador (precisa do {db_filename} na mesma pasta).")

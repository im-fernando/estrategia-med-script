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
<style>
:root{{--p:#2563eb;--pd:#1d4ed8;--pl:#dbeafe;--ok:#16a34a;--okl:#dcfce7;--okb:#86efac;--err:#dc2626;--errl:#fee2e2;--errb:#fca5a5;--w:#f59e0b;--wl:#fef3c7;--g0:#fff;--g1:#f9fafb;--g2:#e5e7eb;--g3:#d1d5db;--g5:#6b7280;--g7:#374151;--g8:#1f2937;--r:10px}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:var(--g1);color:var(--g8)}}
.wrap{{display:flex;min-height:100vh}}
.side{{width:340px;background:var(--g0);padding:20px;border-right:1px solid var(--g2);position:fixed;top:0;left:0;bottom:0;overflow-y:auto;z-index:10}}
.main{{margin-left:340px;padding:24px;flex:1;max-width:960px}}
.side h2{{font-size:18px;font-weight:700;margin-bottom:8px}}
.side .sub{{font-size:12px;color:var(--g5);margin-bottom:14px}}
.stats{{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:16px}}
.st{{flex:1;min-width:60px;text-align:center;padding:8px 4px;border-radius:var(--r);font-size:11px;font-weight:500}}
.st b{{font-size:18px;display:block}}
.st-t{{background:var(--pl);color:var(--pd)}}.st-c{{background:var(--okl);color:var(--ok)}}.st-w{{background:var(--errl);color:var(--err)}}.st-pct{{background:var(--wl);color:var(--w)}}
.fg{{margin-bottom:10px}}.fg label{{display:block;font-weight:600;font-size:12px;color:var(--g5);margin-bottom:4px}}
.fg input[type=text]{{width:100%;padding:8px;border:1px solid var(--g3);border-radius:8px;font-size:13px}}
.fscroll{{max-height:150px;overflow-y:auto;border:1px solid var(--g2);border-radius:8px;padding:6px}}
.fscroll label{{display:flex;align-items:center;gap:6px;font-size:12px;color:var(--g7);padding:2px 0;cursor:pointer}}
.fscroll input{{accent-color:var(--p);width:14px;height:14px}}
.cbg{{display:flex;flex-direction:column;gap:3px}}.cbg label{{display:flex;align-items:center;gap:6px;font-size:12px;cursor:pointer}}.cbg input{{accent-color:var(--p);width:15px;height:15px}}
details summary{{font-size:12px;font-weight:600;color:var(--g5);cursor:pointer;padding:6px 0;user-select:none}}
.btn{{border:none;padding:7px 14px;border-radius:8px;font-size:12px;font-weight:600;cursor:pointer;transition:all .15s}}
.btn-d{{background:var(--errl);color:var(--err);width:100%;margin-top:12px}}
#loading{{text-align:center;padding:60px 20px;font-size:16px;color:var(--g5)}}
.q{{background:var(--g0);border-radius:var(--r);padding:20px;margin-bottom:14px;box-shadow:0 1px 3px rgba(0,0,0,.08);border:2px solid var(--g2);transition:border-color .2s}}
.q.q-ok{{border-color:var(--okb)}}.q.q-err{{border-color:var(--errb)}}
.qh{{display:flex;justify-content:space-between;align-items:center;margin-bottom:4px}}
.qn{{font-weight:700;color:var(--p);font-size:14px}}
.badge{{display:inline-flex;padding:2px 8px;border-radius:20px;font-size:10px;font-weight:600;margin-left:4px}}
.badge-t{{background:var(--pl);color:var(--pd)}}.badge-c{{background:var(--errl);color:var(--err)}}.badge-o{{background:var(--wl);color:var(--w)}}
.qi{{font-size:11px;color:var(--g5);margin-bottom:4px}}.qs{{font-size:11px;color:var(--p);font-weight:600;margin-bottom:10px}}
.qb{{line-height:1.7;margin-bottom:14px;font-size:14px}}.qb img{{max-width:100%;height:auto}}
.alts{{display:flex;flex-direction:column;gap:6px;margin-bottom:14px}}
.alt{{display:flex;align-items:flex-start;gap:10px;padding:10px 14px;border-radius:8px;background:var(--g1);border:2px solid var(--g2);cursor:pointer;font-size:13px;line-height:1.6;transition:all .15s}}
.alt:hover{{border-color:var(--p);background:var(--pl)}}.alt.sel{{border-color:var(--p);background:var(--pl)}}
.alt.c-ok{{border-color:var(--ok)!important;background:var(--okl)!important}}.alt.c-err{{border-color:var(--err)!important;background:var(--errl)!important}}.alt.dim{{opacity:.45}}.alt.lock{{pointer-events:none}}
.altl{{flex-shrink:0;width:26px;height:26px;border-radius:50%;background:var(--g2);display:flex;align-items:center;justify-content:center;font-weight:700;font-size:12px;color:var(--g5)}}
.alt.sel .altl{{background:var(--p);color:#fff}}.alt.c-ok .altl{{background:var(--ok);color:#fff}}.alt.c-err .altl{{background:var(--err);color:#fff}}
.altb{{flex:1}}.altb img{{max-width:100%;height:auto}}
.acts{{display:flex;gap:6px;flex-wrap:wrap}}
.btn-c{{background:var(--p);color:#fff}}.btn-c:disabled{{background:var(--g3)}}.btn-s{{background:var(--g1);color:var(--g7)}}.btn-r{{background:var(--wl);color:var(--g7)}}
.res{{padding:10px 14px;border-radius:8px;font-weight:600;font-size:13px;margin-bottom:10px}}
.res-ok{{background:var(--okl);color:var(--ok)}}.res-err{{background:var(--errl);color:var(--err)}}
.ans{{margin-top:14px;padding:16px;background:var(--g1);border-radius:var(--r);border:1px solid var(--g2);display:none}}
.ans h4{{margin-bottom:8px;color:var(--ok)}}.ans-txt{{line-height:1.7;font-size:13px}}.ans-txt img{{max-width:100%;height:auto}}
.vid{{margin-top:12px}}.vid iframe{{width:100%;height:340px;border-radius:8px;border:none}}
.pag{{display:flex;justify-content:center;gap:4px;margin:16px 0;flex-wrap:wrap}}
.pag button{{padding:6px 12px;border:1px solid var(--g2);background:var(--g0);border-radius:6px;cursor:pointer;font-size:12px}}
.pag button.act{{background:var(--p);color:#fff;border-color:var(--p)}}
@media(max-width:860px){{.side{{position:relative;width:100%;border-right:none;border-bottom:1px solid var(--g2)}}.main{{margin-left:0}}.wrap{{flex-direction:column}}.vid iframe{{height:220px}}}}
</style>
</head>
<body>
<div class="wrap">
<aside class="side">
<h2>Estrategia Med</h2>
<p class="sub" id="total-label">Carregando banco de dados...</p>
<div class="stats">
<div class="st st-t"><b id="st-t">-</b>Exibindo</div>
<div class="st st-c"><b id="st-c">0</b>Acertos</div>
<div class="st st-w"><b id="st-w">0</b>Erros</div>
<div class="st st-pct"><b id="st-pct">-</b>Aproveit.</div>
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
<div id="loading">Carregando banco de dados... Aguarde.</div>
<div id="pag-t" class="pag"></div>
<div id="qc"></div>
<div id="pag-b" class="pag"></div>
</main>
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
function esc(s){{return s?String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'):''}}
function fill(id,items,cls){{let h='';items.forEach(v=>h+='<label><input type=checkbox class="'+cls+'" value="'+esc(v)+'" onchange="af()"><span>'+esc(v)+'</span></label>');document.getElementById(id).innerHTML=h}}
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

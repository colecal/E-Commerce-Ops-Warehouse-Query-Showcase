const $ = (id) => document.getElementById(id);

let chart;

function isoDate(d){
  const pad = (n)=> String(n).padStart(2,'0');
  return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}`;
}

function setDefaults(){
  const today = new Date();
  const end = new Date(today);
  const start = new Date(today); start.setDate(start.getDate()-90);
  $("startDate").value = isoDate(start);
  $("endDate").value = isoDate(end);

  const ms = new Date(today); ms.setDate(1);
  const me = new Date(today); me.setDate(1); me.setMonth(me.getMonth()-5);
  $("startMonth").value = isoDate(me);
  $("endMonth").value = isoDate(ms);
}

async function apiHealth(){
  const el = $("health");
  const dot = document.querySelector('.dot');
  try{
    const r = await fetch('/api/health');
    const j = await r.json();
    if(j.ok){
      dot.classList.add('ok');
      el.textContent = 'API online · Postgres connected';
    } else {
      dot.classList.add('bad');
      el.textContent = 'API error';
    }
  }catch(e){
    dot.classList.add('bad');
    el.textContent = 'API offline (is docker-compose running?)';
  }
}

function renderCards(queries){
  const wrap = $("queryCards");
  wrap.innerHTML = '';
  for(const q of queries){
    const div = document.createElement('div');
    div.className = 'qcard';
    div.innerHTML = `
      <div class="qtitle"><strong>${q.title}</strong><span class="qid">${q.id}</span></div>
      <div class="qdesc">${q.description}</div>
    `;
    div.onclick = ()=> runQuery(q);
    wrap.appendChild(div);
  }
}

function tableFrom(cols, rows){
  const t = $("resultTable");
  t.innerHTML = '';
  if(cols.length === 0){
    t.innerHTML = '<tr><td style="padding:12px; color: rgba(255,255,255,.65)">No rows returned.</td></tr>';
    return;
  }
  const thead = document.createElement('thead');
  const trh = document.createElement('tr');
  for(const c of cols){
    const th = document.createElement('th'); th.textContent = c; trh.appendChild(th);
  }
  thead.appendChild(trh);
  t.appendChild(thead);
  const tb = document.createElement('tbody');
  for(const r of rows.slice(0, 400)){
    const tr = document.createElement('tr');
    for(const v of r){
      const td = document.createElement('td');
      td.textContent = (v === null || v === undefined) ? '' : String(v);
      tr.appendChild(td);
    }
    tb.appendChild(tr);
  }
  t.appendChild(tb);
}

function destroyChart(){
  if(chart){ chart.destroy(); chart = undefined; }
}

function plotIfPossible(result){
  destroyChart();
  const canvas = $("chart");
  const {columns, rows, query_id} = result;
  if(rows.length === 0) return;

  // Lightweight heuristics: plot first column as x, second as y when numeric-ish.
  const xIdx = 0;
  const yIdx = Math.min(2, columns.length-1);
  if(yIdx <= 0) return;

  const pts = rows
    .map(r => ({x: r[xIdx], y: Number(r[yIdx])}))
    .filter(p => Number.isFinite(p.y));
  if(pts.length < 3) return;

  chart = new Chart(canvas, {
    type: 'line',
    data: {
      datasets: [{
        label: `${query_id}: ${columns[yIdx]}`,
        data: pts,
        borderColor: 'rgba(124,92,255,.95)',
        backgroundColor: 'rgba(124,92,255,.25)',
        borderWidth: 2,
        pointRadius: 0,
        tension: 0.25,
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { labels: { color: 'rgba(255,255,255,.8)' } }
      },
      scales: {
        x: { ticks: { color: 'rgba(255,255,255,.65)' }, grid: { color: 'rgba(255,255,255,.06)' } },
        y: { ticks: { color: 'rgba(255,255,255,.65)' }, grid: { color: 'rgba(255,255,255,.06)' } },
      }
    }
  });
}

async function runQuery(q){
  const params = new URLSearchParams();
  const sd = $("startDate").value;
  const ed = $("endDate").value;
  const sm = $("startMonth").value;
  const em = $("endMonth").value;

  for(const p of q.params){
    if(p === 'start_date') params.set('start_date', sd);
    if(p === 'end_date') params.set('end_date', ed);
    if(p === 'start_month') params.set('start_month', sm);
    if(p === 'end_month') params.set('end_month', em);
  }

  $("resultTitle").textContent = q.title;
  $("resultMeta").textContent = 'Running…';

  const url = `/api/query/${q.id}?${params.toString()}`;
  const r = await fetch(url);
  const j = await r.json();

  $("resultMeta").textContent = `${j.row_count} rows · ${Object.entries(j.params).map(([k,v])=>`${k}=${v}`).join(' · ')}`;
  $("rawJson").textContent = JSON.stringify(j, null, 2);
  tableFrom(j.columns, j.rows);
  plotIfPossible(j);
}

async function refresh(){
  const r = await fetch('/api/queries');
  const j = await r.json();
  renderCards(j.queries);
}

$("refresh").onclick = refresh;

setDefaults();
apiHealth();
refresh();

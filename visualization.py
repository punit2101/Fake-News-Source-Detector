import os, math, json, collections
import networkx as nx


INPUT_PATH   = "data.txt"
OUT_HTML = "outputs/source_detection_enhanced.html"
MAX_SOURCES  = 3

if not os.path.exists(INPUT_PATH):
    raise FileNotFoundError(f"Missing {INPUT_PATH}")

with open(INPUT_PATH) as f:
    lines = [ln.strip() for ln in f if ln.strip()]

n, m           = map(int, lines[0].split())
edges_raw      = [tuple(map(int, lines[i].split())) for i in range(1, m + 1)]
k              = int(lines[m + 1])
infected_nodes = list(map(int, lines[m + 2].split()))

# Optional timestamp line
timestamps = {}
if len(lines) > m + 3:
    ts_vals = list(map(float, lines[m + 3].split()))
    for idx, t in enumerate(ts_vals):
        timestamps[idx + 1] = t

G = nx.DiGraph()
G.add_nodes_from(range(1, n + 1))
G.add_edges_from(edges_raw)
R = G.reverse(copy=True)

def reverse_bfs_dist(start):
    dist  = {start: 0}
    queue = collections.deque([start])
    steps = []
    while queue:
        node = queue.popleft()
        for pred in R.neighbors(node):
            if pred in dist:
                continue
            if timestamps:
                t_pred = timestamps.get(pred)
                t_node = timestamps.get(node)
                if t_pred is not None and t_node is not None and t_pred > t_node:
                    continue
            dist[pred] = dist[node] + 1
            steps.append({"from": pred, "to": node})
            queue.append(pred)
    return dist, steps

all_dists, all_steps, all_visited = [], [], []
for s in infected_nodes:
    d, st = reverse_bfs_dist(s)
    all_dists.append(d)
    all_steps.append(st)
    all_visited.append(set(d.keys()))


in_deg_cent = nx.in_degree_centrality(G)
betweenness = nx.betweenness_centrality(G)

def centrality_bonus(node):
    combined = (in_deg_cent.get(node, 0) + betweenness.get(node, 0)) / 2
    return 1.0 + combined

prob_scores = {}
for c in G.nodes():
    score = sum(1.0 / (d[c] + 1.0) for d in all_dists if c in d)
    prob_scores[c] = round(score * centrality_bonus(c), 4) if score > 0 else 0.0

max_score = max(prob_scores.values()) or 1


def greedy_multi_source(max_src):
    covered, selected = [False] * len(infected_nodes), []
    for _ in range(max_src):
        best_node, best_new = None, -1
        for c in G.nodes():
            if prob_scores[c] == 0:
                continue
            nc = sum(1 for i in range(len(infected_nodes))
                     if not covered[i] and c in all_dists[i])
            if nc > best_new or (nc == best_new and best_node and prob_scores[c] > prob_scores[best_node]):
                best_new, best_node = nc, c
        if best_node is None or best_new == 0:
            break
        selected.append(best_node)
        for i in range(len(infected_nodes)):
            if best_node in all_dists[i]:
                covered[i] = True
        if all(covered):
            break
    return selected

multi_sources = greedy_multi_source(MAX_SOURCES)
single_source = max(prob_scores, key=prob_scores.get) if prob_scores else None
intersection  = set(G.nodes())
for vs in all_visited:
    intersection &= vs

raw_pos = nx.spring_layout(G, seed=42)
xs = [v[0] for v in raw_pos.values()]
ys = [v[1] for v in raw_pos.values()]
mn_x, mx_x = min(xs), max(xs)
mn_y, mx_y = min(ys), max(ys)
pad = 0.08

def norm(val, mn, mx):
    return pad + (val - mn) / (mx - mn) * (1 - 2 * pad) if mx != mn else 0.5

node_pos = {
    str(nd): [round(norm(raw_pos[nd][0], mn_x, mx_x), 4),
              round(norm(raw_pos[nd][1], mn_y, mx_y), 4)]
    for nd in G.nodes()
}


bfs_steps = []
for bi, steps in enumerate(all_steps):
    for st in steps:
        bfs_steps.append({"from": st["from"], "to": st["to"], "bi": bi})

# top scores for sidebar
top_scores = sorted(prob_scores.items(), key=lambda x: -x[1])[:12]

# centrality top 8
cent_sorted = sorted(G.nodes(),
    key=lambda nd: in_deg_cent[nd] + betweenness[nd], reverse=True)[:8]


print(f"{'='*50}")
print(f"RESULTS SUMMARY")
print(f"{'='*50}")
print(f"Nodes: {n}  |  Edges: {m}  |  Infected: {infected_nodes}")
print(f"Intersection (old method) : {sorted(intersection) if intersection else '∅ empty'}")
print(f"\nTop 5 Probability Scores:")
for nd, sc in top_scores[:5]:
    print(f"  Node {nd:3d}  score={sc:.4f}  in-deg={in_deg_cent[nd]:.3f}  betw={betweenness[nd]:.3f}")
print(f"\nSingle Best Source : Node {single_source}  (score={prob_scores.get(single_source,0):.4f})")
print(f"Multi-Sources      : {multi_sources}")
print(f"Time-Pruning       : {'ACTIVE' if timestamps else 'OFF'}")
print(f"{'='*50}")

cent_rows_html = ""
for nd in cent_sorted:
    hi = "style='color:#ffd93d'" if nd in multi_sources else ""
    cent_rows_html += (
        f"<tr><td {hi}>{nd}</td>"
        f"<td>{in_deg_cent[nd]:.3f}</td>"
        f"<td>{betweenness[nd]:.3f}</td></tr>"
    )


score_bars_html = ""
for nd, sc in top_scores:
    pct = round(sc / max_score * 100)
    col = ('#ffd93d' if nd in multi_sources
           else '#ff6b6b' if nd in infected_nodes
           else '#2a6090')
    score_bars_html += (
        f"<div class='score-row'>"
        f"<span class='sn'>Node {nd}</span>"
        f"<div class='bar-wrap'><div class='bar' style='width:{pct}%;background:{col}'></div></div>"
        f"<span class='sv'>{sc:.3f}</span>"
        f"</div>"
    )


html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>Source Detection — Reverse BFS</title>
<style>
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ background:#0e1117; color:#c8d6e5; font-family:monospace; height:100vh; display:flex; flex-direction:column; }}
  header {{ padding:10px 20px; border-bottom:1px solid #1e2736; display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:8px; }}
  header h1 {{ font-size:.88rem; color:#fff; font-weight:600; letter-spacing:1px; }}
  .hinfo {{ font-size:.68rem; color:#4a5568; }}
  .htag {{ font-size:.65rem; background:#1a2236; border:1px solid #2d3f5a; color:#5b8dd9; padding:2px 8px; border-radius:2px; }}
  .main {{ display:grid; grid-template-columns:1fr 280px; flex:1; overflow:auto; }}
  .graph-wrap {{ position:relative; background:#0a0c10; }}
  canvas {{ width:100%; height:100%; display:block; }}
  .side {{ border-left:1px solid #1e2736; display:flex; flex-direction:column; overflow-y:auto; }}
  .block {{ padding:12px 14px; border-bottom:1px solid #1e2736; }}
  .block-title {{ font-size:.6rem; color:#4a5568; letter-spacing:2px; text-transform:uppercase; margin-bottom:9px; }}
  .score-row {{ display:flex; align-items:center; gap:6px; margin:3px 0; font-size:.65rem; }}
  .sn {{ width:56px; color:#c8d6e5; }}
  .bar-wrap {{ flex:1; background:#1a1f2b; height:7px; border-radius:1px; overflow:hidden; }}
  .bar {{ height:100%; border-radius:1px; }}
  .sv {{ width:36px; text-align:right; color:#555; }}
  table {{ width:100%; border-collapse:collapse; font-size:.63rem; }}
  th {{ color:#4a5568; padding:3px 5px; text-align:left; border-bottom:1px solid #1e2736; font-weight:400; }}
  td {{ padding:3px 5px; border-bottom:1px solid #111722; }}
  .result-row {{ display:flex; justify-content:space-between; font-size:.68rem; margin:4px 0; gap:8px; }}
  .label {{ color:#4a5568; }}
  .val {{ color:#ffd93d; text-align:right; }}
  .val.blue {{ color:#00d4ff; }}
  .val.red  {{ color:#ff6b6b; }}
  .controls {{ padding:8px 14px; border-top:1px solid #1e2736; background:#0a0c10; display:flex; align-items:center; gap:10px; }}
  .btn {{ background:none; border:1px solid #2d3748; color:#c8d6e5; font-family:monospace; font-size:.72rem; padding:4px 12px; border-radius:2px; cursor:pointer; }}
  .btn:hover {{ border-color:#4a5568; }}
  input[type=range] {{ accent-color:#00d4ff; width:70px; }}
  .step {{ font-size:.65rem; color:#4a5568; margin-left:auto; }}
  #log {{ font-size:.62rem; max-height:80px; overflow-y:auto; line-height:1.9; color:#4a5568; }}
  #log .e {{ color:#c8d6e5; }} #log .done {{ color:#ffd93d; }}
  .dot {{ display:inline-block; width:8px; height:8px; border-radius:50%; margin-right:5px; }}
</style>
</head>
<body>
<header>
  <div>
    <h1>Reverse BFS — Source Detection</h1>
  </div>
  <div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap">
    <span class="htag">{n} nodes</span>
    <span class="htag">{m} edges</span>
    <span class="htag">infected: {infected_nodes}</span>
  </div>
</header>

<div class="main">
  <div class="graph-wrap"><canvas id="c"></canvas></div>
  <div class="side">

    <div class="block">
      <div class="block-title">Probability Score</div>
      {score_bars_html}
    </div>

    <div class="block">
      <div class="block-title">Detection Results</div>
      <div class="result-row"><span class="label">Best Single Source</span><span class="val">Node {single_source} ({prob_scores.get(single_source,0):.3f})</span></div>
      <div class="result-row"><span class="label">Multi-Source (greedy)</span><span class="val">{multi_sources}</span></div>
      <div class="result-row"><span class="label">Intersection (old)</span><span class="val blue">{sorted(intersection) if intersection else "∅ empty"}</span></div>
      <div class="result-row"><span class="label">Time Pruning</span><span class="val blue">{"Active" if timestamps else "Off (no timestamps)"}</span></div>
    </div>

    <div class="block">
      <div class="block-title">Centrality (top 8)</div>
      <table>
        <thead><tr><th>Node</th><th>In-Deg</th><th>Betweenness</th></tr></thead>
        <tbody>{cent_rows_html}</tbody>
      </table>
    </div>

    <div class="block">
      <div class="block-title">Legend</div>
      <div style="font-size:.66rem;line-height:2.2">
        <div><span class="dot" style="background:#ffd93d"></span>Detected source</div>
        <div><span class="dot" style="background:#ff6b6b"></span>Infected node</div>
        <div><span class="dot" style="background:#00d4ff"></span>Visited by BFS</div>
        <div><span class="dot" style="background:#1e2530"></span>Unvisited</div>
      </div>
    </div>

    <div class="block">
      <div class="block-title">Log</div>
      <div id="log"></div>
    </div>

  </div>
</div>

<div class="controls">
  <button class="btn" id="btnPlay">&#9654; Play</button>
  <button class="btn" id="btnPause" style="display:none">&#9646;&#9646; Pause</button>
  <button class="btn" id="btnReset">&#8635; Reset</button>
  <input type="range" id="spd" min="50" max="800" value="350">
  <span class="step" id="stepInfo">0 / {len(bfs_steps)}</span>
</div>

<script>
const N            = {n};
const EDGES        = {json.dumps(edges_raw)};
const INFECTED     = {json.dumps(infected_nodes)};
const PROB_SCORES  = {json.dumps({str(k): v for k, v in prob_scores.items()})};
const IN_DEG       = {json.dumps({str(k): round(v, 4) for k, v in in_deg_cent.items()})};
const BETWEEN      = {json.dumps({str(k): round(v, 4) for k, v in betweenness.items()})};
const NODE_POS     = {json.dumps(node_pos)};
const MULTI_SOURCES= {json.dumps(multi_sources)};
const BFS_STEPS    = {json.dumps(bfs_steps)};

const canvas = document.getElementById('c');
const ctx    = canvas.getContext('2d');
function resize(){{
  canvas.width  = canvas.offsetWidth  * devicePixelRatio;
  canvas.height = canvas.offsetHeight * devicePixelRatio;
  ctx.scale(devicePixelRatio, devicePixelRatio);
}}
resize();
window.addEventListener('resize', () => {{ resize(); draw(); }});

function px(nd){{
  const W=canvas.offsetWidth, H=canvas.offsetHeight, p=44;
  const [x,y]=NODE_POS[String(nd)];
  return [p + x*(W-2*p), p + y*(H-2*p)];
}}

function nodeCol(nd){{
  if(MULTI_SOURCES.includes(nd)) return '#ffd93d';
  if(INFECTED.includes(nd))      return '#ff6b6b';
  if(visited.has(nd))            return '#2a6090';
  return '#1e2530';
}}

function drawArrow(x1,y1,x2,y2,col,prog=1){{
  const sf=0.88, tx=x1+(x2-x1)*sf*prog, ty=y1+(y2-y1)*sf*prog;
  ctx.beginPath(); ctx.moveTo(x1,y1); ctx.lineTo(tx,ty);
  ctx.strokeStyle=col; ctx.lineWidth=1.8; ctx.stroke();
  if(prog>.9){{
    const a=Math.atan2(ty-y1,tx-x1);
    ctx.beginPath(); ctx.moveTo(tx,ty);
    ctx.lineTo(tx-9*Math.cos(a-.4), ty-9*Math.sin(a-.4));
    ctx.lineTo(tx-9*Math.cos(a+.4), ty-9*Math.sin(a+.4));
    ctx.closePath(); ctx.fillStyle=col; ctx.fill();
  }}
}}

function draw(){{
  const W=canvas.offsetWidth, H=canvas.offsetHeight;
  ctx.clearRect(0,0,W,H);
  for(const [u,v] of EDGES){{
    const[x1,y1]=px(u),[x2,y2]=px(v);
    ctx.beginPath(); ctx.moveTo(x1,y1); ctx.lineTo(x2,y2);
    ctx.strokeStyle='#1a2030'; ctx.lineWidth=1; ctx.stroke();
  }}
  const bfsColors=['#3a7bd5aa','#e55555aa','#d4a500aa'];
  for(let i=0;i<=stepIdx&&i<BFS_STEPS.length;i++){{
    const s=BFS_STEPS[i];
    const[x1,y1]=px(s.from),[x2,y2]=px(s.to);
    drawArrow(x1,y1,x2,y2, bfsColors[s.bi]||'#555');
  }}
  for(const a of activeArrows){{
    const[x1,y1]=px(a.from),[x2,y2]=px(a.to);
    drawArrow(x1,y1,x2,y2,'#ffffff',a.p);
  }}
  for(let nd=1;nd<=N;nd++){{
    const[x,y]=px(nd);
    const isKey=MULTI_SOURCES.includes(nd)||INFECTED.includes(nd);
    const r=isKey?17:11;
    ctx.beginPath(); ctx.arc(x,y,r,0,Math.PI*2);
    ctx.fillStyle=nodeCol(nd); ctx.fill();
    ctx.strokeStyle='rgba(255,255,255,.08)'; ctx.lineWidth=1; ctx.stroke();
    if(isKey){{
      ctx.fillStyle='rgba(255,255,255,.85)';
      ctx.font=`bold ${{Math.round(r*.75)}}px monospace`;
      ctx.textAlign='center'; ctx.textBaseline='middle';
      ctx.fillText(nd,x,y);
    }}
  }}
  document.getElementById('stepInfo').textContent=
    `${{Math.max(0,stepIdx+1)}} / ${{BFS_STEPS.length}}`;
}}

let stepIdx=-1, visited=new Set(), activeArrows=[], playing=false,
    lastTime=0, arrowT=0, stepDelay=300;
const logEl=document.getElementById('log');
function addLog(t,cls='e'){{
  const d=document.createElement('div'); d.className=cls; d.textContent=t;
  logEl.appendChild(d); logEl.scrollTop=logEl.scrollHeight;
}}

function animate(ts){{
  if(!playing) return;
  const dt=ts-lastTime; lastTime=ts;
  if(activeArrows.length){{
    arrowT+=dt/(stepDelay*.6);
    for(const a of activeArrows) a.p=Math.min(1,arrowT);
    if(arrowT>=1){{
      activeArrows=[]; arrowT=0;
      if(stepIdx>=0 && stepIdx<BFS_STEPS.length){{
        visited.add(BFS_STEPS[stepIdx].to);
        visited.add(BFS_STEPS[stepIdx].from);
      }}
    }}
  }} else {{
    stepIdx++;
    if(stepIdx>=BFS_STEPS.length){{
      playing=false;
      document.getElementById('btnPlay').style.display='';
      document.getElementById('btnPause').style.display='none';
      addLog('done — sources detected','done');
      draw(); return;
    }}
    const s=BFS_STEPS[stepIdx];
    activeArrows=[{{from:s.from, to:s.to, p:0}}];
    addLog(`bfs-${{s.bi+1}}  node ${{s.from}} → node ${{s.to}}`);
  }}
  draw(); requestAnimationFrame(animate);
}}

function play(){{
  if(playing) return; playing=true; lastTime=performance.now();
  document.getElementById('btnPlay').style.display='none';
  document.getElementById('btnPause').style.display='';
  requestAnimationFrame(animate);
}}
function pause(){{
  playing=false;
  document.getElementById('btnPlay').style.display='';
  document.getElementById('btnPause').style.display='none';
}}
function reset(){{
  pause(); stepIdx=-1; visited=new Set(); activeArrows=[]; arrowT=0;
  logEl.innerHTML=''; addLog('ready — press play'); draw();
}}

document.getElementById('btnPlay').onclick=play;
document.getElementById('btnPause').onclick=pause;
document.getElementById('btnReset').onclick=reset;
document.getElementById('spd').oninput=e=>{{ stepDelay=850-Number(e.target.value); }};

reset();
</script>
</body>
</html>"""

with open(OUT_HTML, "w", encoding="utf-8") as f:
    f.write(html)

print(f"Wrote: {OUT_HTML}")

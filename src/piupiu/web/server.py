from __future__ import annotations
import logging
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from ..graph.engine import GraphEngine

logger = logging.getLogger(__name__)

# ── HTML page ─────────────────────────────────────────────────────────────────

_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>PiuPiu — Knowledge Graph</title>
<script src="https://unpkg.com/cytoscape@3.28.1/dist/cytoscape.min.js"></script>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: system-ui, -apple-system, sans-serif;
    background: #0F172A; color: #E2E8F0;
    height: 100vh; display: flex; flex-direction: column; overflow: hidden;
  }
  #toolbar {
    display: flex; align-items: center; gap: 10px;
    padding: 8px 16px; background: #1E293B;
    border-bottom: 1px solid #334155; flex-shrink: 0;
  }
  #logo { font-weight: 700; font-size: 16px; color: #818CF8; }
  #logo span { color: #475569; font-weight: 400; font-size: 13px; }
  #search {
    flex: 1; max-width: 240px; padding: 5px 10px;
    background: #0F172A; border: 1px solid #334155; border-radius: 6px;
    color: #E2E8F0; font-size: 13px; outline: none;
  }
  #search:focus { border-color: #6366F1; }
  #search::placeholder { color: #475569; }
  #refresh {
    padding: 5px 12px; background: #1D3461; color: #93C5FD;
    border: none; border-radius: 6px; cursor: pointer;
    font-size: 13px; font-weight: 500;
  }
  #refresh:hover { background: #1D4ED8; color: #fff; }
  #stats { color: #475569; font-size: 12px; margin-left: auto; white-space: nowrap; }

  #main { display: flex; flex: 1; overflow: hidden; position: relative; }
  #cy { flex: 1; }

  #empty-msg {
    position: absolute; inset: 0; display: none;
    flex-direction: column; align-items: center; justify-content: center;
    color: #334155; pointer-events: none;
  }
  #empty-msg h2 { font-size: 20px; margin-bottom: 6px; }
  #empty-msg p { font-size: 13px; }

  #panel {
    width: 0; overflow: hidden;
    background: #1E293B; border-left: 1px solid transparent;
    transition: width 0.2s ease, border-color 0.2s;
    display: flex; flex-direction: column;
  }
  #panel.open { width: 280px; border-color: #334155; overflow-y: auto; }
  #panel-inner { padding: 14px; min-width: 280px; }
  #panel-top {
    display: flex; align-items: flex-start;
    justify-content: space-between; margin-bottom: 10px;
  }
  #panel-title { font-size: 15px; font-weight: 600; color: #F1F5F9; word-break: break-word; line-height: 1.3; }
  #panel-close {
    background: none; border: none; color: #475569;
    font-size: 16px; cursor: pointer; padding: 0 0 0 8px;
    line-height: 1; flex-shrink: 0;
  }
  #panel-close:hover { color: #E2E8F0; }
  #panel-badge {
    display: inline-block; padding: 2px 8px; border-radius: 12px;
    font-size: 11px; font-weight: 600; margin-bottom: 12px;
  }
  .sec {
    font-size: 10px; font-weight: 700; text-transform: uppercase;
    letter-spacing: 1px; color: #475569; margin: 14px 0 5px;
  }
  .prop { display: flex; padding: 4px 0; font-size: 12px; border-bottom: 1px solid #0F172A; gap: 8px; }
  .prop-k { color: #64748B; min-width: 60px; flex-shrink: 0; }
  .prop-v { color: #CBD5E1; word-break: break-all; }
  .rel { display: flex; align-items: center; gap: 6px; padding: 4px 0; font-size: 12px; color: #94A3B8; }
  .rel-type {
    font-family: monospace; font-size: 10px;
    background: #0F172A; color: #64748B;
    padding: 1px 4px; border-radius: 3px;
  }
  #del-btn {
    margin-top: 16px; width: 100%; padding: 7px;
    background: #3B0A0A; color: #FCA5A5;
    border: 1px solid #7F1D1D; border-radius: 6px;
    cursor: pointer; font-size: 13px; font-weight: 500;
  }
  #del-btn:hover { background: #7F1D1D; }

  #legend {
    display: flex; gap: 12px; padding: 6px 16px;
    background: #1E293B; border-top: 1px solid #334155;
    flex-shrink: 0; flex-wrap: wrap;
  }
  .leg { display: flex; align-items: center; gap: 4px; font-size: 11px; color: #64748B; }
  .dot { width: 8px; height: 8px; border-radius: 50%; }
</style>
</head>
<body>

<div id="toolbar">
  <span id="logo">PiuPiu <span>graph</span></span>
  <input id="search" placeholder="Search nodes…" autocomplete="off" spellcheck="false">
  <button id="refresh">↺ Refresh</button>
  <span id="stats"></span>
</div>

<div id="main">
  <div id="cy">
    <div id="empty-msg">
      <h2>Graph is empty</h2>
      <p>Tell your bot something to remember</p>
    </div>
  </div>
  <div id="panel">
    <div id="panel-inner">
      <div id="panel-top">
        <span id="panel-title"></span>
        <button id="panel-close">✕</button>
      </div>
      <span id="panel-badge"></span>
      <div id="panel-props"></div>
      <div id="panel-rels"></div>
      <button id="del-btn">Delete node</button>
    </div>
  </div>
</div>

<div id="legend"></div>

<script>
const COLORS = {
  Organization: '#6366F1', Person:   '#10B981',
  Service:      '#F59E0B', Credential: '#EF4444',
  Resource:     '#8B5CF6', Concept:    '#06B6D4',
  Event:        '#EC4899', Location:   '#84CC16',
};
const color = t => COLORS[t] || '#64748B';

// Build legend
const legendEl = document.getElementById('legend');
Object.entries(COLORS).forEach(([t, c]) => {
  legendEl.innerHTML +=
    `<span class="leg"><span class="dot" style="background:${c}"></span>${t}</span>`;
});

let cy, selected;

function buildCy(data) {
  const els = [
    ...data.nodes.map(n => ({
      data: { id: n.id, label: n.label, type: n.type, props: n.properties, color: color(n.type) }
    })),
    ...data.edges.map((e, i) => ({
      data: { id: 'e' + i, source: e.source, target: e.target, label: e.type }
    })),
  ];

  if (cy) cy.destroy();
  cy = cytoscape({
    container: document.getElementById('cy'),
    elements: els,
    style: [
      {
        selector: 'node',
        style: {
          'background-color': 'data(color)', label: 'data(label)',
          color: '#F1F5F9', 'font-size': 11,
          'text-valign': 'bottom', 'text-margin-y': 4,
          'text-outline-color': '#0F172A', 'text-outline-width': 2,
          width: 32, height: 32,
          'border-width': 2, 'border-color': '#334155',
        },
      },
      { selector: 'node:selected', style: { 'border-color': '#F8FAFC', 'border-width': 3 } },
      { selector: '.dim', style: { opacity: 0.15 } },
      {
        selector: 'edge',
        style: {
          width: 1.5, 'line-color': '#334155',
          'target-arrow-color': '#334155', 'target-arrow-shape': 'triangle',
          'curve-style': 'bezier', label: 'data(label)',
          color: '#475569', 'font-size': 9, 'text-rotation': 'autorotate',
          'text-background-color': '#0F172A', 'text-background-opacity': 1,
          'text-background-padding': '2px',
        },
      },
      { selector: 'edge.dim', style: { opacity: 0.05 } },
    ],
    layout: {
      name: 'cose', animate: false,
      nodeRepulsion: 10000, idealEdgeLength: 140, gravity: 0.8, randomize: true,
    },
    minZoom: 0.15, maxZoom: 5,
  });

  cy.on('tap', 'node', e => { try { openPanel(e.target); } catch(err) { console.error('openPanel:', err); } });
  cy.on('tap', e => { if (e.target === cy) { closePanel(); clearDim(); } });

  const empty = document.getElementById('empty-msg');
  empty.style.display = data.nodes.length ? 'none' : 'flex';
}

function openPanel(node) {
  selected = node;
  clearDim();
  cy.elements().not(node.closedNeighborhood()).addClass('dim');

  document.getElementById('panel-title').textContent = node.data('label');
  const badge = document.getElementById('panel-badge');
  const t = node.data('type');
  badge.textContent = t;
  badge.style.background = color(t) + '28';
  badge.style.color = color(t);

  const props = node.data('props') || {};
  const keys = Object.keys(props).filter(k => props[k]);
  document.getElementById('panel-props').innerHTML = keys.length
    ? '<div class="sec">Properties</div>' + keys.map(k =>
        `<div class="prop"><span class="prop-k">${k}</span><span class="prop-v">${escHtml(String(props[k]))}</span></div>`
      ).join('')
    : '';

  const out = node.outgoers('edge');
  const inc = node.incomers('edge');
  let html = '';
  if (out.length || inc.length) {
    html = '<div class="sec">Relationships</div>';
    out.forEach(e => {
      html += `<div class="rel">→ <span class="rel-type">${escHtml(e.data('label'))}</span> ${escHtml(e.target().data('label') || e.target().id())}</div>`;
    });
    inc.forEach(e => {
      html += `<div class="rel">← <span class="rel-type">${escHtml(e.data('label'))}</span> ${escHtml(e.source().data('label') || e.source().id())}</div>`;
    });
  }
  document.getElementById('panel-rels').innerHTML = html;
  document.getElementById('panel').classList.add('open');
}

function closePanel() {
  selected = null;
  document.getElementById('panel').classList.remove('open');
}

function clearDim() { if (cy) cy.elements().removeClass('dim'); }

function escHtml(s) {
  if (s == null) return '';
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

async function loadGraph() {
  const r = await fetch('/api/graph');
  const data = await r.json();
  document.getElementById('stats').textContent =
    `${data.nodes.length} nodes · ${data.edges.length} edges`;
  buildCy(data);
  closePanel();
}

// Search — highlight matching nodes and their neighbours
let searchTimer;
document.getElementById('search').addEventListener('input', e => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    const q = e.target.value.trim().toLowerCase();
    if (!cy) return;
    clearDim(); closePanel();
    if (!q) return;
    const matched = cy.nodes().filter(n => n.data('label').toLowerCase().includes(q));
    cy.elements().not(matched.closedNeighborhood()).addClass('dim');
  }, 180);
});

document.getElementById('refresh').addEventListener('click', loadGraph);
document.getElementById('panel-close').addEventListener('click', () => { closePanel(); clearDim(); });

document.getElementById('del-btn').addEventListener('click', async () => {
  if (!selected) return;
  const label = selected.data('label');
  if (!confirm(`Delete "${label}" and all its edges?`)) return;
  const nodeId = selected.id();
  const r = await fetch('/api/nodes/' + encodeURIComponent(nodeId), { method: 'DELETE' });
  if (r.ok) {
    loadGraph();
  } else {
    const d = await r.json().catch(() => ({}));
    alert(d.detail || 'Delete failed');
  }
});

loadGraph();
</script>
</body>
</html>"""


# ── FastAPI app ────────────────────────────────────────────────────────────────

def create_app(engine: GraphEngine) -> FastAPI:
    app = FastAPI(title="PiuPiu Graph", docs_url=None, redoc_url=None)

    @app.get("/", response_class=HTMLResponse)
    async def index():
        return _HTML

    @app.get("/api/graph")
    async def get_graph():
        nodes, edges = [], []
        for node_id, data in engine._graph.nodes(data=True):
            nodes.append({
                "id": node_id,
                "label": data.get("label", node_id),
                "type": data.get("type", "Unknown"),
                "properties": {k: v for k, v in data.items() if k not in ("type", "label")},
            })
        for src, dst, data in engine._graph.edges(data=True):
            edges.append({"source": src, "target": dst, "type": data.get("type", "RELATED_TO")})
        return {"nodes": nodes, "edges": edges}

    @app.delete("/api/nodes/{node_id:path}")
    async def delete_node(node_id: str):
        if not engine._graph.has_node(node_id):
            raise HTTPException(status_code=404, detail=f"Node not found: {node_id}")
        data = dict(engine._graph.nodes[node_id])
        label = data.get("label", node_id)
        edge_count = engine._graph.in_degree(node_id) + engine._graph.out_degree(node_id)
        engine._graph.remove_node(node_id)
        engine._storage.save_graph(engine._graph)
        logger.info("Web UI deleted [%s] %s (%d edge(s))", data.get("type", "?"), label, edge_count)
        return {"message": f"Deleted [{data.get('type', '?')}] {label} ({edge_count} edge(s) removed)"}

    return app


# ── Uvicorn runner (asyncio-compatible) ───────────────────────────────────────

async def run_web(engine: GraphEngine, host: str, port: int) -> None:
    try:
        import uvicorn
    except ImportError:
        raise RuntimeError("Web UI requires: pip install 'piupiu[web]'")

    class _Server(uvicorn.Server):
        def install_signal_handlers(self) -> None:
            pass  # let asyncio handle SIGINT so Ctrl+C works normally

    config = uvicorn.Config(
        app=create_app(engine),
        host=host,
        port=port,
        log_level="error",
        access_log=False,
    )
    await _Server(config).serve()

"""
module 6 — visualization & reporting  (v2 — custom html)

replaces pyvis with a hand-crafted html visualization using vis-network.js.
"""

import json
import html as html_mod
import argparse
from pathlib import Path
from datetime import timedelta


_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Concept DAG — {video_id}</title>
<script src="https://unpkg.com/vis-network@9.1.6/standalone/umd/vis-network.min.js"></script>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  :root {{
    --bg: #0d1117; --surface: #161b22; --border: #30363d;
    --text: #e6edf3; --text-dim: #8b949e; --accent: #58a6ff;
    --green: #3fb950; --orange: #d29922; --red: #f85149;
    --purple: #bc8cff; --cyan: #39d353;
  }}
  html, body {{
    height: 100%; overflow: hidden;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
    background: var(--bg); color: var(--text); line-height: 1.5;
  }}
  body {{ display: flex; flex-direction: column; }}
  .header {{
    flex-shrink: 0;
    padding: 16px 24px; background: var(--surface);
    border-bottom: 1px solid var(--border);
    display: flex; align-items: center; gap: 16px;
  }}
  .header h1 {{ font-size: 18px; font-weight: 600; }}
  .header .badge {{
    padding: 2px 10px; border-radius: 12px; font-size: 12px;
    background: var(--accent); color: var(--bg); font-weight: 600;
  }}
  .header .lang-badge {{ background: var(--purple); }}
  .stats {{
    flex-shrink: 0;
    display: flex; gap: 24px; padding: 12px 24px;
    background: var(--surface); border-bottom: 1px solid var(--border); font-size: 13px;
  }}
  .stat {{ display: flex; align-items: center; gap: 6px; }}
  .stat-value {{ font-weight: 700; color: var(--accent); font-size: 16px; }}
  .stat-label {{ color: var(--text-dim); }}
  .main {{ flex: 1; min-height: 0; display: grid; grid-template-columns: 1fr 320px; }}
  #graph {{ background: var(--bg); border-right: 1px solid var(--border); height: 100%; }}
  .sidebar {{ background: var(--surface); overflow-y: auto; height: 100%; }}
  .sidebar-section {{ padding: 12px 16px; border-bottom: 1px solid var(--border); }}
  .sidebar-section h3 {{
    font-size: 11px; text-transform: uppercase; letter-spacing: 1px;
    color: var(--text-dim); margin-bottom: 8px;
  }}
  .node-detail {{ display: none; }}
  .node-detail.active {{ display: block; }}
  .node-name {{ font-size: 16px; font-weight: 600; color: var(--accent); margin-bottom: 4px; }}
  .node-meta {{ font-size: 12px; color: var(--text-dim); margin-bottom: 8px; }}
  .mentions-list {{ list-style: none; max-height: 200px; overflow-y: auto; }}
  .mentions-list li {{ padding: 4px 0; font-size: 12px; border-bottom: 1px solid var(--border); }}
  .mention-time {{ color: var(--green); font-family: monospace; margin-right: 6px; }}
  .mention-src {{
    padding: 1px 4px; border-radius: 3px; font-size: 10px;
    background: var(--border); color: var(--text-dim);
  }}
  .topo-list {{ list-style: none; counter-reset: topo; }}
  .topo-list li {{ counter-increment: topo; padding: 3px 0; font-size: 13px; cursor: pointer; }}
  .topo-list li:hover {{ color: var(--accent); }}
  .topo-list li::before {{
    content: counter(topo) "."; color: var(--text-dim);
    margin-right: 8px; font-size: 11px; font-family: monospace;
  }}
  .legend-item {{ display: flex; align-items: center; gap: 8px; padding: 2px 0; font-size: 12px; }}
  .legend-line {{ width: 24px; height: 2px; border-radius: 1px; }}
  .timeline {{ display: flex; gap: 1px; height: 20px; margin-top: 6px; }}
  .timeline-bar {{
    flex: 1; border-radius: 2px; min-width: 3px; position: relative; cursor: pointer;
  }}
  .timeline-bar:hover::after {{
    content: attr(data-tip); position: absolute; bottom: 100%;
    left: 50%; transform: translateX(-50%);
    background: var(--surface); border: 1px solid var(--border);
    padding: 2px 6px; font-size: 10px; white-space: nowrap; border-radius: 3px;
  }}
  .no-select {{ font-size: 13px; color: var(--text-dim); padding: 8px 0; }}
  @media (max-width: 768px) {{
    .main {{ grid-template-columns: 1fr; grid-template-rows: 60vh 1fr; }}
  }}
</style>
</head>
<body>
<div class="header">
  <h1>Concept DAG</h1>
  <span class="badge">{video_id}</span>
  <span class="badge lang-badge">{source_lang}</span>
</div>
<div class="stats">
  <div class="stat"><span class="stat-value">{n_concepts}</span><span class="stat-label">concepts</span></div>
  <div class="stat"><span class="stat-value">{n_edges}</span><span class="stat-label">edges</span></div>
  <div class="stat"><span class="stat-value">{n_topo}/{n_concepts}</span><span class="stat-label">topo order</span></div>
  <div class="stat"><span class="stat-value">{n_segments}</span><span class="stat-label">segments</span></div>
</div>
<div class="main">
  <div id="graph"></div>
  <div class="sidebar">
    <div class="sidebar-section node-detail" id="node-detail">
      <h3>Selected Concept</h3>
      <div class="node-name" id="detail-name"></div>
      <div class="node-meta" id="detail-meta"></div>
      <h3 style="margin-top:12px">Mentions</h3>
      <ul class="mentions-list" id="detail-mentions"></ul>
      <h3 style="margin-top:12px">Connections</h3>
      <div id="detail-edges" style="font-size:12px"></div>
    </div>
    <div class="sidebar-section" id="no-select-panel">
      <p class="no-select">Click a node to see details</p>
    </div>
    <div class="sidebar-section">
      <h3>Topological Order</h3>
      <ol class="topo-list" id="topo-list">{topo_html}</ol>
    </div>
    <div class="sidebar-section">
      <h3>Edge Types</h3>
      {legend_html}
    </div>
    <div class="sidebar-section">
      <h3>Mention Timeline</h3>
      <div class="timeline">{timeline_html}</div>
    </div>
  </div>
</div>
<script>
const graphData = {graph_json};
const conceptMeta = {concept_meta_json};

window.addEventListener('load', function() {{
  const nodes = new vis.DataSet(graphData.nodes.map(n => ({{
    id: n.id, label: n.label,
    color: {{ background: n.color || '#58a6ff', border: n.border || '#388bfd',
             highlight: {{ background: '#79c0ff', border: '#58a6ff' }} }},
    font: {{ color: '#e6edf3', size: 14, face: '-apple-system, BlinkMacSystemFont, Segoe UI, Helvetica, Arial, sans-serif' }},
    shape: 'box', margin: {{ top: 10, bottom: 10, left: 14, right: 14 }},
    borderWidth: 2, borderWidthSelected: 3,
    shadow: {{ enabled: true, color: 'rgba(0,0,0,0.3)', size: 6, x: 2, y: 2 }},
  }})));
  const edgeColors = {{'domain_rule':'#d29922','temporal':'#8b949e','causal':'#f85149','co-occurrence':'#bc8cff'}};
  const edges = new vis.DataSet(graphData.edges.map((e, i) => ({{
    id: i, from: e.from, to: e.to, arrows: {{ to: {{ enabled: true, scaleFactor: 0.7 }} }},
    color: {{ color: edgeColors[e.type] || '#30363d', highlight: '#58a6ff' }},
    width: e.type === 'domain_rule' ? 2.5 : 1.5,
    dashes: e.type === 'temporal',
    smooth: {{ type: 'cubicBezier', forceDirection: 'vertical', roundness: 0.4 }},
    title: e.type + (e.rule ? ' (' + e.rule + ')' : ''),
  }})));

  const container = document.getElementById('graph');
  const network = new vis.Network(container, {{ nodes, edges }}, {{
    layout: {{
      hierarchical: {{
        enabled: true,
        direction: 'UD',
        sortMethod: 'directed',
        levelSeparation: 100,
        nodeSpacing: 170,
        treeSpacing: 200,
        blockShifting: true,
        edgeMinimization: true,
        parentCentralization: true,
      }}
    }},
    physics: {{ enabled: false }},
    interaction: {{
      dragNodes: false,
      dragView: false,
      zoomView: false,
      selectable: true,
      hover: true,
      tooltipDelay: 100,
    }},
  }});

  network.once('afterDrawing', function() {{
    network.fit({{ animation: false }});
  }});

  network.on('click', function(params) {{
    const detail = document.getElementById('node-detail');
    const noSelect = document.getElementById('no-select-panel');
    if (params.nodes.length > 0) {{
      const nid = params.nodes[0];
      const meta = conceptMeta[nid];
      if (!meta) return;
      document.getElementById('detail-name').textContent = meta.label;
      document.getElementById('detail-meta').textContent =
        meta.mentions + ' mentions \u00b7 first at ' + meta.first_seen;
      const ml = document.getElementById('detail-mentions');
      ml.innerHTML = (meta.mention_list || []).map(m =>
        '<li><span class="mention-time">' + m.time + '</span>' +
        '<span class="mention-src">' + m.source + '</span> ' + m.text + '</li>'
      ).join('');
      const el = document.getElementById('detail-edges');
      el.innerHTML = (meta.edges || []).map(e =>
        '<div style="padding:2px 0">' + e + '</div>'
      ).join('');
      detail.classList.add('active');
      noSelect.style.display = 'none';
    }} else {{
      detail.classList.remove('active');
      noSelect.style.display = 'block';
    }}
  }});

  document.querySelectorAll('.topo-list li').forEach(li => {{
    li.addEventListener('click', () => {{
      const nid = li.dataset.nid;
      if (nid) {{ network.selectNodes([nid]); network.focus(nid, {{scale:1.2, animation:true}}); }}
    }});
  }});
}});
</script>
</body>
</html>"""



def _fmt_time(seconds):
    """Format seconds as MM:SS."""
    return str(timedelta(seconds=int(seconds)))[2:]


def _node_color(n_mentions):
    """Color by mention frequency."""
    if n_mentions >= 8:
        return "#3fb950", "#2ea043"   # green — high frequency
    elif n_mentions >= 4:
        return "#58a6ff", "#388bfd"   # blue — medium
    elif n_mentions >= 2:
        return "#d29922", "#9e6a03"   # orange — low
    else:
        return "#8b949e", "#6e7681"   # gray — rare


def build_graph_data(concepts, edges, topo_order):
    """Prepare graph data for vis.js."""
    nodes = []
    for c in concepts:
        bg, border = _node_color(c.get("mentions", 1))
        nodes.append({
            "id": c["name"],
            "label": c["name"].replace("_", " ").title(),
            "color": bg,
            "border": border,
        })
    edge_list = []
    for e in edges:
        edge_list.append({
            "from": e["from"],
            "to": e["to"],
            "type": e.get("type", "temporal"),
            "rule": e.get("rule", ""),
        })
    return {"nodes": nodes, "edges": edge_list}


def build_concept_meta(concepts, edges, normalized_segs):
    """Build per-concept metadata for the detail panel."""
    meta = {}
    for c in concepts:
        name = c["name"]
        label = name.replace("_", " ").title()

        mention_list = []
        for m in c.get("mention_details", []):
            mention_list.append({
                "time": _fmt_time(m.get("start", 0)),
                "source": m.get("source", "?"),
                "text": m.get("text", "")[:80],
            })

        edge_descs = []
        for e in edges:
            e_to = e["to"].replace("_", " ")
            e_from = e["from"].replace("_", " ")
            e_type = e.get("type", "?")
            if e["from"] == name:
                edge_descs.append("\u2192 " + e_to + " (" + e_type + ")")
            elif e["to"] == name:
                edge_descs.append(e_from + " \u2192 this (" + e_type + ")")

        meta[name] = {
            "label": label,
            "mentions": c.get("mentions", 0),
            "first_seen": _fmt_time(c.get("first_seen", 0)),
            "mention_list": mention_list[:20],
            "edges": edge_descs,
        }
    return meta


def _normalize_concept(c):
    """Normalize concept dict from either old or new format."""
    return {
        "name": c.get("name", ""),
        "mentions": c.get("mentions", c.get("mention_count", 0)),
        "first_seen": c.get("first_seen", c.get("first_mention", 0)),
        "sources": c.get("sources", []),
        "mention_details": c.get("mention_details", [
            {"start": t.get("start", 0), "source": "?", "text": ""}
            for t in c.get("timestamps", [])
        ]),
    }


def _normalize_edge(e):
    """Normalize edge dict from either old or new format."""
    return {
        "from": e.get("from", e.get("source", "")),
        "to": e.get("to", e.get("target", "")),
        "type": e.get("type", "domain_rule"),
        "rule": e.get("rule", ""),
    }


def run(concepts_path, prereqs_path=None, data_dir=None):
    """Generate visualization HTML and report."""
    concepts_path = Path(concepts_path)
    out_dir = concepts_path.parent if not data_dir else Path(data_dir)

    with open(concepts_path) as f:
        concepts_data = json.load(f)

    # try prereqs_path, fall back to graph.json
    prereqs_data = {}
    if prereqs_path:
        prereqs_path = Path(prereqs_path)
        if prereqs_path.exists():
            with open(prereqs_path) as f:
                prereqs_data = json.load(f)
    if not prereqs_data:
        graph_path = out_dir / "graph.json"
        if graph_path.exists():
            with open(graph_path) as f:
                prereqs_data = json.load(f)

    # normalize from old/new format
    raw_concepts = concepts_data.get("concepts", [])
    concepts = [_normalize_concept(c) for c in raw_concepts]

    raw_edges = prereqs_data.get("edges", [])
    edges = [_normalize_edge(e) for e in raw_edges]
    topo = prereqs_data.get("topological_order", [])

    # load normalized segments for timeline
    norm_path = out_dir / "normalized_segments.json"
    normalized = []
    if norm_path.exists():
        with open(norm_path) as f:
            normalized = json.load(f)

    # load language info
    lang_path = out_dir / "detected_language.json"
    source_lang = "en"
    if lang_path.exists():
        with open(lang_path) as f:
            source_lang = json.load(f).get("language", "en")

    lang_names = {"en": "English", "hi": "Hindi", "te": "Telugu",
                  "ta": "Tamil", "kn": "Kannada", "ml": "Malayalam"}
    source_lang_display = lang_names.get(source_lang, source_lang.upper())

    video_id = out_dir.name

    # build graph data
    graph_data = build_graph_data(concepts, edges, topo)
    concept_meta = build_concept_meta(concepts, edges, normalized)

    # topo html
    topo_html = ""
    for name in topo:
        label = name.replace("_", " ").title()
        topo_html += '<li data-nid="' + name + '">' + label + '</li>'

    # legend html
    edge_types = {
        "domain_rule": ("#d29922", "solid", "Domain knowledge rule"),
        "causal": ("#f85149", "solid", "Causal language pattern"),
        "temporal": ("#8b949e", "dashed", "Temporal ordering"),
        "co-occurrence": ("#bc8cff", "solid", "Co-occurrence proximity"),
    }
    legend_html = ""
    for etype, (color, style, desc) in edge_types.items():
        border_style = "dashed" if style == "dashed" else "solid"
        legend_html += (
            '<div class="legend-item">'
            '<div class="legend-line" style="border-top:2px '
            + border_style + ' ' + color + ';background:none"></div>'
            '<span>' + desc + '</span></div>'
        )

    # timeline html
    n_bins = min(20, max(5, len(normalized) // 5)) if normalized else 5
    if normalized:
        max_t = max(s.get("end", 0) for s in normalized)
        bin_size = max(1, max_t / n_bins)
        bins = [0] * n_bins
        for s in normalized:
            idx = min(int(s.get("start", 0) / bin_size), n_bins - 1)
            bins[idx] += 1
        max_bin = max(bins) or 1
        timeline_html = ""
        for i, count in enumerate(bins):
            h = max(3, int(20 * count / max_bin))
            opacity = 0.3 + 0.7 * (count / max_bin)
            tip = _fmt_time(i * bin_size) + "-" + _fmt_time((i + 1) * bin_size) + ": " + str(count) + " segs"
            timeline_html += (
                '<div class="timeline-bar" data-tip="' + tip + '" '
                'style="background:var(--accent);height:' + str(h) + 'px;'
                'opacity:' + f"{opacity:.2f}" + ';align-self:flex-end"></div>'
            )
    else:
        timeline_html = '<span style="font-size:12px;color:var(--text-dim)">no data</span>'

    # render
    graph_html = _HTML_TEMPLATE.format(
        video_id=html_mod.escape(video_id),
        source_lang=html_mod.escape(source_lang_display),
        n_concepts=len(concepts),
        n_edges=len(edges),
        n_topo=len(topo),
        n_segments=len(normalized),
        topo_html=topo_html,
        legend_html=legend_html,
        timeline_html=timeline_html,
        graph_json=json.dumps(graph_data),
        concept_meta_json=json.dumps(concept_meta),
    )

    html_path = out_dir / "graph.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(graph_html)
    print("[m6] graph visualization:", html_path)

    # markdown report
    report = _build_report(video_id, source_lang_display, concepts, edges, topo)
    report_path = out_dir / "report.md"
    with open(report_path, "w") as f:
        f.write(report)
    print("[m6] report:", report_path)

    return {
        "graph_html": str(html_path),
        "report_md": str(report_path),
        "n_concepts": len(concepts),
        "n_edges": len(edges),
        "n_topo": len(topo),
    }


def _build_report(video_id, lang, concepts, edges, topo):
    lines = [
        "# Concept DAG Report — " + video_id,
        "",
        "**Source language:** " + lang,
        "**Concepts:** " + str(len(concepts)) + " | **Edges:** " + str(len(edges)) + " | **Topo order:** " + str(len(topo)) + "/" + str(len(concepts)),
        "",
        "## Topological Order",
        "",
    ]
    for i, name in enumerate(topo, 1):
        lines.append(str(i) + ". " + name.replace("_", " ").title())

    lines += ["", "## Concepts", ""]
    for c in concepts:
        cname = c["name"].replace("_", " ").title()
        lines.append("### " + cname)
        lines.append("- Mentions: " + str(c.get("mentions", 0)))
        lines.append("- First seen: " + _fmt_time(c.get("first_seen", 0)))
        sources = c.get("sources", [])
        lines.append("- Sources: " + ", ".join(sources))
        lines.append("")

    lines += ["## Prerequisite Edges", ""]
    lines.append("| From | To | Type | Rule |")
    lines.append("|------|-----|------|------|")
    for e in edges:
        efrom = e["from"].replace("_", " ")
        eto = e["to"].replace("_", " ")
        etype = e.get("type", "?")
        erule = e.get("rule", "")
        lines.append("| " + efrom + " | " + eto + " | " + etype + " | " + erule + " |")

    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("concepts_path")
    parser.add_argument("prereqs_path")
    parser.add_argument("--data-dir", default=None)
    args = parser.parse_args()
    print(run(args.concepts_path, args.prereqs_path, args.data_dir))

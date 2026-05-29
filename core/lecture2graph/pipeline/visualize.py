"""Standalone HTML export for processed lecture graphs."""

from __future__ import annotations

import json

from lecture2graph.models import LectureGraphResult


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Lecture2Graph | __TITLE__</title>
  <script src="https://unpkg.com/vis-network@9.1.6/standalone/umd/vis-network.min.js"></script>
  <style>
    @import url("https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=IBM+Plex+Mono:wght@400;500&display=swap");
    :root {{
      --bg: #07131f;
      --panel: rgba(8, 25, 39, 0.88);
      --panel-solid: #0d2235;
      --line: rgba(141, 184, 213, 0.14);
      --text: #eaf4ff;
      --muted: #8ca2b8;
      --accent: #7ce0c3;
      --accent-2: #ffc670;
      --accent-3: #89b4ff;
      --danger: #ff8d8d;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      color: var(--text);
      background:
        radial-gradient(circle at top left, rgba(124, 224, 195, 0.18), transparent 26%),
        radial-gradient(circle at top right, rgba(137, 180, 255, 0.12), transparent 24%),
        linear-gradient(180deg, #04101a 0%, #07131f 60%, #07131f 100%);
      font-family: "Space Grotesk", system-ui, sans-serif;
    }}
    a {{ color: inherit; }}
    .shell {{
      width: min(1440px, calc(100vw - 32px));
      margin: 16px auto;
      padding: 16px;
      display: grid;
      gap: 16px;
    }}
    .hero {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 28px;
      padding: 24px;
      backdrop-filter: blur(18px);
      box-shadow: 0 24px 90px rgba(0, 0, 0, 0.28);
    }}
    .eyebrow {{
      display: inline-flex;
      gap: 10px;
      padding: 8px 12px;
      border-radius: 999px;
      background: rgba(124, 224, 195, 0.08);
      border: 1px solid rgba(124, 224, 195, 0.18);
      color: var(--accent);
      font-size: 12px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}
    h1 {{
      margin: 16px 0 10px;
      font-size: clamp(2rem, 5vw, 3.4rem);
      line-height: 1.03;
    }}
    .lede {{
      max-width: 860px;
      color: var(--muted);
      font-size: 1rem;
      line-height: 1.7;
    }}
    .stats {{
      margin-top: 20px;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 12px;
    }}
    .stat {{
      padding: 16px;
      border-radius: 20px;
      background: rgba(255, 255, 255, 0.02);
      border: 1px solid var(--line);
    }}
    .stat .value {{
      display: block;
      font-size: 1.65rem;
      font-weight: 700;
      color: var(--accent-2);
    }}
    .stat .label {{
      color: var(--muted);
      font-size: 0.92rem;
    }}
    .workspace {{
      display: grid;
      grid-template-columns: minmax(0, 1.6fr) minmax(320px, 0.9fr);
      gap: 16px;
    }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 26px;
      backdrop-filter: blur(18px);
      overflow: hidden;
    }}
    .panel-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 10px;
      padding: 18px 20px 12px;
    }}
    .panel-title {{
      font-size: 0.94rem;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      color: var(--muted);
    }}
    .panel-hint {{
      font-size: 0.85rem;
      color: var(--muted);
    }}
    #graph {{
      height: 74vh;
      min-height: 560px;
      background:
        linear-gradient(180deg, rgba(255,255,255,0.01), rgba(255,255,255,0)),
        radial-gradient(circle at 20% 20%, rgba(124,224,195,0.08), transparent 30%),
        #07131f;
    }}
    .sidebar {{
      display: grid;
      gap: 16px;
      align-content: start;
      padding: 0 0 16px;
    }}
    .sidebar-card {{
      padding: 18px 20px;
      border-top: 1px solid var(--line);
    }}
    .sidebar-card:first-of-type {{
      border-top: 0;
    }}
    .pill {{
      display: inline-flex;
      padding: 5px 10px;
      margin: 0 6px 6px 0;
      border-radius: 999px;
      background: rgba(137, 180, 255, 0.1);
      color: var(--accent-3);
      font-size: 0.8rem;
    }}
    .concept-name {{
      font-size: 1.5rem;
      margin: 0 0 8px;
    }}
    .concept-copy {{
      color: var(--muted);
      font-size: 0.96rem;
      line-height: 1.65;
    }}
    .timestamp-list, .path-list, .transcript-list {{
      list-style: none;
      margin: 12px 0 0;
      padding: 0;
      display: grid;
      gap: 10px;
    }}
    .timestamp-list a {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      padding: 12px;
      border-radius: 16px;
      text-decoration: none;
      background: rgba(255, 255, 255, 0.02);
      border: 1px solid var(--line);
    }}
    .mono {{
      font-family: "IBM Plex Mono", monospace;
      color: var(--accent);
      font-size: 0.88rem;
    }}
    .row {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
    }}
    .path-list li {{
      padding: 12px;
      border-radius: 16px;
      background: rgba(255, 255, 255, 0.025);
      border: 1px solid var(--line);
    }}
    .path-step {{
      color: var(--accent-2);
      font-size: 0.8rem;
      text-transform: uppercase;
      letter-spacing: 0.1em;
    }}
    .path-title {{
      font-size: 1rem;
      margin-top: 4px;
    }}
    .path-copy {{
      margin-top: 4px;
      color: var(--muted);
      font-size: 0.92rem;
      line-height: 1.55;
    }}
    .tabs {{
      display: inline-flex;
      gap: 8px;
      padding: 6px;
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid var(--line);
    }}
    .tabs button {{
      border: 0;
      background: transparent;
      color: var(--muted);
      padding: 8px 12px;
      border-radius: 999px;
      cursor: pointer;
      font: inherit;
    }}
    .tabs button.active {{
      background: rgba(124, 224, 195, 0.12);
      color: var(--accent);
    }}
    .transcript-list li {{
      padding: 12px;
      border-radius: 16px;
      background: rgba(255,255,255,0.02);
      border: 1px solid var(--line);
      line-height: 1.55;
      color: var(--muted);
    }}
    .transcript-list strong {{
      display: block;
      margin-bottom: 6px;
      color: var(--accent-3);
    }}
    @media (max-width: 1024px) {{
      .workspace {{
        grid-template-columns: 1fr;
      }}
      #graph {{
        height: 58vh;
        min-height: 460px;
      }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <section class="hero">
      <div class="eyebrow">
        <span>Lecture2Graph</span>
        <span>__LANGUAGE__</span>
        <span>__ENGINE__</span>
      </div>
      <h1>__TITLE__</h1>
      <p class="lede">Understand the lecture instantly: inspect the concept graph, follow the learning path, and jump back to the exact video moments where each idea is introduced.</p>
      <div class="stats">
        <div class="stat"><span class="value">__CONCEPT_COUNT__</span><span class="label">Concepts</span></div>
        <div class="stat"><span class="value">__EDGE_COUNT__</span><span class="label">Dependencies</span></div>
        <div class="stat"><span class="value">__LEARNING_PATH_LENGTH__</span><span class="label">Learning steps</span></div>
        <div class="stat"><span class="value">__TRANSCRIPT_COUNT__</span><span class="label">Transcript segments</span></div>
      </div>
    </section>
    <section class="workspace">
      <article class="panel">
        <div class="panel-header">
          <div class="panel-title">Interactive Concept Graph</div>
          <div class="panel-hint">Pan, zoom, and click a node to highlight dependencies.</div>
        </div>
        <div id="graph"></div>
      </article>
      <aside class="panel sidebar">
        <div class="sidebar-card">
          <div class="panel-title">Selected Concept</div>
          <h2 class="concept-name" id="concept-name">Pick a node</h2>
          <p class="concept-copy" id="concept-description">The sidebar will show the concept summary, timestamps, prerequisites, and dependents.</p>
          <div class="row" id="concept-badges"></div>
        </div>
        <div class="sidebar-card">
          <div class="panel-title">Timestamps</div>
          <ul class="timestamp-list" id="timestamp-list"></ul>
        </div>
        <div class="sidebar-card">
          <div class="panel-title">Connections</div>
          <div class="concept-copy" id="connections-copy">Select a concept to inspect its graph neighborhood.</div>
        </div>
        <div class="sidebar-card">
          <div class="panel-title">Learning Path</div>
          <ol class="path-list" id="learning-path"></ol>
        </div>
        <div class="sidebar-card">
          <div class="panel-header" style="padding:0 0 12px">
            <div class="panel-title">Transcripts</div>
            <div class="tabs">
              <button id="tab-translated" class="active">Translated</button>
              <button id="tab-original">Original</button>
            </div>
          </div>
          <ul class="transcript-list" id="transcript-list"></ul>
        </div>
      </aside>
    </section>
  </div>
  <script>
    const payload = __PAYLOAD__;
    const conceptMap = Object.fromEntries(payload.concepts.map(concept => [concept.id, concept]));
    const prerequisitesByTarget = {};
    const dependentsBySource = {};
    payload.graph.edges.forEach(edge => {{
      prerequisitesByTarget[edge.target] = prerequisitesByTarget[edge.target] || [];
      prerequisitesByTarget[edge.target].push(edge);
      dependentsBySource[edge.source] = dependentsBySource[edge.source] || [];
      dependentsBySource[edge.source].push(edge);
    }});

    const baseNodes = payload.graph.nodes.map(node => {{
      const mentions = node.mention_count || 1;
      let color = "#89b4ff";
      if (mentions >= 8) color = "#7ce0c3";
      else if (mentions >= 4) color = "#ffc670";
      return {{
        id: node.id,
        label: node.label,
        shape: "box",
        font: {{ color: "#eaf4ff", face: "Space Grotesk", size: 16 }},
        borderWidth: 1.5,
        color: {{
          background: color,
          border: color,
          highlight: {{ background: "#ffffff", border: "#7ce0c3" }}
        }},
        margin: 14
      }};
    }});

    const baseEdges = payload.graph.edges.map((edge, index) => {{
      const colors = {{
        domain_rule: "#ffc670",
        causal: "#ff8d8d",
        temporal: "#8ca2b8",
        llm: "#7ce0c3"
      }};
      return {{
        id: index,
        from: edge.source,
        to: edge.target,
        arrows: "to",
        width: edge.evidence === "domain_rule" ? 2.4 : 1.6,
        dashes: edge.evidence === "temporal",
        color: {{ color: colors[edge.evidence] || "#89b4ff", opacity: 0.85 }},
        title: `${{edge.evidence}}: ${{edge.reason || edge.relation}}`,
        smooth: {{ type: "cubicBezier", forceDirection: "vertical", roundness: 0.42 }}
      }};
    }});

    const nodes = new vis.DataSet(baseNodes);
    const edges = new vis.DataSet(baseEdges);
    const network = new vis.Network(
      document.getElementById("graph"),
      {{ nodes, edges }},
      {{
        autoResize: true,
        layout: {{
          hierarchical: {{
            enabled: true,
            direction: "UD",
            levelSeparation: 120,
            nodeSpacing: 180,
            treeSpacing: 210,
            blockShifting: true,
            edgeMinimization: true,
            parentCentralization: true
          }}
        }},
        physics: false,
        interaction: {{
          dragView: true,
          zoomView: true,
          hover: true,
          navigationButtons: true
        }}
      }}
    );

    function graphNeighborhood(nodeId) {{
      const ancestors = new Set();
      const descendants = new Set();
      const incoming = prerequisitesByTarget[nodeId] || [];
      const outgoing = dependentsBySource[nodeId] || [];

      function walkIncoming(current) {{
        (prerequisitesByTarget[current] || []).forEach(edge => {{
          if (!ancestors.has(edge.source)) {{
            ancestors.add(edge.source);
            walkIncoming(edge.source);
          }}
        }});
      }}

      function walkOutgoing(current) {{
        (dependentsBySource[current] || []).forEach(edge => {{
          if (!descendants.has(edge.target)) {{
            descendants.add(edge.target);
            walkOutgoing(edge.target);
          }}
        }});
      }}

      walkIncoming(nodeId);
      walkOutgoing(nodeId);
      return {{ ancestors, descendants, incoming, outgoing }};
    }}

    function resetGraph() {{
      nodes.update(baseNodes);
      edges.update(baseEdges);
    }}

    function renderConcept(nodeId) {{
      const concept = conceptMap[nodeId];
      if (!concept) return;

      const neighborhood = graphNeighborhood(nodeId);
      document.getElementById("concept-name").textContent = concept.name;
      document.getElementById("concept-description").textContent = concept.description;
      document.getElementById("concept-badges").innerHTML = [
        `<span class="pill">${{concept.mention_count}} mentions</span>`,
        `<span class="pill">${{concept.sources.join(", ")}}</span>`
      ].join("");

      document.getElementById("timestamp-list").innerHTML = concept.timestamps.map(item => `
        <li>
          <a href="${{item.url}}" target="_blank" rel="noreferrer">
            <span class="mono">${{item.label}}</span>
            <span>${{item.source}}</span>
          </a>
        </li>
      `).join("");

      const prerequisiteNames = concept.prerequisites.map(item => item.name).join(", ") || "None";
      const dependentNames = concept.dependents.map(item => item.name).join(", ") || "None";
      document.getElementById("connections-copy").innerHTML = `
        <div><strong>Prerequisites:</strong> ${{prerequisiteNames}}</div>
        <div style="margin-top:8px"><strong>Unlocks:</strong> ${{dependentNames}}</div>
      `;

      const nodeUpdates = baseNodes.map(node => {{
        if (node.id === nodeId) {{
          return {{ ...node, color: {{ ...node.color, background: "#ffffff", border: "#7ce0c3" }} }};
        }}
        if (neighborhood.ancestors.has(node.id)) {{
          return {{ ...node, color: {{ ...node.color, background: "#ffc670", border: "#ffc670" }} }};
        }}
        if (neighborhood.descendants.has(node.id)) {{
          return {{ ...node, color: {{ ...node.color, background: "#7ce0c3", border: "#7ce0c3" }} }};
        }}
        return {{ ...node, color: {{ ...node.color, background: "rgba(90, 111, 129, 0.22)", border: "rgba(90, 111, 129, 0.32)" }}, font: {{ ...node.font, color: "#8ca2b8" }} }};
      }});
      nodes.update(nodeUpdates);

      const edgeUpdates = baseEdges.map(edge => {{
        if (edge.from === nodeId || edge.to === nodeId || neighborhood.ancestors.has(edge.from) || neighborhood.descendants.has(edge.to)) {{
          return {{ ...edge, color: {{ ...edge.color, opacity: 1 }}, width: edge.width + 0.8 }};
        }}
        return {{ ...edge, color: {{ ...edge.color, opacity: 0.16 }}, width: Math.max(1, edge.width - 0.4) }};
      }});
      edges.update(edgeUpdates);
    }}

    function renderLearningPath() {{
      document.getElementById("learning-path").innerHTML = payload.learning_path.map(step => `
        <li>
          <div class="path-step">Step ${{step.step}}</div>
          <div class="path-title">${{step.title}}</div>
          <div class="path-copy">${{step.description}}</div>
        </li>
      `).join("");
    }}

    const translatedTranscript = payload.transcripts.translated;
    const originalTranscript = payload.transcripts.original.length ? payload.transcripts.original : payload.transcripts.translated;

    function renderTranscript(mode) {{
      const items = mode === "original" ? originalTranscript : translatedTranscript;
      document.getElementById("transcript-list").innerHTML = items.slice(0, 24).map(item => `
        <li>
          <strong>${{new Date(item.start * 1000).toISOString().substr(14, 5)}} · ${{item.source}}</strong>
          <span>${{item.text}}</span>
        </li>
      `).join("");
      document.getElementById("tab-translated").classList.toggle("active", mode !== "original");
      document.getElementById("tab-original").classList.toggle("active", mode === "original");
    }}

    network.on("click", event => {{
      if (!event.nodes.length) {{
        resetGraph();
        return;
      }}
      renderConcept(event.nodes[0]);
    }});

    document.getElementById("tab-translated").addEventListener("click", () => renderTranscript("translated"));
    document.getElementById("tab-original").addEventListener("click", () => renderTranscript("original"));

    renderLearningPath();
    renderTranscript("translated");
    network.fit({{ animation: true }});
  </script>
</body>
</html>
"""


def render_html(result: LectureGraphResult) -> str:
    replacements = {
        "__TITLE__": result.video.watch_url,
        "__LANGUAGE__": result.video.source_language_label,
        "__ENGINE__": result.video.engine.upper(),
        "__CONCEPT_COUNT__": str(result.stats.concept_count),
        "__EDGE_COUNT__": str(result.stats.edge_count),
        "__LEARNING_PATH_LENGTH__": str(result.stats.learning_path_length),
        "__TRANSCRIPT_COUNT__": str(result.stats.transcript_segment_count),
        "__PAYLOAD__": json.dumps(result.model_dump(mode="json")),
    }
    html = HTML_TEMPLATE
    for key, value in replacements.items():
        html = html.replace(key, value)
    html = html.replace("{{", "{").replace("}}", "}")
    return html

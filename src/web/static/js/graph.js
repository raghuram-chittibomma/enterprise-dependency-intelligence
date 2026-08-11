// FR4/FR5: renders the bounded upstream/downstream dependency subgraph
// for the entity detail page. Fetches plain node/edge JSON from
// `/entities/{id}/graph` (kept viz-library-agnostic in the API) and adapts
// it into Cytoscape.js's `elements` format here.

(function () {
  "use strict";

  const NODE_COLORS_BY_LABEL = {
    Application: "#2563eb",
    Service: "#7c3aed",
    API: "#0891b2",
    Database: "#b45309",
    DataPipeline: "#059669",
    Report: "#64748b",
    Team: "#334155",
    ExternalSystem: "#9333ea",
    BusinessCapability: "#475569",
  };
  const DEFAULT_NODE_COLOR = "#64748b";
  const ROOT_NODE_COLOR = "#dc2626";

  function nodeColor(node) {
    if (node.data("isRoot")) return ROOT_NODE_COLOR;
    return NODE_COLORS_BY_LABEL[node.data("label")] || DEFAULT_NODE_COLOR;
  }

  function toElements(graphData) {
    const nodes = graphData.nodes.map((node) => ({
      data: {
        id: node.id,
        label: node.label,
        name: node.name,
        depth: node.depth,
        isRoot: node.id === graphData.root_id,
      },
    }));
    const edges = graphData.edges.map((edge) => ({
      data: {
        id: `${edge.source_id}->${edge.target_id}->${edge.rel_type}`,
        source: edge.source_id,
        target: edge.target_id,
        relType: edge.rel_type,
      },
    }));
    return [...nodes, ...edges];
  }

  function renderGraph(container, graphData) {
    return cytoscape({
      container,
      elements: toElements(graphData),
      style: [
        {
          selector: "node",
          style: {
            "background-color": nodeColor,
            label: "data(name)",
            "font-size": "10px",
            color: "#1e293b",
            "text-valign": "bottom",
            "text-margin-y": 4,
            width: 28,
            height: 28,
            "border-width": 2,
            "border-color": "#ffffff",
          },
        },
        {
          selector: "edge",
          style: {
            width: 2,
            "line-color": "#94a3b8",
            "target-arrow-color": "#94a3b8",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            label: "data(relType)",
            "font-size": "8px",
            color: "#64748b",
            "text-rotation": "autorotate",
          },
        },
      ],
      layout: {
        name: "breadthfirst",
        directed: true,
        roots: `#${CSS.escape(graphData.root_id)}`,
        spacingFactor: 1.4,
      },
      wheelSensitivity: 0.2,
    });
  }

  async function loadGraph(entityId, direction, depth) {
    const url = `/entities/${encodeURIComponent(entityId)}/graph?direction=${direction}&depth=${depth}`;
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Failed to load dependency graph (${response.status})`);
    }
    return response.json();
  }

  function init() {
    const section = document.querySelector(".graph-section");
    if (!section) return;

    const entityId = section.dataset.entityId;
    const container = document.getElementById("dependency-graph");
    const emptyMessage = document.getElementById("graph-empty-message");
    const directionSelect = document.getElementById("graph-direction");
    const depthSelect = document.getElementById("graph-depth");
    let currentInstance = null;

    async function refresh() {
      const direction = directionSelect.value;
      const depth = depthSelect.value;
      const graphData = await loadGraph(entityId, direction, depth);

      if (currentInstance) {
        currentInstance.destroy();
        currentInstance = null;
      }

      const hasEdges = graphData.nodes.length > 1;
      container.hidden = !hasEdges;
      emptyMessage.hidden = hasEdges;
      if (hasEdges) {
        currentInstance = renderGraph(container, graphData);
      }
    }

    directionSelect.addEventListener("change", refresh);
    depthSelect.addEventListener("change", refresh);
    refresh().catch((err) => {
      emptyMessage.textContent = "Could not load the dependency graph.";
      emptyMessage.hidden = false;
      container.hidden = true;
      console.error(err);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();

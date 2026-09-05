// FR4/FR5: renders the bounded upstream/downstream dependency subgraph
// for the entity detail page. Fetches plain node/edge JSON from
// `/entities/{id}/graph` (kept viz-library-agnostic in the API) and adapts
// it into Cytoscape.js's `elements` format here.

(function () {
  "use strict";

  // High-contrast fills for dark canvas backgrounds.
  const NODE_COLORS_BY_LABEL = {
    Application: "#60a5fa",
    Service: "#c4b5fd",
    API: "#67e8f9",
    Database: "#fcd34d",
    DataPipeline: "#6ee7b7",
    Report: "#cbd5e1",
    Team: "#e2e8f0",
    ExternalSystem: "#f0abfc",
    BusinessCapability: "#bbf7d0",
    Document: "#a5f3fc",
  };
  const DEFAULT_NODE_COLOR = "#cbd5e1";
  const ROOT_NODE_COLOR = "#fb7185";

  const LABEL_STYLE = {
    color: "#ffffff",
    "font-weight": 700,
    "text-outline-width": 0,
    "text-background-color": "#0b1020",
    "text-background-opacity": 0.92,
    "text-background-padding": "3px",
    "text-background-shape": "roundrectangle",
  };

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
            "font-size": "13px",
            "text-valign": "bottom",
            "text-margin-y": 8,
            "text-max-width": 140,
            "text-wrap": "wrap",
            width: 34,
            height: 34,
            "border-width": 2,
            "border-color": "#ffffff",
            ...LABEL_STYLE,
          },
        },
        {
          selector: "node[?isRoot]",
          style: {
            width: 42,
            height: 42,
            "border-width": 3,
            "border-color": "#fecdd3",
          },
        },
        {
          selector: "edge",
          style: {
            width: 2.5,
            "line-color": "#cbd5e1",
            "target-arrow-color": "#f8fafc",
            "target-arrow-shape": "triangle",
            "arrow-scale": 1.2,
            "curve-style": "bezier",
            label: "data(relType)",
            "font-size": "11px",
            "text-rotation": "autorotate",
            "text-margin-y": -8,
            ...LABEL_STYLE,
          },
        },
      ],
      layout: {
        name: "breadthfirst",
        directed: true,
        roots: `#${CSS.escape(graphData.root_id)}`,
        spacingFactor: 1.6,
        padding: 28,
      },
      minZoom: 0.15,
      maxZoom: 4,
      wheelSensitivity: 0.25,
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

  function resizeAndFit(cy) {
    requestAnimationFrame(() => {
      cy.resize();
      cy.fit(undefined, 48);
    });
  }

  function bindViewportControls(cy, shell) {
    if (!shell) return;
    const zoomIn = shell.querySelector("[data-graph-action='zoom-in']");
    const zoomOut = shell.querySelector("[data-graph-action='zoom-out']");
    const fit = shell.querySelector("[data-graph-action='fit']");
    const fullscreen = shell.querySelector("[data-graph-action='fullscreen']");

    if (zoomIn) {
      zoomIn.onclick = () => {
        cy.zoom({
          level: Math.min(cy.maxZoom(), cy.zoom() * 1.3),
          renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 },
        });
      };
    }
    if (zoomOut) {
      zoomOut.onclick = () => {
        cy.zoom({
          level: Math.max(cy.minZoom(), cy.zoom() / 1.3),
          renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 },
        });
      };
    }
    if (fit) {
      fit.onclick = () => cy.fit(undefined, 40);
    }
    if (fullscreen) {
      fullscreen.onclick = () => toggleFullscreen(shell, cy, fullscreen);
    }
  }

  function toggleFullscreen(shell, cy, button) {
    const entering = !shell.classList.contains("is-fullscreen");
    const placeholderId = "dependency-graph-shell-placeholder";

    if (entering) {
      const placeholder = document.createElement("div");
      placeholder.id = placeholderId;
      placeholder.style.display = "none";
      shell.parentNode.insertBefore(placeholder, shell);
      document.body.appendChild(shell);
      shell.classList.add("is-fullscreen");
      document.body.classList.add("graph-fullscreen-active");
      button.setAttribute("aria-pressed", "true");
      button.textContent = "Exit full page";
    } else {
      const placeholder = document.getElementById(placeholderId);
      shell.classList.remove("is-fullscreen");
      document.body.classList.remove("graph-fullscreen-active");
      button.setAttribute("aria-pressed", "false");
      button.textContent = "Full page";
      if (placeholder && placeholder.parentNode) {
        placeholder.parentNode.insertBefore(shell, placeholder);
        placeholder.remove();
      }
    }

    resizeAndFit(cy);
    // Second pass after layout settles (esp. when reparenting).
    setTimeout(() => resizeAndFit(cy), 50);
  }

  function init() {
    const section = document.querySelector(".graph-section");
    if (!section) return;

    const entityId = section.dataset.entityId;
    const shell = document.getElementById("dependency-graph-shell");
    const container = document.getElementById("dependency-graph");
    const emptyMessage = document.getElementById("graph-empty-message");
    const directionSelect = document.getElementById("graph-direction");
    const depthSelect = document.getElementById("graph-depth");
    if (!container || !directionSelect || !depthSelect) return;

    let currentInstance = null;

    document.addEventListener("keydown", (event) => {
      if (event.key !== "Escape" || !shell || !shell.classList.contains("is-fullscreen")) {
        return;
      }
      const fullscreen = shell.querySelector("[data-graph-action='fullscreen']");
      if (currentInstance && fullscreen) {
        toggleFullscreen(shell, currentInstance, fullscreen);
      }
    });

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
      if (emptyMessage) emptyMessage.hidden = hasEdges;
      if (hasEdges) {
        currentInstance = renderGraph(container, graphData);
        bindViewportControls(currentInstance, shell);
      }
    }

    directionSelect.addEventListener("change", refresh);
    depthSelect.addEventListener("change", refresh);
    refresh().catch((err) => {
      if (emptyMessage) {
        emptyMessage.textContent = "Could not load the dependency graph.";
        emptyMessage.hidden = false;
      }
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

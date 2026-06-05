<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import * as d3 from "d3";
import type { Edge, Node } from "../types";

type UnimodEntry = {
  l_unimod_id: number;
  unimod_id: string;
  full_name: string;
  avg_mass: number;
};

type ModificationOption = {
  l_unimod_id: number;
  unimod_id: string;
  title: string;
};

type GraphNode = d3.SimulationNodeDatum & {
  id: string;
  label: string;
  protein: string;
  modification: string;
  size: number;
  color: string;
  visible: boolean;
};

type GraphLink = d3.SimulationLinkDatum<GraphNode> & {
  id: string;
  source: string | GraphNode;
  target: string | GraphNode;
  score: number;
  visible: boolean;
};

const env = import.meta.env.MODE;
const baseApiUrl =
  env === "development"
    ? "http://localhost:5600/tabloidproteome/api/v1/"
    : "/tabloidproteome/api/v1/";

const d3Container = ref<HTMLElement | null>(null);
const svgRef = ref<SVGSVGElement | null>(null);

const showLoader = ref(true);
const dataEdges = ref<Edge[]>([]);
const dataNodes = ref<Node[]>([]);
const dataUnimod = ref<UnimodEntry[]>([]);

const score = ref<[number, number]>([0.6, 1]);
const proteins = ref<string[]>([]);
const modifications = ref<ModificationOption[]>([]);
const proteinNameModel = ref<string[]>([]);
const modificationsVmodel = ref<string[]>([]);

const nodes = ref<GraphNode[]>([]);
const links = ref<GraphLink[]>([]);

const selectedNodeId = ref<string | null>(null);
const selectedNodeNeighbors = ref<Set<string>>(new Set());
const hoveredEdgeId = ref<string | null>(null);

let svgSelection: d3.Selection<SVGSVGElement, unknown, null, undefined> | null = null;
let viewportGroup: d3.Selection<SVGGElement, unknown, null, undefined> | null = null;
let linkSelection: d3.Selection<SVGLineElement, GraphLink, SVGGElement, unknown> | null = null;
let nodeSelection: d3.Selection<SVGCircleElement, GraphNode, SVGGElement, unknown> | null = null;
let labelSelection: d3.Selection<SVGTextElement, GraphNode, SVGGElement, unknown> | null = null;
let zoomBehavior: d3.ZoomBehavior<SVGSVGElement, unknown> | null = null;
let simulation: d3.Simulation<GraphNode, undefined> | null = null;

const fetchJson = async <T,>(endpoint: string): Promise<T> => {
  const response = await fetch(`${baseApiUrl}${endpoint}`);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return (await response.json()) as T;
};

const getDataEdges = async () => {
  dataEdges.value = await fetchJson<Edge[]>("get-edges");
};

const getDataNodes = async () => {
  dataNodes.value = await fetchJson<Node[]>("get-nodes");
};

const getDataModifications = async () => {
  dataUnimod.value = await fetchJson<UnimodEntry[]>("get-unimod");
};

const setFiltersAttributes = () => {
  proteins.value = [...new Set(dataNodes.value.map((node) => node.accession))].sort((a, b) =>
    a.localeCompare(b),
  );

  const nodeUnimodIds = [...new Set(dataNodes.value.map((node) => node.l_unimod_id))].sort(
    (a, b) => a - b,
  );
  modifications.value = nodeUnimodIds
    .map((localUnimodId) => {
      const match = dataUnimod.value.find((entry) => entry.l_unimod_id === localUnimodId);
      if (!match) {
        return null;
      }
      return {
        l_unimod_id: match.l_unimod_id,
        unimod_id: match.unimod_id,
        title: `${match.unimod_id} ${match.full_name} ${match.avg_mass}`,
      };
    })
    .filter((entry): entry is ModificationOption => entry !== null);
};

const getNodeId = (nodeOrId: string | number | GraphNode): string => {
  if (typeof nodeOrId === "string") {
    return nodeOrId;
  }
  if (typeof nodeOrId === "number") {
    return String(nodeOrId);
  }
  return nodeOrId.id;
};

const createGraphData = () => {
  const degreeMap = new Map<string, number>();
  dataEdges.value.forEach((edge) => {
    degreeMap.set(edge.node_a, (degreeMap.get(edge.node_a) ?? 0) + 1);
    degreeMap.set(edge.node_b, (degreeMap.get(edge.node_b) ?? 0) + 1);
  });

  const degrees = [...degreeMap.values()];
  const minDegree = degrees.length ? Math.min(...degrees) : 0;
  const maxDegree = degrees.length ? Math.max(...degrees) : 1;
  const minSize = 4;
  const maxSize = 14;

  const unimodByLocalId = new Map<number, string>();
  modifications.value.forEach((modification) => {
    unimodByLocalId.set(modification.l_unimod_id, modification.unimod_id);
  });

  nodes.value = dataNodes.value.map((node) => {
    const degree = degreeMap.get(node.composite_name) ?? 0;
    const normalizedDegree =
      maxDegree === minDegree ? 0.5 : (degree - minDegree) / (maxDegree - minDegree);
    return {
      id: node.composite_name,
      label: node.composite_name,
      protein: node.accession,
      modification: unimodByLocalId.get(node.l_unimod_id) ?? String(node.l_unimod_id),
      size: minSize + normalizedDegree * (maxSize - minSize),
      color: node.composite_name.includes("ORF") ? "#ff3433" : "#04cccc",
      visible: true,
    };
  });

  links.value = dataEdges.value.map((edge, index) => ({
    id: `${edge.node_a}__${edge.node_b}__${index}`,
    source: edge.node_a,
    target: edge.node_b,
    score: Number(edge.score),
    visible: true,
  }));
};

const isConnectedToSelected = (link: GraphLink): boolean => {
  if (!selectedNodeId.value) {
    return false;
  }
  const source = getNodeId(link.source);
  const target = getNodeId(link.target);
  return source === selectedNodeId.value || target === selectedNodeId.value;
};

const updateVisualState = () => {
  if (!nodeSelection || !linkSelection || !labelSelection) {
    return;
  }

  nodeSelection
    .attr("display", (d) => (d.visible ? null : "none"))
    .attr("fill", (d) => (selectedNodeId.value === d.id ? "#ff8300" : d.color))
    .attr("opacity", (d) => {
      if (!d.visible) {
        return 0;
      }
      if (!selectedNodeId.value) {
        return 1;
      }
      if (d.id === selectedNodeId.value || selectedNodeNeighbors.value.has(d.id)) {
        return 1;
      }
      return 0.15;
    })
    .attr("stroke", (d) => {
      if (d.id === selectedNodeId.value) {
        return "#9d4e00";
      }
      if (selectedNodeNeighbors.value.has(d.id)) {
        return "#2160ba";
      }
      return "#f3f5f7";
    })
    .attr("stroke-width", (d) => {
      if (d.id === selectedNodeId.value) {
        return 2.2;
      }
      if (selectedNodeNeighbors.value.has(d.id)) {
        return 1.4;
      }
      return 0.8;
    });

  linkSelection
    .attr("display", (d) => (d.visible ? null : "none"))
    .attr("stroke", (d) => {
      if (hoveredEdgeId.value === d.id) {
        return "#054cb7";
      }
      if (isConnectedToSelected(d)) {
        return "#990000";
      }
      return "#cccccc";
    })
    .attr("stroke-width", (d) => {
      if (hoveredEdgeId.value === d.id) {
        return 5;
      }
      if (isConnectedToSelected(d)) {
        return 4;
      }
      return 1.4;
    })
    .attr("opacity", (d) => {
      if (!d.visible) {
        return 0;
      }
      if (!selectedNodeId.value) {
        return hoveredEdgeId.value === d.id ? 1 : 0.75;
      }
      return isConnectedToSelected(d) ? 0.95 : 0.1;
    });

  labelSelection
    .attr("display", (d) => (d.visible ? null : "none"))
    .attr("opacity", (d) => {
      if (!selectedNodeId.value) {
        return 0.95;
      }
      return d.id === selectedNodeId.value || selectedNodeNeighbors.value.has(d.id) ? 1 : 0;
    });
};

const applyFilters = () => {
  const minScore = Math.min(score.value[0], score.value[1]);
  const maxScore = Math.max(score.value[0], score.value[1]);

  const visibleNodeIds = new Set<string>();
  nodes.value.forEach((node) => {
    const proteinMatch =
      proteinNameModel.value.length === 0 || proteinNameModel.value.includes(node.protein);
    const modificationMatch =
      modificationsVmodel.value.length === 0 ||
      modificationsVmodel.value.includes(node.modification);
    node.visible = proteinMatch && modificationMatch;
    if (node.visible) {
      visibleNodeIds.add(node.id);
    }
  });

  links.value.forEach((link) => {
    const sourceId = getNodeId(link.source);
    const targetId = getNodeId(link.target);
    const scoreMatch = link.score >= minScore && link.score <= maxScore;
    link.visible = visibleNodeIds.has(sourceId) && visibleNodeIds.has(targetId) && scoreMatch;
  });

  if (selectedNodeId.value && !visibleNodeIds.has(selectedNodeId.value)) {
    selectedNodeId.value = null;
    selectedNodeNeighbors.value = new Set();
  }

  updateVisualState();
};

const setClickedNode = (nodeId: string) => {
  if (selectedNodeId.value === nodeId) {
    selectedNodeId.value = null;
    selectedNodeNeighbors.value = new Set();
    updateVisualState();
    return;
  }

  selectedNodeId.value = nodeId;
  const neighbors = new Set<string>();
  links.value.forEach((link) => {
    const source = getNodeId(link.source);
    const target = getNodeId(link.target);
    if (source === nodeId) {
      neighbors.add(target);
    }
    if (target === nodeId) {
      neighbors.add(source);
    }
  });
  selectedNodeNeighbors.value = neighbors;
  updateVisualState();
};

const initializeD3 = () => {
  if (!svgRef.value || !d3Container.value) {
    return;
  }

  const width = Math.max(300, d3Container.value.clientWidth || 1200);
  const height = Math.max(400, d3Container.value.clientHeight || 850);

  svgSelection = d3.select(svgRef.value);
  svgSelection.selectAll("*").remove();
  svgSelection
    .attr("viewBox", `0 0 ${width} ${height}`)
    .attr("width", "100%")
    .attr("height", "100%");

  viewportGroup = svgSelection.append("g").attr("class", "viewport");

  linkSelection = viewportGroup
    .append("g")
    .attr("class", "links")
    .selectAll<SVGLineElement, GraphLink>("line")
    .data(links.value)
    .join("line")
    .attr("stroke", "#cccccc")
    .attr("stroke-opacity", 0.75)
    .attr("stroke-width", 1.4)
    .on("mouseover", (_, d) => {
      hoveredEdgeId.value = d.id;
      updateVisualState();
    })
    .on("mouseout", () => {
      hoveredEdgeId.value = null;
      updateVisualState();
    });

  nodeSelection = viewportGroup
    .append("g")
    .attr("class", "nodes")
    .selectAll<SVGCircleElement, GraphNode>("circle")
    .data(nodes.value)
    .join("circle")
    .attr("r", (d) => d.size)
    .attr("fill", (d) => d.color)
    .attr("stroke", "#f3f5f7")
    .attr("stroke-width", 0.8)
    .style("cursor", "pointer")
    .on("click", (event, d) => {
      event.stopPropagation();
      setClickedNode(d.id);
    });

  labelSelection = viewportGroup
    .append("g")
    .attr("class", "labels")
    .selectAll<SVGTextElement, GraphNode>("text")
    .data(nodes.value)
    .join("text")
    .text((d) => d.label)
    .attr("font-size", 9)
    .attr("fill", "#1e1e1e")
    .attr("text-anchor", "middle")
    .attr("dy", (d) => -(d.size + 2))
    .style("pointer-events", "none");

  const dragBehavior = d3
    .drag<SVGCircleElement, GraphNode>()
    .on("start", (event, d) => {
      if (!event.active) {
        simulation?.alphaTarget(0.3).restart();
      }
      d.fx = d.x;
      d.fy = d.y;
    })
    .on("drag", (event, d) => {
      d.fx = event.x;
      d.fy = event.y;
    })
    .on("end", (event, d) => {
      if (!event.active) {
        simulation?.alphaTarget(0);
      }
      d.fx = null;
      d.fy = null;
    });

  nodeSelection.call(dragBehavior);

  simulation?.stop();
  simulation = d3
    .forceSimulation(nodes.value)
    .force(
      "link",
      d3
        .forceLink<GraphNode, GraphLink>(links.value)
        .id((d) => d.id)
        .distance(80),
    )
    .force("charge", d3.forceManyBody().strength(-80))
    .force("center", d3.forceCenter(width / 2, height / 2))
    .force(
      "collision",
      d3.forceCollide<GraphNode>().radius((d) => d.size + 2),
    )
    .on("tick", () => {
      linkSelection
        ?.attr("x1", (d) => (d.source as GraphNode).x ?? 0)
        .attr("y1", (d) => (d.source as GraphNode).y ?? 0)
        .attr("x2", (d) => (d.target as GraphNode).x ?? 0)
        .attr("y2", (d) => (d.target as GraphNode).y ?? 0);

      nodeSelection?.attr("cx", (d) => d.x ?? 0).attr("cy", (d) => d.y ?? 0);

      labelSelection?.attr("x", (d) => d.x ?? 0).attr("y", (d) => d.y ?? 0);
    });

  zoomBehavior = d3
    .zoom<SVGSVGElement, unknown>()
    .scaleExtent([0.1, 8])
    .on("zoom", (event) => {
      viewportGroup?.attr("transform", event.transform.toString());
    });

  svgSelection.call(zoomBehavior).on("click", (event) => {
    if (event.target === svgRef.value) {
      selectedNodeId.value = null;
      selectedNodeNeighbors.value = new Set();
      updateVisualState();
    }
  });

  applyFilters();
  showLoader.value = false;
};

const resetGraph = () => {
  selectedNodeId.value = null;
  selectedNodeNeighbors.value = new Set();
  hoveredEdgeId.value = null;
  updateVisualState();
};

const resetZoom = () => {
  if (!svgSelection || !zoomBehavior) {
    return;
  }

  svgSelection.transition().duration(600).call(zoomBehavior.transform, d3.zoomIdentity);
};

const downloadImage = () => {
  if (!svgRef.value || !d3Container.value) {
    return;
  }

  const width = Math.max(300, d3Container.value.clientWidth || 1200);
  const height = Math.max(400, d3Container.value.clientHeight || 850);

  const serializer = new XMLSerializer();
  const svgString = serializer.serializeToString(svgRef.value);
  const svgWithNs = svgString.includes("xmlns=")
    ? svgString
    : svgString.replace("<svg", '<svg xmlns="http://www.w3.org/2000/svg"');

  const blob = new Blob([svgWithNs], { type: "image/svg+xml;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const image = new Image();

  image.onload = () => {
    const canvas = document.createElement("canvas");
    canvas.width = width * 2;
    canvas.height = height * 2;
    const context = canvas.getContext("2d");
    if (!context) {
      URL.revokeObjectURL(url);
      return;
    }

    context.fillStyle = "#ffffff";
    context.fillRect(0, 0, canvas.width, canvas.height);
    context.drawImage(image, 0, 0, canvas.width, canvas.height);

    const pngUrl = canvas.toDataURL("image/png");
    const link = document.createElement("a");
    link.href = pngUrl;
    link.download = "network.png";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  image.src = url;
};

const downloadData = () => {
  const visibleLinks = links.value.filter((link) => link.visible);
  const linksToExport = selectedNodeId.value
    ? visibleLinks.filter((link) => isConnectedToSelected(link))
    : visibleLinks;

  const exported = linksToExport.map((link) => ({
    score: link.score,
    node_a: getNodeId(link.source),
    node_b: getNodeId(link.target),
  }));

  const blob = new Blob([JSON.stringify(exported, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "network.json";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
};

const loadInitialData = async () => {
  try {
    await Promise.all([getDataEdges(), getDataNodes(), getDataModifications()]);
    setFiltersAttributes();
    createGraphData();
  } catch (error) {
    console.error(error);
    showLoader.value = false;
  }
};

onMounted(async () => {
  await loadInitialData();
  await nextTick();
  initializeD3();
});

onBeforeUnmount(() => {
  simulation?.stop();
  simulation = null;
});

watch([proteinNameModel, modificationsVmodel, score], () => {
  applyFilters();
});
</script>

<template lang="pug">
v-row
        .v-col-9
                div(id="loader" v-if="showLoader")
                        p Creating network
                div(
                        id="d3-network"
                        ref="d3Container"
                )
                        svg(ref="svgRef")
        .v-col-3
                div
                        h5 Score
                        v-range-slider(
                                v-model="score"
                                :step="0.1"
                                :max="1"
                                :min="-1"
                        )
                                template(v-slot:prepend)
                                        v-text-field(
                                                v-model="score[0]"
                                                density="compact"
                                                style="width: 70px"
                                                type="number"
                                                step="0.1"
                                                variant="outlined"
                                                hide-details
                                                single-line
                                        )
                                template(v-slot:append)
                                        v-text-field(
                                                v-model="score[1]"
                                                density="compact"
                                                style="width: 70px"
                                                type="number"
                                                step="0.1"
                                                variant="outlined"
                                                hide-details
                                                single-line
                                     )
                div
                        h5 Gene/Protein name
                        v-autocomplete(
                                clearable
                                closable-chips
                                multiple
                                chips
                                v-model="proteinNameModel"
                                :items="proteins"
                        )
                div
                        h5 Modifications
                        v-autocomplete(
                                clearable
                                closable-chips
                                chips
                                v-model="modificationsVmodel"
                                :items="modifications"
                                multiple
                                item-title="title"
                                item-value="unimod_id"
                        )
                div
                        v-btn(
                                block
                                @click="downloadImage"
                        ) Download image
                div.mt-5
                        v-btn(
                                block
                                @click="downloadData"
                        ) Download data
                v-row.mt-5
                        v-col(cols="12" md="6")
                                v-btn.action-btn(
                                        block
                                        @click="resetGraph"
                                ) Reset selections
                        v-col(cols="12" md="6")
                                v-btn.action-btn(
                                        block
                                        @click="resetZoom"
                                ) Reset zoom
                div.licence
                        small
                                | © 2025 -  CompOmics -  Licensed under Apache 2.0
</template>

<style lang="scss" scoped>
#d3-network {
  width: 100%;
  height: 850px;
  background: #ffffff;
}

#d3-network svg {
  width: 100%;
  height: 100%;
  display: block;
}

.licence {
  position: absolute;
  bottom: 10px;
  font-size: 15px;
  color: #888;
}

.action-btn {
  white-space: normal;
  height: auto !important;
  min-height: 36px;
}

:deep(.action-btn .v-btn__content) {
  text-wrap: auto !important;
}
</style>

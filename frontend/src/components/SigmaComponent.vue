<script setup lang="ts">
import {
  useTemplateRef,
  ref,
  reactive,
  watch,
  watchEffect,
  onMounted,
  onBeforeMount,
  render,
} from "vue";
import Graph from "graphology";
import type { Attributes } from "graphology-types"; // gives error ReferenceError: AbstractGraph is not defined
import Sigma from "sigma";
import type { EdgeDisplayData, NodeDisplayData } from "sigma/types"; // check vite for typescript config because all types give errors
import { downloadAsImage } from "@sigma/export-image";
import forceAtlas2 from "graphology-layout-forceatlas2";
import circular from "graphology-layout/circular";
import type { Node, Edge, Unimod } from "../types";
import { useDebounce } from "../use-debounce";

//TODO setup properly env vars to use for dev and prod
const env = import.meta.env.MODE;

const baseApiUrl =
  env === "development"
    ? "http://localhost:5600/tabloidproteome/api/v1/"
    : "/tabloidproteome/api/v1/";

const sigmaContainer = useTemplateRef<HTMLInputElement>("sigma-container");
const loader = useTemplateRef<HTMLInputElement>("loader");
const showLoader = ref(true);
const dataEdges = ref(null);
const dataNodes = ref(null);
const dataUnimod = ref(null);
const renderer = ref(null);
const score = ref([0.6, 1]);
const modifications = ref([]);
const positions = ref([]);
const residues = ref([]);
const proteins = ref([]);
const modificationsVmodel = ref([]);
const positionsVmodel = ref([]);
const residuesVmodel = ref([]);
const proteinNameModel = ref([]);
const pval = ref(null);
const hoveredEdge = ref(null);
const selectedData = ref(null);
const state = reactive({
  hoveredNode: null,
  // hoveredNeighbors: null,
  selectedNode: null,
  selectedNodeNeighbors: null,
});
const debouncedHoveredNode = ref(null);
// const filterState = reactive({
//     modifications: [],
//     score: null,
//     pval: null,
//     protein: []
// })
const filterState = reactive({
  modifications: modificationsVmodel,
  proteins: proteinNameModel,
  residues: residuesVmodel,
  positions: positionsVmodel,
  pval: pval,
  score: score,
});
const graph = new Graph();

onBeforeMount(async () => {
  await getDataEdges();
  await getDataNodes();
  await getDataModifications();
  setFiltersAttributes();
});

watch(filterState, (newValue, oldValue) => {
  const { modifications, proteins, residues, positions, pval, score } = filterState;
  if (modifications.length > 0 || proteins.length > 0) {
    if (modifications.length > 0 && proteins.length == 0) {
      graph.forEachNode((node, { modification }) => {
        graph.setNodeAttribute(node, "hidden", !modifications.includes(modification));
      });
    } else if (modifications.length > 0 && proteins.length > 0) {
      graph.forEachNode((node, { modification, protein }) => {
        graph.setNodeAttribute(
          node,
          "hidden",
          !modifications.includes(modification) || !proteins.includes(protein),
        );
      });
    } else if (modifications.length == 0 && proteins.length > 0) {
      graph.forEachNode((node, { protein }) => {
        graph.setNodeAttribute(node, "hidden", !proteins.includes(protein));
      });
    }
  } else {
    resetGraph();
  }
  if (score != oldValue.score) {
    updateGraphByScore(score);
  }
  renderer.value.refresh({
    // We don't touch the graph data so we can skip its reindexation
    skipIndexation: true,
  });
});
const isNodeVisible = () => {
  let boolArray = [];
  const { modifications, proteins, residues, positions, pval, score } = filterState;
  for (const [key, value] of Object.entries(filterState)) {
    if (key !== "pval" && key !== "score") {
      if (value.length > 0) {
        boolArray.push(true);
      }
    }
  }
};
watch(state, (newValue, oldValue) => {
  if (state.hoveredNode !== undefined && state.hoveredNode !== null) {
    debouncedHoveredNode.value = useDebounce(state.hoveredNode, 40);
    renderer.value.setSetting("nodeReducer", (node: string, data: Attributes) => {
      if (debouncedHoveredNode.value) {
        const res = { ...data };
        if (debouncedHoveredNode.value === node) {
          res.highlighted = true;
        }
        return res;
      }
    });
    renderer.value.refresh({
      // We don't touch the graph data so we can skip its reindexation
      skipIndexation: true,
    });
  }
  if (state.selectedNode !== null) {
    renderer.value.setSetting("nodeReducer", (node: string, data: Attributes) => {
      const res = { ...data };
      if (
        state.selectedNodeNeighbors &&
        !state.selectedNodeNeighbors.has(node) &&
        state.hoveredNode !== node
      ) {
        res.label = "";
        res.color = "#f6f6f6";
        res.zIndex = 0;
      }
      if (state.selectedNode === node) {
        res.label = data.label;
        res.color = "#ff8300";
        res.highlighted = true;
      }
      return res;
    });
    renderer.value.setSetting("edgeReducer", (edge: string, data: Attributes) => {
      const res = { ...data };
      if (
        state.selectedNode &&
        !graph
          .extremities(edge)
          .every((n) => n === state.selectedNode || graph.areNeighbors(n, state.selectedNode))
      ) {
        res.hidden = true;
      } else if (graph.hasExtremity(edge, state.selectedNode)) {
        res.color = "#990000";
        res.size = 4;
        res.zIndex = 1;
      }
      return res;
    });
    renderer.value.refresh({
      // We don't touch the graph data so we can skip its reindexation
      skipIndexation: true,
    });
  }
});
watch(
  () => hoveredEdge.value,
  () => {
    renderer.value.setSetting("edgeReducer", (edge: EdgeDisplayData, data: Attributes) => {
      const res = { ...data };
      if (edge == hoveredEdge.value) {
        res.color = "#054cb7";
        res.size = 4;
        res.label = data.score;
      }
      return res;
    });
    renderer.value.refresh({
      // We don't touch the graph data so we can skip its reindexation
      skipIndexation: true,
    });
  },
);
watch(
  () => dataUnimod.value,
  () => {
    setModifications();
    addDataToGraph();
    setGraph();
  },
);

const updateGraphByFilters = () => {
  updateGraphByModification();
  updateGraphByProteinName();
  renderer.value.refresh({
    // We don't touch the graph data so we can skip its reindexation
    skipIndexation: true,
  });
};
const setGraph = () => {
  circular.assign(graph);
  const settings = forceAtlas2.inferSettings(graph);
  forceAtlas2.assign(graph, { settings, iterations: 100 });
  showLoader.value = false;
  renderer.value = new Sigma(graph, sigmaContainer.value, {
    renderEdgeLabels: false,
    // renderLabels: false,        // get node count to not show node labels if node nb > 5000
    enableEdgeEvents: true,
    defaultEdgeType: "line",
    hideEdgesOnMove: true, // Critical for graphs with >1000 edges
    hideLabelsOnMove: true, // Reduces text rendering during movement
    defaultNodeType: "circle",
    zIndex: true,
  });
  // Bind graph interactions:
  renderer.value.on("enterNode", ({ node }) => {
    // console.log('enterNode')
    setHoveredNode(node);
  });
  renderer.value.on("leaveNode", () => {
    // console.log('leaveNode')
    if (state.selectedNode) {
      return;
    }
    setHoveredNode(undefined);
  });
  renderer.value.on("clickNode", ({ node }) => {
    // console.log('clickNode')
    setClickedNode(node);
  });
  renderer.value.on("enterEdge", ({ edge }) => {
    // console.log('enterEdge',)
    hoveredEdge.value = edge;
    renderer.value.refresh();
  });
  renderer.value.on("leaveEdge", ({ edge }) => {
    hoveredEdge.value = null;
    renderer.value.refresh();
  });
  renderer.value.setSetting("nodeReducer", (node: NodeDisplayData, data: Attributes) => {
    const res = { ...data };
    if (
      state.selectedNodeNeighbors &&
      !state.selectedNodeNeighbors.has(node) &&
      state.selectedNode !== node
    ) {
      // res.label = ''
      res.color = "#0598bc";
      res.zIndex = 0;
      res.highlighted = false;
    }
    if (state.hoveredNode === node) {
      res.highlighted = true;
    }
    if (state.selectedNode !== null || state.selectedNode === node) {
      res.highlighted = true;
      res.color = "#0598bc";
    }
    return res;
  });
  renderer.value.setSetting("edgeReducer", (edge: EdgeDisplayData, data: Attributes) => {
    const res = { ...data };
    if (
      state.selectedNode &&
      !graph
        .extremities(edge)
        .every((n) => n === state.selectedNode || graph.areNeighbors(n, state.selectedNode))
    ) {
      res.hidden = true;
    } else if (graph.hasExtremity(edge, state.selectedNode)) {
      res.color = "#990000";
      res.size = 4;
      ((res.zIndex = 1), (res.label = ""));
    }
    return res;
  });
  filterState.score = score.value;
  updateGraphByScore(score.value);
};
const setClickedNode = (node: string) => {
  // TODO set a boolean variable to toggle node click
  // console.log('setClickedNode', node)
  if (node) {
    console.log("set selectedNode");
    state.selectedNode = node;
    state.selectedNodeNeighbors = new Set(graph.neighbors(node));
  }
};
const setHoveredNode = (node?: string) => {
  if (node) {
    state.hoveredNode = node;
  }
  if (!node) {
    state.hoveredNode = undefined;
  }
};
const updateFilters = (filterType, modelValue) => {
  console.log("updateFilters", modelValue);
  filterState[filterType] = modelValue;
};
const updateGraphByPosition = () => {
  // console.log('updateGraphByPosition', positionsVmodel.value)
  if (positionsVmodel.value !== null && positionsVmodel.value.length !== 0) {
    graph.forEachNode((node, { position }) => {
      graph.setNodeAttribute(node, "hidden", !positionsVmodel.value.includes(position));
    });
    renderer.value.refresh({
      skipIndexation: true,
    });
  } else {
    graph.forEachNode((node) => {
      graph.setNodeAttribute(node, "hidden", false);
    });
    renderer.value.refresh({
      // We don't touch the graph data so we can skip its reindexation
      skipIndexation: true,
    });
  }
};
// TODO review logic to highlight all edged and neighbouring nodes(in diff color)
const updateGraphByProteinName = () => {
  if (proteinNameModel.value !== null && proteinNameModel.value.length !== 0) {
    graph.forEachNode((node, { protein }) => {
      const isHidden = graph.getNodeAttribute(node, "hidden");
      if (isHidden == undefined || !isHidden) {
        graph.setNodeAttribute(node, "hidden", !proteinNameModel.value.includes(protein));
      }
    });
    renderer.value.refresh({
      skipIndexation: true,
    });
  } else {
    resetGraph();
    if (modificationsVmodel.value.length > 0) {
      updateGraphByModification();
    }
  }
};

const updateGraphByResidue = () => {
  if (residuesVmodel.value !== null && residuesVmodel.value.length !== 0) {
    graph.forEachNode((node, { residue }) => {
      graph.setNodeAttribute(node, "hidden", !residuesVmodel.value.includes(residue));
    });
    renderer.value.refresh({
      skipIndexation: true,
    });
  } else {
    graph.forEachNode((node) => {
      graph.setNodeAttribute(node, "hidden", false);
    });
    renderer.value.refresh({
      // We don't touch the graph data so we can skip its reindexation
      skipIndexation: true,
    });
  }
};
const updateGraphByScore = (score: number[]) => {
  renderer.value.setSetting("edgeReducer", (edge: EdgeDisplayData, data: Attributes) => {
    const res = { ...data }; // make a new type for res that extends Attributes with pval and score
    if (res.score >= score[0] && res.score <= score[1]) {
      res.hidden = true;
    }
    return res;
  });
};
const updateGraphByPval = () => {
  renderer.value.setSetting("edgeReducer", (edge: EdgeDisplayData, data: Attributes) => {
    const res = { ...data };
    if (res.pval >= pval.value) {
      res.hidden = true;
    }
    return res;
  });
};
const updateGraphByModification = () => {
  if (modificationsVmodel.value !== null && modificationsVmodel.value.length > 0) {
    graph.forEachNode((node, { modification }) => {
      const isHidden = graph.getNodeAttribute(node, "hidden");
      if (isHidden == undefined || !isHidden) {
        graph.setNodeAttribute(node, "hidden", !modificationsVmodel.value.includes(modification));
      }
    });
    renderer.value.refresh({
      // We don't touch the graph data so we can skip its reindexation
      skipIndexation: true,
    });
  } else {
    resetGraph();
    if (proteinNameModel.value.length > 0) {
      updateGraphByProteinName();
    }
  }
};
const resetZoom = () => {
  // renderer.value.getCamera().goTo({ x: 0, y: 0, angle: 0, ratio: 0.5 })
  renderer.value.getCamera().animatedReset({ duration: 600 });
};
const resetGraph = () => {
  state.selectedNode = null;
  state.selectedNodeNeighbors = null;
  state.hoveredNode = null;
  graph.forEachNode((node) => {
    graph.setNodeAttribute(node, "hidden", undefined);
  });

  renderer.value.refresh({
    // We don't touch the graph data so we can skip its reindexation
    skipIndexation: true,
  });
};
const getMouseLayer = () => {
  return document.querySelector(".sigma-mouse");
};

const addDataToGraph = () => {
  dataNodes.value.forEach((node: Node, index: number) => {
    graph.addNode(node.composite_name, {
      size: 10,
      label: node.composite_name,
      protein: node.accession,
      modification: modifications.value.filter((el) => el.l_unimod_id == node.l_unimod_id)[0]
        .unimod_id,
      position: node.position,
      residue: node.residue,
    });
  });

  dataEdges.value.forEach((edge: Edge, index: number) => {
    graph.addEdge(edge.node_a, edge.node_b, {
      type: "line",
      label: "",
      color: "#cccccc",
      weight: 1,
      score: edge.score,
    });
  });
  const degrees = graph.nodes().map((node) => graph.degree(node));
  const minDegree = Math.min(...degrees);
  const maxDegree = Math.max(...degrees);
  const minSize = 2,
    maxSize = 15;
  graph.forEachNode((node) => {
    const degree = graph.degree(node);
    graph.setNodeAttribute(
      node,
      "size",
      minSize + ((degree - minDegree) / (maxDegree - minDegree)) * (maxSize - minSize),
    );
  });
  graph.forEachNode((node, attributes) => {
    let color = node.includes("ORF") ? "#ff3433" : "#04cccc";
    graph.setNodeAttribute(node, "color", color);
  });
};
const getDataEdges = async () => {
  const url = baseApiUrl + "get-edges";
  try {
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Response status: ${response.status}`);
    }
    const res_json = await response.json();
    dataEdges.value = res_json;
  } catch (error) {
    console.log(error.message);
  }
};
const getDataNodes = async () => {
  const url = baseApiUrl + "get-nodes";
  try {
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Response status: ${response.status}`);
    }
    const res_json = await response.json();
    dataNodes.value = res_json;
  } catch (error) {
    console.log(error.message);
  }
};
const getDataModifications = async () => {
  const url = baseApiUrl + "get-unimod";
  try {
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Response status: ${response.status}`);
    }
    dataUnimod.value = await response.json();
  } catch (error) {
    console.log(error.message);
  }
};
const setFiltersAttributes = () => {
  dataNodes.value.forEach((node: Node) => {
    if (!positions.value.includes(node.position)) {
      positions.value.push(node.position);
    }
    if (!residues.value.includes(node.residue)) {
      residues.value.push(node.residue);
    }
    if (!proteins.value.includes(node.accession)) {
      proteins.value.push(node.accession);
    }
  });
};
const setModifications = async () => {
  dataNodes.value.forEach((node: Node, index: number) => {
    if (index > 0) {
      if (!modifications.value.includes(node.l_unimod_id)) {
        modifications.value.push(node.l_unimod_id);
      }
    }
  });
  modifications.value.sort(compareNumbers);
  modifications.value.forEach((value, index) => {
    const foundUnimod = dataUnimod.value.filter((el) => {
      return el.l_unimod_id == value;
    });
    foundUnimod[0]["title"] =
      foundUnimod[0].unimod_id + " " + foundUnimod[0].full_name + " " + foundUnimod[0].avg_mass;
    modifications.value[index] = foundUnimod[0];
  });
};
const toggleModifications = () => {
  console.log("modifications vmodel", modificationsVmodel.value);
};

const compareNumbers = (a: number, b: number) => {
  return a - b;
};

const downloadImage = () => {
  downloadAsImage(renderer.value, {
    layers: ["edges", "nodes", "edgeLabels", "labels"],
    format: "png",
    fileName: "network.png",
    backgroundColor: "#ffffff",
  });
};
const downloadData = () => {
  let edgesList = [];
  graph.forEachEdge((edge, data) => {
    const res = { ...data };
    if (
      (state.selectedNodeNeighbors && graph.hasExtremity(edge, state.selectedNode)) ||
      graph
        .extremities(edge)
        .every((n) => state.selectedNodeNeighbors.has(n) || n === state.selectedNode)
    ) {
      edgesList.push({
        score: data.score,
        node_a: graph.extremities(edge)[0],
        node_b: graph.extremities(edge)[1],
      });
    }
  });
  const exportedGraph = JSON.stringify(edgesList);
  const blob = new Blob([exportedGraph], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "network.json";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
};
</script>

<template lang="pug">
v-row
    .v-col-9
        div(id="loader" ref="loader" v-if="showLoader")
            p Creating network
        div(
            id="sigma-network"
            ref="sigma-container"
        )
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
                @update:modelValue="updateGraphByFilters"
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
#sigma-network {
  width: 100%;
  height: 850px;
}
.extension-panel {
  max-height: 500px;
  overflow-y: scroll;
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

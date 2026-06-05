<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import cytoscape, {
    type Core,
    type EdgeDefinition,
    type ElementDefinition,
    type EventObject,
    type NodeDefinition,
} from "cytoscape";
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

const env = import.meta.env.MODE;
const baseApiUrl =
    env === "development"
        ? "http://localhost:5600/tabloidproteome/api/v1/"
        : "/tabloidproteome/api/v1/";

const cyContainer = ref<HTMLElement | null>(null);
const cy = ref<Core | null>(null);
const showLoader = ref(true);

const dataEdges = ref<Edge[]>([]);
const dataNodes = ref<Node[]>([]);
const dataUnimod = ref<UnimodEntry[]>([]);

const score = ref<[number, number]>([0.6, 1]);
const proteins = ref<string[]>([]);
const modifications = ref<ModificationOption[]>([]);
const proteinNameModel = ref<string[]>([]);
const modificationsVmodel = ref<string[]>([]);

const selectedNodeId = ref<string | null>(null);
const selectedNodeNeighbors = ref<Set<string>>(new Set());
const hoveredEdgeId = ref<string | null>(null);

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

const createElements = (): ElementDefinition[] => {
    const degreeMap = new Map<string, number>();
    dataEdges.value.forEach((edge) => {
        degreeMap.set(edge.node_a, (degreeMap.get(edge.node_a) ?? 0) + 1);
        degreeMap.set(edge.node_b, (degreeMap.get(edge.node_b) ?? 0) + 1);
    });

    const degrees = [...degreeMap.values()];
    const minDegree = degrees.length ? Math.min(...degrees) : 0;
    const maxDegree = degrees.length ? Math.max(...degrees) : 1;

    const minSize = 16;
    const maxSize = 56;

    const unimodByLocalId = new Map<number, string>();
    modifications.value.forEach((modification) => {
        unimodByLocalId.set(modification.l_unimod_id, modification.unimod_id);
    });

    const nodes: NodeDefinition[] = dataNodes.value.map((node) => {
        const degree = degreeMap.get(node.composite_name) ?? 0;
        const normalizedDegree =
            maxDegree === minDegree ? 0.5 : (degree - minDegree) / (maxDegree - minDegree);

        return {
            data: {
                id: node.composite_name,
                label: node.composite_name,
                protein: node.accession,
                modification: unimodByLocalId.get(node.l_unimod_id) ?? String(node.l_unimod_id),
                sitePosition: node.position,
                residue: node.residue,
                size: minSize + normalizedDegree * (maxSize - minSize),
                color: node.composite_name.includes("ORF") ? "#ff3433" : "#04cccc",
            },
        };
    });

    const edges: EdgeDefinition[] = dataEdges.value.map((edge, index) => ({
        data: {
            id: `${edge.node_a}__${edge.node_b}__${index}`,
            source: edge.node_a,
            target: edge.node_b,
            score: Number(edge.score),
        },
    }));

    return [...nodes, ...edges] as ElementDefinition[];
};

const applySelectionStyling = () => {
    if (!cy.value) {
        return;
    }

    cy.value.batch(() => {
        cy.value?.nodes().removeClass("dimmed selected neighbor");
        cy.value?.edges().removeClass("dimmed highlighted-edge hovered-edge");

        if (selectedNodeId.value) {
            cy.value?.nodes().forEach((node) => {
                const id = String(node.id());
                const isSelected = id === selectedNodeId.value;
                const isNeighbor = selectedNodeNeighbors.value.has(id);
                if (!isSelected && !isNeighbor) {
                    node.addClass("dimmed");
                }
            });

            const selectedNode = cy.value?.$id(selectedNodeId.value);
            selectedNode?.addClass("selected");
            selectedNode?.connectedEdges().forEach((edge) => {
                edge.addClass("highlighted-edge");
            });

            cy.value?.edges().forEach((edge) => {
                if (!edge.hasClass("highlighted-edge")) {
                    edge.addClass("dimmed");
                }
            });

            selectedNodeNeighbors.value.forEach((neighborId) => {
                cy.value?.$id(neighborId).addClass("neighbor");
            });
        }

        if (hoveredEdgeId.value) {
            cy.value?.$id(hoveredEdgeId.value).addClass("hovered-edge");
        }
    });
};

const applyVisibilityFilters = () => {
    if (!cy.value) {
        return;
    }

    const minScore = Math.min(score.value[0], score.value[1]);
    const maxScore = Math.max(score.value[0], score.value[1]);

    cy.value.batch(() => {
        cy.value?.nodes().forEach((node) => {
            const nodeProtein = String(node.data("protein"));
            const nodeModification = String(node.data("modification"));

            const proteinMatch =
                proteinNameModel.value.length === 0 || proteinNameModel.value.includes(nodeProtein);
            const modificationMatch =
                modificationsVmodel.value.length === 0 ||
                modificationsVmodel.value.includes(nodeModification);

            node.style("display", proteinMatch && modificationMatch ? "element" : "none");
        });

        cy.value?.edges().forEach((edge) => {
            const sourceVisible = edge.source().style("display") !== "none";
            const targetVisible = edge.target().style("display") !== "none";
            const edgeScore = Number(edge.data("score") ?? 0);
            const scoreMatch = edgeScore >= minScore && edgeScore <= maxScore;

            edge.style(
                "display",
                sourceVisible && targetVisible && scoreMatch ? "element" : "none",
            );
        });
    });

    applySelectionStyling();
};

const setClickedNode = (nodeId: string) => {
    if (!cy.value) {
        return;
    }

    if (selectedNodeId.value === nodeId) {
        selectedNodeId.value = null;
        selectedNodeNeighbors.value = new Set();
        applySelectionStyling();
        return;
    }

    selectedNodeId.value = nodeId;
    const node = cy.value.$id(nodeId);
    const neighbors = new Set(
        node.neighborhood("node").map((neighborNode) => String(neighborNode.id())),
    );
    selectedNodeNeighbors.value = neighbors;
    applySelectionStyling();
};

const initializeCytoscape = async () => {
    if (!cyContainer.value) {
        return;
    }

    cy.value?.destroy();
    cy.value = cytoscape({
        container: cyContainer.value,
        elements: createElements(),
        style: [
            {
                selector: "node",
                style: {
                    width: "data(size)",
                    height: "data(size)",
                    "background-color": "data(color)",
                    label: "data(label)",
                    color: "#1e1e1e",
                    "font-size": 10,
                    "text-halign": "center",
                    "text-valign": "center",
                    "text-wrap": "ellipsis",
                    "text-max-width": "120px",
                    "border-width": 0.8,
                    "border-color": "#f3f5f7",
                },
            },
            {
                selector: "edge",
                style: {
                    width: "mapData(score, -1, 1, 1, 5)",
                    "line-color": "#a7b4bd",
                    opacity: 0.7,
                    "curve-style": "haystack",
                },
            },
            {
                selector: ".dimmed",
                style: {
                    opacity: 0.15,
                },
            },
            {
                selector: "node.selected",
                style: {
                    "background-color": "#ff8300",
                    opacity: 1,
                    "border-width": 2,
                    "border-color": "#9d4e00",
                },
            },
            {
                selector: "node.neighbor",
                style: {
                    opacity: 1,
                    "border-width": 1.2,
                    "border-color": "#2160ba",
                },
            },
            {
                selector: "edge.highlighted-edge",
                style: {
                    "line-color": "#990000",
                    opacity: 0.95,
                    width: 4,
                },
            },
            {
                selector: "edge.hovered-edge",
                style: {
                    "line-color": "#054cb7",
                    opacity: 1,
                    width: 5,
                },
            },
        ],
        layout: {
            name: "cose",
            fit: true,
            padding: 40,
            animate: false,
        },
    });

    cy.value.on("tap", "node", (event: EventObject) => {
        setClickedNode(String(event.target.id()));
    });

    cy.value.on("tap", (event: EventObject) => {
        if (event.target === cy.value) {
            selectedNodeId.value = null;
            selectedNodeNeighbors.value = new Set();
            applySelectionStyling();
        }
    });

    cy.value.on("mouseover", "edge", (event: EventObject) => {
        hoveredEdgeId.value = String(event.target.id());
        applySelectionStyling();
    });

    cy.value.on("mouseout", "edge", () => {
        hoveredEdgeId.value = null;
        applySelectionStyling();
    });

    applyVisibilityFilters();
    showLoader.value = false;
};

const resetGraph = () => {
    selectedNodeId.value = null;
    selectedNodeNeighbors.value = new Set();
    hoveredEdgeId.value = null;
    applySelectionStyling();
};

const resetZoom = () => {
    cy.value?.fit(cy.value.elements(":visible"), 40);
};

const downloadImage = () => {
    if (!cy.value) {
        return;
    }

    const imageData = cy.value.png({ full: true, scale: 2, bg: "#ffffff" });
    const link = document.createElement("a");
    link.href = imageData;
    link.download = "network.png";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
};

const downloadData = () => {
    if (!cy.value) {
        return;
    }

    let edgesToExport = cy.value.edges(":visible");
    if (selectedNodeId.value) {
        edgesToExport = cy.value.$id(selectedNodeId.value).connectedEdges(":visible");
    }

    const exported = edgesToExport.map((edge) => ({
        score: Number(edge.data("score")),
        node_a: String(edge.data("source")),
        node_b: String(edge.data("target")),
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

onMounted(async () => {
    try {
        await Promise.all([getDataEdges(), getDataNodes(), getDataModifications()]);
        setFiltersAttributes();
        await nextTick();
        await initializeCytoscape();
    } catch (error) {
        console.error(error);
        showLoader.value = false;
    }
});

onBeforeUnmount(() => {
    cy.value?.destroy();
});

watch([proteinNameModel, modificationsVmodel, score], () => {
    applyVisibilityFilters();
});
</script>

<template lang="pug">
v-row
    .v-col-lg-10.v-col-md-9
        div(id="loader" v-if="showLoader")
            p Creating network
        div(
            id="cy-network"
            ref="cyContainer"
        )
    .v-col-lg-2.v-col-md-3
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
#cy-network {
    width: 100%;
    height: 850px;
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

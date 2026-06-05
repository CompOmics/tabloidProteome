<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { Cosmograph } from "@cosmograph/cosmograph";
import type { Edge, Node, Unimod } from "../types";

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

type GraphPoint = {
    pointIndex: number;
    id: string;
    label: string;
    protein: string;
    modification: string;
    size: number;
};

type GraphLink = {
    id: string;
    source: string;
    target: string;
    linkSourceIndex: number;
    linkTargetIndex: number;
    score: number;
};

const env = import.meta.env.MODE;
const baseApiUrl =
    env === "development"
        ? "http://localhost:5600/tabloidproteome/api/v1/"
        : "/tabloidproteome/api/v1/";

const cosmographContainer = ref<HTMLElement | null>(null);
const cosmographInstance = ref<Cosmograph | null>(null);

const showLoader = ref(true);
const dataEdges = ref<Edge[]>([]);
const dataNodes = ref<Node[]>([]);
const dataUnimod = ref<UnimodEntry[]>([]);

const score = ref<[number, number]>([0.6, 1]);
const proteins = ref<string[]>([]);
const modifications = ref<ModificationOption[]>([]);
const proteinNameModel = ref<string[]>([]);
const modificationsVmodel = ref<string[]>([]);

const allPoints = ref<GraphPoint[]>([]);
const allLinks = ref<GraphLink[]>([]);
const visiblePoints = ref<GraphPoint[]>([]);
const visibleLinks = ref<GraphLink[]>([]);
const renderPoints = ref<GraphPoint[]>([]);
const renderLinks = ref<GraphLink[]>([]);

const DEBUG_COSMOGRAPH = true;

const logDebug = (label: string, payload: unknown) => {
    if (!DEBUG_COSMOGRAPH) {
        return;
    }
    console.log(`[Cosmograph Debug] ${label}`, payload);
};

const fetchJson = async <T,>(endpoint: string): Promise<T> => {
    const response = await fetch(`${baseApiUrl}${endpoint}`);
    if (!response.ok) {
        throw new Error(`Request failed: ${response.status}`);
    }
    return (await response.json()) as T;
};

const getDataEdges = async () => {
    dataEdges.value = await fetchJson<Edge[]>("get-edges");
    logDebug("Fetched edges", {
        count: dataEdges.value.length,
        sample: dataEdges.value.slice(0, 5),
        nullishNodeA: dataEdges.value.filter((edge) => edge?.node_a == null).length,
        nullishNodeB: dataEdges.value.filter((edge) => edge?.node_b == null).length,
        nullishScore: dataEdges.value.filter((edge) => edge?.score == null).length,
    });
};

const getDataNodes = async () => {
    dataNodes.value = await fetchJson<Node[]>("get-nodes");
    logDebug("Fetched nodes", {
        count: dataNodes.value.length,
        sample: dataNodes.value.slice(0, 5),
        nullishCompositeName: dataNodes.value.filter((node) => node?.composite_name == null).length,
        nullishAccession: dataNodes.value.filter((node) => node?.accession == null).length,
        nullishUnimodId: dataNodes.value.filter((node) => node?.l_unimod_id == null).length,
    });
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

const getPointNeighbors = (pointId: string): Set<string> => {
    const neighbors = new Set<string>();
    visibleLinks.value.forEach((link) => {
        if (link.source === pointId) {
            neighbors.add(link.target);
        }
        if (link.target === pointId) {
            neighbors.add(link.source);
        }
    });
    return neighbors;
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
    const minSize = 2;
    const maxSize = 15;

    const unimodByLocalId = new Map<number, string>();
    modifications.value.forEach((modification) => {
        unimodByLocalId.set(modification.l_unimod_id, modification.unimod_id);
    });

    const uniquePoints = new Map<string, GraphPoint>();

    dataNodes.value.forEach((node) => {
        const pointId = String(node.composite_name ?? "").trim();
        if (!pointId || uniquePoints.has(pointId)) {
            return;
        }

        const degree = degreeMap.get(node.composite_name) ?? 0;
        const normalizedDegree =
            maxDegree === minDegree ? 0.5 : (degree - minDegree) / (maxDegree - minDegree);

        uniquePoints.set(pointId, {
            pointIndex: uniquePoints.size,
            id: pointId,
            label: pointId,
            protein: node.accession,
            modification: unimodByLocalId.get(node.l_unimod_id) ?? String(node.l_unimod_id),
            size: minSize + normalizedDegree * (maxSize - minSize),
        });
    });

    allPoints.value = [...uniquePoints.values()];

    const pointIds = new Set(allPoints.value.map((point) => point.id));

    allLinks.value = dataEdges.value
        .map((edge, index) => {
            const source = String(edge.node_a ?? "").trim();
            const target = String(edge.node_b ?? "").trim();
            const numericScore = Number(edge.score);

            if (
                !source ||
                !target ||
                !pointIds.has(source) ||
                !pointIds.has(target) ||
                !Number.isFinite(numericScore)
            ) {
                return null;
            }

            return {
                id: `${source}__${target}__${index}`,
                source,
                target,
                linkSourceIndex: 0,
                linkTargetIndex: 0,
                score: numericScore,
            };
        })
        .filter((link): link is GraphLink => link !== null);

    logDebug("Prepared graph data", {
        pointsCount: allPoints.value.length,
        linksCount: allLinks.value.length,
        pointsSample: allPoints.value.slice(0, 5),
        linksSample: allLinks.value.slice(0, 5),
        invalidPointIndex: allPoints.value.filter((point) => !Number.isFinite(point.pointIndex))
            .length,
        invalidLinkSourceIndex: allLinks.value.filter(
            (link) => !Number.isFinite(link.linkSourceIndex),
        ).length,
        invalidLinkTargetIndex: allLinks.value.filter(
            (link) => !Number.isFinite(link.linkTargetIndex),
        ).length,
        nullishPointId: allPoints.value.filter((point) => point.id == null).length,
        nullishLinkSource: allLinks.value.filter((link) => link.source == null).length,
        nullishLinkTarget: allLinks.value.filter((link) => link.target == null).length,
    });
};

const applyFilters = () => {
    const minScore = Math.min(score.value[0], score.value[1]);
    const maxScore = Math.max(score.value[0], score.value[1]);

    visiblePoints.value = allPoints.value.filter((point) => {
        const proteinMatch =
            proteinNameModel.value.length === 0 || proteinNameModel.value.includes(point.protein);
        const modificationMatch =
            modificationsVmodel.value.length === 0 ||
            modificationsVmodel.value.includes(point.modification);
        return proteinMatch && modificationMatch;
    });

    const visiblePointIds = new Set(visiblePoints.value.map((point) => point.id));
    visibleLinks.value = allLinks.value.filter((link) => {
        const scoreMatch = link.score >= minScore && link.score <= maxScore;
        return scoreMatch && visiblePointIds.has(link.source) && visiblePointIds.has(link.target);
    });

    renderPoints.value = visiblePoints.value.map((point, index) => {
        return {
            ...point,
            pointIndex: index,
        };
    });

    const renderIndexByPointId = new Map<string, number>();
    renderPoints.value.forEach((point) => {
        renderIndexByPointId.set(point.id, point.pointIndex);
    });

    renderLinks.value = visibleLinks.value
        .map((link) => {
            const linkSourceIndex = renderIndexByPointId.get(link.source);
            const linkTargetIndex = renderIndexByPointId.get(link.target);
            if (linkSourceIndex === undefined || linkTargetIndex === undefined) {
                return null;
            }

            return {
                ...link,
                linkSourceIndex,
                linkTargetIndex,
            };
        })
        .filter((link): link is GraphLink => link !== null);

    logDebug("Prepared render data", {
        renderPointsCount: renderPoints.value.length,
        renderLinksCount: renderLinks.value.length,
        renderPointsSample: renderPoints.value.slice(0, 5),
        renderLinksSample: renderLinks.value.slice(0, 5),
        invalidRenderPointIndex: renderPoints.value.filter(
            (point) => !Number.isFinite(point.pointIndex),
        ).length,
        invalidRenderLinkSourceIndex: renderLinks.value.filter(
            (link) => !Number.isFinite(link.linkSourceIndex),
        ).length,
        invalidRenderLinkTargetIndex: renderLinks.value.filter(
            (link) => !Number.isFinite(link.linkTargetIndex),
        ).length,
    });
};

const getBaseConfig = () => ({
    pointIdBy: "id",
    pointIndexBy: "pointIndex",
    linkSourceBy: "source",
    linkTargetBy: "target",
    linkSourceIndexBy: "linkSourceIndex",
    linkTargetIndexBy: "linkTargetIndex",
    pointLabelBy: "label",
    pointSizeBy: "size",
    links: [],
});

const getRenderPayload = () => {
    const points = renderPoints.value
        .filter((point) => point && point.id && Number.isFinite(point.pointIndex))
        .map((point) => ({
            pointIndex: point.pointIndex,
            id: point.id,
            label: point.label,
            protein: point.protein,
            modification: point.modification,
            size: point.size,
        }));

    const pointIndexById = new Map<string, number>();
    points.forEach((point) => {
        pointIndexById.set(point.id, point.pointIndex);
    });

    const links = renderLinks.value
        .map((link) => {
            const linkSourceIndex = pointIndexById.get(link.source);
            const linkTargetIndex = pointIndexById.get(link.target);
            if (
                !link ||
                !link.source ||
                !link.target ||
                linkSourceIndex === undefined ||
                linkTargetIndex === undefined
            ) {
                return null;
            }

            return {
                id: link.id,
                source: link.source,
                target: link.target,
                linkSourceIndex,
                linkTargetIndex,
                score: link.score,
            };
        })
        .filter((link): link is NonNullable<typeof link> => link !== null);

    logDebug("Payload passed to Cosmograph", {
        pointsCount: points.length,
        linksCount: links.length,
        pointsSample: points.slice(0, 5),
        linksSample: links.slice(0, 5),
        invalidPayloadPointIndex: points.filter((point) => !Number.isFinite(point.pointIndex))
            .length,
        invalidPayloadLinkSourceIndex: links.filter(
            (link) => !Number.isFinite(link.linkSourceIndex),
        ).length,
        invalidPayloadLinkTargetIndex: links.filter(
            (link) => !Number.isFinite(link.linkTargetIndex),
        ).length,
    });

    return { points, links };
};

const renderGraph = () => {
    applyFilters();

    if (!cosmographInstance.value) {
        return;
    }

    const { points, links } = getRenderPayload();

    if (points.length === 0) {
        return;
    }

    try {
        cosmographInstance.value.setConfig({
            ...getBaseConfig(),
            points,
            links,
        });
    } catch (error) {
        console.error("Cosmograph setConfig failed", error);
        cosmographInstance.value.setConfig({
            ...getBaseConfig(),
            points,
            links: [],
        });
    }
};

const initializeCosmograph = () => {
    if (!cosmographContainer.value) {
        return;
    }

    if (renderPoints.value.length === 0) {
        showLoader.value = false;
        return;
    }

    const { points, links } = getRenderPayload();

    try {
        cosmographInstance.value = new Cosmograph(cosmographContainer.value, {
            ...getBaseConfig(),
            points,
            links,
        });
    } catch (error) {
        console.error("Failed to initialize Cosmograph", error);
        showLoader.value = false;
        return;
    }

    renderGraph();
    cosmographInstance.value.fitView(250, 0.1);
    showLoader.value = false;
};

const loadGraphData = async () => {
    await Promise.all([getDataEdges(), getDataNodes(), getDataModifications()]);
    setFiltersAttributes();
    createGraphData();
    applyFilters();
};

const resetGraph = () => {
    proteinNameModel.value = [];
    modificationsVmodel.value = [];
    score.value = [0.6, 1];
    renderGraph();
};

const resetZoom = () => {
    cosmographInstance.value?.fitView(600, 0.1);
};

const downloadImage = () => {
    cosmographInstance.value?.captureScreenshot("network", 2);
};

const downloadData = () => {
    // const linksToExport = selectedPointId.value
    //     ? visibleLinks.value.filter(
    //           (link) =>
    //               link.source === selectedPointId.value || link.target === selectedPointId.value,
    //       )
    //     : visibleLinks.value;
    // const exported = linksToExport.map((link) => ({
    //     score: link.score,
    //     node_a: link.source,
    //     node_b: link.target,
    // }));
    // const blob = new Blob([JSON.stringify(exported, null, 2)], { type: "application/json" });
    // const url = URL.createObjectURL(blob);
    // const link = document.createElement("a");
    // link.href = url;
    // link.download = "network.json";
    // document.body.appendChild(link);
    // link.click();
    // document.body.removeChild(link);
    // URL.revokeObjectURL(url);
};

onMounted(async () => {
    try {
        await nextTick();
        await loadGraphData();
        initializeCosmograph();
    } catch (error) {
        console.error(error);
        showLoader.value = false;
    }
});

onBeforeUnmount(() => {
    void cosmographInstance.value?.destroy();
    cosmographInstance.value = null;
});

watch([proteinNameModel, modificationsVmodel, score], () => {
    renderGraph();
});
</script>

<template lang="pug">
v-row
        .v-col-9
                div(id="loader" v-if="showLoader")
                        p Creating network
                div(
                        id="cosmograph-network"
                        ref="cosmographContainer"
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
#cosmograph-network {
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

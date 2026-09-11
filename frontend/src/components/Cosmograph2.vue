<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { Cosmograph, prepareCosmographData } from "@cosmograph/cosmograph";
import * as d3 from "d3";

type ApiNode = {
    composite_name: string;
    composite_gene_name: string;
    accession: string;
    gene_name: string;
    position: string | null;
    residue: string | null;
    unimod_id: string;
    full_name: string;
};
type ApiEdge = {
    node_a: string;
    node_b: string;
    score: number;
    qvalue: number | null;
    same_protein: number | null;
    same_site: number | null;
    position_gap: number | null;
    same_mod: number | null;
    shared_peptide: number | null;
};
type UnimodEntry = { unimod_id: string; full_name: string; avg_mass: number };
type HistoBin = { lo: number; hi: number; count: number };

const BASE_URL =
    import.meta.env.MODE === "development"
        ? "http://localhost:5600/tabloidproteome/api/v1/"
        : "/tabloidproteome/api/v1/";

async function fetchJson<T>(endpoint: string): Promise<T> {
    const res = await fetch(BASE_URL + endpoint);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
}

// — Graph instance —
const container = ref<HTMLDivElement | null>(null);
const cosmographInstance = ref<Cosmograph | null>(null);

// — Raw data from the API —
const allNodes = ref<ApiNode[]>([]);
const allEdges = ref<ApiEdge[]>([]);
const unimodEntries = ref<UnimodEntry[]>([]);

// — Filter state —
// Slider's lower bound. Edge count explodes below ~0.35 (4.1M edges at 0.35, 11.1M at 0.3,
// ~19M — the whole table — at 0.2-0.25): past that cliff a force-directed layout isn't
// meaningfully renderable regardless of fetch/query speed, so the floor is set past it rather
// than at the true global minimum (0.2). Hardcoded rather than queried at runtime — the
// dataset only changes on a manual re-ingest.
const DATA_MIN_SCORE = 0.4;
// The selection itself still starts at 0.6 regardless of that bound.
const scoreRange = ref<[number, number]>([0.6, 1]);
// Live count of edges matching the current score range, shown next to the slider so users see
// the fetch size before it happens rather than discovering it by a frozen tab.
const edgeCount = ref<number | null>(null);
const selectedProteins = ref<string[]>([]);
const selectedMods = ref<string[]>([]);
const proteinFilterField = ref<"accession" | "gene_name">("accession");

// — Color scheme —
type ColorScheme = "degree" | "modification";
const colorScheme = ref<ColorScheme>("degree");

const DEGREE_PALETTE = ["#c6dbef", "#08306b"];
const MOD_PALETTE = [
    "#4e79a7",
    "#f28e2b",
    "#e15759",
    "#76b7b2",
    "#59a14f",
    "#edc948",
    "#b07aa1",
    "#ff9da7",
    "#9c755f",
    "#bab0ac",
    "#86bcb6",
    "#ff9888",
];

// — Legend state —
const degreeRange = ref<{ min: number; max: number }>({ min: 0, max: 0 });
const modLegendItems = ref<Array<{ name: string; color: string }>>([]);
const currentModColorMap = ref<Record<string, string>>({});

// — Selected item (shown in the info panel) —
const selectedNode = ref<ApiNode | null>(null);
const selectedEdge = ref<ApiEdge | null>(null);

// — Filter options derived from the loaded data —
const proteinOptions = computed(() =>
    [...new Set(allNodes.value.map((n) => n[proteinFilterField.value]))].sort(),
);

const modificationOptions = computed(() => {
    const uniqueIds = [...new Set(allNodes.value.map((n) => n.unimod_id))].sort();
    return uniqueIds.map((id) => {
        const fullName = allNodes.value.find((n) => n.unimod_id === id)?.full_name ?? "";
        const avgMass = unimodEntries.value.find((u) => u.unimod_id === id)?.avg_mass;
        return {
            value: id,
            title: avgMass !== undefined ? `${id} ${fullName} (${avgMass})` : `${id} ${fullName}`,
        };
    });
});

// Track the arrays currently rendered — click callbacks receive numeric indices into these
const renderedNodes = ref<ApiNode[]>([]);
const renderedEdges = ref<ApiEdge[]>([]);

const connectedEdges = computed(() => {
    if (!selectedNode.value) return [];
    const name = selectedNode.value.composite_name;
    return renderedEdges.value.filter((e) => e.node_a === name || e.node_b === name);
});

const selectedNodeModDisplay = computed(() => {
    if (!selectedNode.value) return "";
    return `${selectedNode.value.full_name} (${selectedNode.value.unimod_id})`;
});

const histogramBins = computed((): HistoBin[] | null => {
    const edges = connectedEdges.value;
    if (edges.length < 2) return null;

    const lo = Math.min(scoreRange.value[0], scoreRange.value[1]);
    const hi = Math.max(scoreRange.value[0], scoreRange.value[1]);
    const span = hi - lo;
    if (span <= 0) return null;

    const BIN_COUNT = 5;
    const binW = span / BIN_COUNT;
    const counts = new Array<number>(BIN_COUNT).fill(0);
    edges.forEach((e) => {
        const idx = Math.min(Math.floor((e.score - lo) / binW), BIN_COUNT - 1);
        if (idx >= 0 && idx < BIN_COUNT) counts[idx]++;
    });

    return Array.from({ length: BIN_COUNT }, (_, i) => ({
        lo: lo + i * binW,
        hi: lo + (i + 1) * binW,
        count: counts[i],
    }));
});

const histogramRef = ref<HTMLDivElement | null>(null);

function drawHistogram() {
    const el = histogramRef.value;
    if (!el) return;
    d3.select(el).selectAll("*").remove();
    const bins = histogramBins.value;
    if (!bins) return;

    d3.select(el).style("position", "relative");

    const W = el.getBoundingClientRect().width || el.offsetWidth || 200;
    const margin = { top: 4, right: 2, bottom: 20, left: 2 };
    const innerW = W - margin.left - margin.right;
    const innerH = 38;

    const lo = bins[0].lo;
    const hi = bins[bins.length - 1].hi;
    const maxCount = Math.max(...bins.map((b) => b.count), 1);

    const xScale = d3.scaleLinear([lo, hi], [0, innerW]);
    const yScale = d3.scaleLinear([0, maxCount], [innerH, 0]);

    const svg = d3
        .select(el)
        .append("svg")
        .attr("width", W)
        .attr("height", innerH + margin.top + margin.bottom);

    const g = svg.append("g").attr("transform", `translate(${margin.left},${margin.top})`);

    const tooltip = d3
        .select(el)
        .append("div")
        .style("position", "absolute")
        .style("background", "rgba(0,0,0,0.72)")
        .style("color", "#fff")
        .style("padding", "3px 8px")
        .style("border-radius", "4px")
        .style("font-size", "11px")
        .style("line-height", "1.4")
        .style("pointer-events", "none")
        .style("white-space", "nowrap")
        .style("opacity", "0")
        .style("transition", "opacity 0.1s");

    g.selectAll<SVGRectElement, HistoBin>("rect")
        .data(bins)
        .join("rect")
        .attr("x", (d) => xScale(d.lo) + 1)
        .attr("y", (d) => (d.count > 0 ? yScale(d.count) : innerH))
        .attr("width", (d) => Math.max(xScale(d.hi) - xScale(d.lo) - 2, 0))
        .attr("height", (d) => Math.max(innerH - yScale(d.count), 0))
        .attr("fill", "#4a9eff")
        .attr("rx", 1)
        .attr("opacity", 0.85)
        .on("mouseover", (event: MouseEvent, d: HistoBin) => {
            d3.select(event.currentTarget as Element).attr("opacity", 1);
            const [px, py] = d3.pointer(event, el);
            tooltip
                .html(
                    `<strong>${d.count}</strong> edge${d.count !== 1 ? "s" : ""}<br>${d.lo.toFixed(2)} – ${d.hi.toFixed(2)}`,
                )
                .style("opacity", "1")
                .style("left", `${px + 8}px`)
                .style("top", `${py - 38}px`);
        })
        .on("mousemove", (event: MouseEvent) => {
            const [px, py] = d3.pointer(event, el);
            tooltip.style("left", `${px + 8}px`).style("top", `${py - 38}px`);
        })
        .on("mouseleave", (event: MouseEvent) => {
            d3.select(event.currentTarget as Element).attr("opacity", 0.85);
            tooltip.style("opacity", "0");
        });

    g.append("g")
        .attr("transform", `translate(0,${innerH})`)
        .call(
            d3
                .axisBottom(xScale)
                .ticks(6)
                .tickSize(3)
                .tickFormat((d) => (d as number).toFixed(2)),
        )
        .call((axis) => {
            axis.select(".domain").attr("stroke", "#ccc");
            axis.selectAll(".tick line").attr("stroke", "#999");
            axis.selectAll<SVGTextElement, unknown>(".tick text")
                .style("font-size", "8px")
                .attr("fill", "#888");
        });
}

watch(histogramBins, drawHistogram, { immediate: true, flush: "post" });

// — Color helpers —

function buildModColors(nodes: ApiNode[]) {
    const uniqueModIds = [...new Set(nodes.map((n) => n.unimod_id))].sort();
    const colorMap: Record<string, string> = {};
    const legendItems: Array<{ name: string; color: string }> = [];
    uniqueModIds.forEach((unimodId, i) => {
        const fullName = nodes.find((n) => n.unimod_id === unimodId)?.full_name ?? unimodId;
        const color = MOD_PALETTE[i % MOD_PALETTE.length];
        colorMap[unimodId] = color;
        legendItems.push({ name: `${unimodId} — ${fullName}`, color });
    });
    currentModColorMap.value = colorMap;
    modLegendItems.value = legendItems;
}

function computeDegreeRange(nodes: ApiNode[], edges: ApiEdge[]) {
    const dm = new Map<string, number>(nodes.map((n) => [n.composite_name, 0]));
    edges.forEach((e) => {
        dm.set(e.node_a, (dm.get(e.node_a) ?? 0) + 1);
        dm.set(e.node_b, (dm.get(e.node_b) ?? 0) + 1);
    });
    const vals = [...dm.values()];
    degreeRange.value = {
        min: vals.length ? Math.min(...vals) : 0,
        max: vals.length ? Math.max(...vals) : 0,
    };
}

// — Data helpers —

function filterData(): { nodes: ApiNode[]; edges: ApiEdge[] } {
    const [minScore, maxScore] =
        scoreRange.value[0] <= scoreRange.value[1]
            ? scoreRange.value
            : [scoreRange.value[1], scoreRange.value[0]];

    const nodes = allNodes.value.filter((n) => {
        const proteinOk =
            selectedProteins.value.length === 0 ||
            selectedProteins.value.includes(n[proteinFilterField.value]);
        const modOk = selectedMods.value.length === 0 || selectedMods.value.includes(n.unimod_id);
        return proteinOk && modOk;
    });

    const nodeIds = new Set(nodes.map((n) => n.composite_name));
    const edges = allEdges.value.filter(
        (e) =>
            e.score >= minScore &&
            e.score <= maxScore &&
            nodeIds.has(e.node_a) &&
            nodeIds.has(e.node_b),
    );

    return { nodes, edges };
}

let storedPrepared: Awaited<ReturnType<typeof prepareCosmographData>> | null = null;

async function prepareData(nodes: ApiNode[], edges: ApiEdge[]) {
    const validEdges = edges.filter((e) => e.node_a && e.node_b);

    buildModColors(nodes);
    computeDegreeRange(nodes, validEdges);

    const useGene = proteinFilterField.value === "gene_name";

    const points = nodes.map((n) => ({
        id: n.composite_name,
        mod_name: n.unimod_id,
        label: formatPipedLabel(useGene ? n.composite_gene_name : n.composite_name),
    }));
    const links = validEdges.map((e) => ({ source: e.node_a, target: e.node_b, score: e.score }));

    const prepared = await prepareCosmographData(
        {
            points: { pointIdBy: "id", pointIncludeColumns: ["mod_name", "label"] },
            links: {
                linkSourceBy: "source",
                linkTargetsBy: ["target"],
                linkIncludeColumns: ["score"],
            },
        },
        points,
        links,
    );

    renderedNodes.value = nodes;
    renderedEdges.value = validEdges;
    storedPrepared = prepared;

    return prepared;
}

// — Highlight helpers —
function highlightNode(index: number) {
    cosmographInstance.value?.selectPoint(index, false, true);
    cosmographInstance.value?.setFocusedPoint(index);
}

function highlightEdgeEndpoints(edge: ApiEdge) {
    const srcIdx = renderedNodes.value.findIndex((n) => n.composite_name === edge.node_a);
    const tgtIdx = renderedNodes.value.findIndex((n) => n.composite_name === edge.node_b);
    cosmographInstance.value?.unselectAllPoints();
    if (srcIdx !== -1) cosmographInstance.value?.selectPoint(srcIdx, false, false);
    if (tgtIdx !== -1) cosmographInstance.value?.selectPoint(tgtIdx, true, false);
    cosmographInstance.value?.setFocusedPoint(undefined);
}

function clearHighlight() {
    cosmographInstance.value?.unselectAllPoints();
    cosmographInstance.value?.setFocusedPoint(undefined);
}

function buildColorConfig() {
    if (colorScheme.value === "degree") {
        return {
            pointColorStrategy: "preciseDegree" as const,
            pointColorPalette: DEGREE_PALETTE,
        };
    }
    return {
        pointColorBy: "mod_name",
        pointColorStrategy: "map" as const,
        pointColorByMap: currentModColorMap.value,
    };
}

// setConfig merges against defaults, not the previous config — all non-data options
// must be included in every setConfig call or they are reset to defaults.
function buildNonDataConfig() {
    return {
        ...buildColorConfig(),
        pointGreyoutOpacity: 0.1,
        linkGreyoutOpacity: 0.05,
        focusedPointRingColor: "#f59e0b",
        pointLabelBy: "label",
        showLabels: true,
        showDynamicLabels: false,
        showTopLabels: false,
        showUnselectedPointLabels: false,
        linkWidthBy: "score",
        simulationDecay: 500,
        onClick: (index: number | undefined) => {
            selectedEdge.value = null;
            if (index !== undefined) {
                const clicked = renderedNodes.value[index] ?? null;
                const alreadySelected =
                    clicked?.composite_name === selectedNode.value?.composite_name;
                if (alreadySelected) {
                    selectedNode.value = null;
                    clearHighlight();
                } else {
                    selectedNode.value = clicked;
                    highlightNode(index);
                }
            } else {
                selectedNode.value = null;
                clearHighlight();
            }
        },
        onLinkClick: (linkIndex: number) => {
            selectedNode.value = null;
            const edge = renderedEdges.value[linkIndex] ?? null;
            selectedEdge.value = edge;
            if (edge) highlightEdgeEndpoints(edge);
            else clearHighlight();
        },
        onSimulationEnd,
    };
}

function buildConfig(prepared: Awaited<ReturnType<typeof prepareData>>) {
    return {
        points: prepared.points,
        links: prepared.links,
        ...prepared.cosmographConfig,
        ...buildNonDataConfig(),
    };
}

// true only for the very first simulation end — we auto-fit once, then leave zoom to the user
let initialFitDone = false;

// Called from buildConfig so Cosmograph fires it when the layout stabilises.
// setConfig is called on every filter/scheme change so the flag prevents re-fitting on those.
function onSimulationEnd() {
    if (initialFitDone) return;
    initialFitDone = true;
    fitToNodes(400);
}

// fitView zooms to the full simulation space (very large). fitViewByIndices zooms to the
// actual bounding box of the rendered nodes, which is what we want.
function fitToNodes(duration = 500) {
    const indices = Array.from({ length: renderedNodes.value.length }, (_, i) => i);
    cosmographInstance.value?.fitViewByIndices(indices, duration, 0.1);
}

// — Update the graph when filters change (resets selection) —
async function updateGraph() {
    if (!cosmographInstance.value) return;
    selectedNode.value = null;
    selectedEdge.value = null;
    clearHighlight();
    const { nodes, edges } = filterData();
    const prepared = await prepareData(nodes, edges);
    cosmographInstance.value.setConfig(buildConfig(prepared));
}

// — Recolour only: reuse stored prepared data so layout is not re-run —
function updateColors() {
    if (!cosmographInstance.value || !storedPrepared) return;
    buildModColors(renderedNodes.value);
    const zoom = cosmographInstance.value.getZoomLevel();
    cosmographInstance.value.setConfig(buildConfig(storedPrepared));
    requestAnimationFrame(() => {
        if (zoom !== undefined) cosmographInstance.value?.setZoomLevel(zoom, 0);
        if (selectedNode.value) {
            const idx = renderedNodes.value.findIndex(
                (n) => n.composite_name === selectedNode.value!.composite_name,
            );
            if (idx !== -1) highlightNode(idx);
        } else if (selectedEdge.value) {
            highlightEdgeEndpoints(selectedEdge.value);
        }
    });
}

// — Display helpers —

/** Adds spacing around "|" separators, e.g. "Q53SF7|356|S|21" -> "Q53SF7 | 356 | S | 21". */
function formatPipedLabel(value: string): string {
    return value.replace(/\|/g, " | ");
}

/** Compact count display, e.g. 1424588 -> "1.4M", 50563 -> "50.6K", 170 -> "170". */
function formatCount(n: number): string {
    if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
    if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
    return n.toLocaleString();
}

/** Human-readable label for a node, respecting the current protein filter field. */
function nodeDisplayLabel(node: ApiNode): string {
    return proteinFilterField.value === "gene_name"
        ? node.composite_gene_name
        : node.composite_name;
}

/**
 * Protein/gene identifier line for the info panel.
 * Gene mode: "EGFR (P12345)"  |  Accession mode: "P12345"
 */
function nodeProteinDisplay(node: ApiNode): string {
    if (proteinFilterField.value === "gene_name" && node.gene_name) {
        return `${node.gene_name} (${node.accession})`;
    }
    return node.accession;
}

/** Resolve a composite_name to its display label (used for edge endpoints). */
function edgeEndpointLabel(compositeName: string): string {
    const node = renderedNodes.value.find((n) => n.composite_name === compositeName);
    return node ? nodeDisplayLabel(node) : compositeName;
}

/** Split a label like "Q53SF7|356|S|21" into its pipe-separated parts. */
function splitLabel(label: string): string[] {
    return label.split("|");
}

// — Actions —
const resetFilters = () => {
    scoreRange.value = [0.6, 1];
    selectedProteins.value = [];
    selectedMods.value = [];
};

const resetZoom = () => fitToNodes(500);

const EDGE_CSV_COLUMNS = [
    "node_a",
    "node_b",
    "score",
    "qvalue",
    "same_protein",
    "same_site",
    "position_gap",
    "same_mod",
    "shared_peptide",
] as const;

function edgesToCsv(edges: ApiEdge[]): string {
    const escape = (value: unknown): string => {
        if (value === null || value === undefined) return "";
        const s = String(value);
        return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
    };
    const rows = edges.map((e) => EDGE_CSV_COLUMNS.map((col) => escape(e[col])).join(","));
    return [EDGE_CSV_COLUMNS.join(","), ...rows].join("\n");
}

/** Downloads the currently displayed connected edges for the selected node as CSV. */
const downloadConnectedEdges = () => {
    if (!selectedNode.value || connectedEdges.value.length === 0) return;
    const csv = edgesToCsv(connectedEdges.value);
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${selectedNode.value.composite_name.replace(/\|/g, "_")}_edges.csv`;
    link.click();
    URL.revokeObjectURL(url);
};

/**
 * Cosmograph renders labels as CSS DOM elements (via @interacta/css-labels), not on the
 * WebGL canvas. captureScreenshot() only exports the canvas, so labels are missing.
 * This function composites both layers manually.
 *
 * Canvas selection: cosmos.gl creates multiple canvas elements and Cosmograph's own
 * captureScreenshot uses `_cosmosElement.querySelector("canvas")`. We mirror that
 * exactly via the internal property to avoid picking the wrong canvas from the outer
 * container. A requestAnimationFrame pause ensures the GPU has flushed the current
 * frame before toDataURL reads the drawing buffer.
 */
const downloadImage = async () => {
    if (!container.value || !cosmographInstance.value) return;

    // Wait for the current animation frame to finish so the drawing buffer is populated.
    await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));

    // Mirror Cosmograph.captureScreenshot: use _cosmosElement.querySelector("canvas")
    // rather than container.value.querySelector("canvas") — cosmos.gl may have multiple
    // canvases in the outer container and only the one inside _cosmosElement is the
    // WebGL rendering target.
    const instance = cosmographInstance.value as unknown as { _cosmosElement: HTMLElement };
    const glCanvas = instance._cosmosElement?.querySelector<HTMLCanvasElement>("canvas");
    if (!glCanvas) return;

    const canvasRect = glCanvas.getBoundingClientRect();
    const scaleX = glCanvas.width / canvasRect.width;
    const scaleY = glCanvas.height / canvasRect.height;

    const output = document.createElement("canvas");
    output.width = glCanvas.width;
    output.height = glCanvas.height;
    const ctx = output.getContext("2d");
    if (!ctx) return;

    // 1. WebGL content — toDataURL on the same canvas Cosmograph uses internally.
    const networkDataUrl = glCanvas.toDataURL("image/png");
    await new Promise<void>((resolve) => {
        const img = new Image();
        img.onload = () => {
            ctx.drawImage(img, 0, 0);
            resolve();
        };
        img.onerror = () => resolve();
        img.src = networkDataUrl;
    });

    // 2. CSS label overlay — query all label divs that are not fully hidden
    const labelEls = container.value.querySelectorAll<HTMLElement>(
        ".css-label--label:not(.css-label--hidden)",
    );

    labelEls.forEach((el) => {
        const r = el.getBoundingClientRect();
        if (r.width === 0 || r.height === 0) return;

        // Clip labels that fall entirely outside the canvas area
        if (
            r.right < canvasRect.left ||
            r.left > canvasRect.right ||
            r.bottom < canvasRect.top ||
            r.top > canvasRect.bottom
        )
            return;

        const x = (r.left - canvasRect.left) * scaleX;
        const y = (r.top - canvasRect.top) * scaleY;
        const w = r.width * scaleX;
        const h = r.height * scaleY;

        const cs = window.getComputedStyle(el);
        const opacity = parseFloat(cs.opacity);

        ctx.save();
        ctx.globalAlpha = Number.isFinite(opacity) ? opacity : 1;

        // Background with rounded corners (CSS specifies border-radius: 6px)
        ctx.fillStyle = cs.backgroundColor;
        ctx.beginPath();
        if (typeof ctx.roundRect === "function") {
            ctx.roundRect(x, y, w, h, 6 * Math.min(scaleX, scaleY));
        } else {
            ctx.rect(x, y, w, h);
        }
        ctx.fill();

        // Label text
        const fontSize = parseFloat(cs.fontSize) * scaleY;
        ctx.font = `${cs.fontWeight} ${fontSize}px ${cs.fontFamily}`;
        ctx.fillStyle = cs.color;
        ctx.textBaseline = "top";
        const padL = parseFloat(cs.paddingLeft) * scaleX;
        const padT = parseFloat(cs.paddingTop) * scaleY;
        ctx.fillText(el.textContent?.trim() ?? "", x + padL, y + padT, w - padL * 2);

        ctx.restore();
    });

    const link = document.createElement("a");
    link.download = "network";
    link.href = output.toDataURL("image/png");
    link.click();
};

// — Layout height (viewport-fitted) —
// We measure from div.right-panel itself rather than from the outer wrapper.
// This sidesteps the v-row margin:-12px / v-col padding:12px gutter arithmetic
// (overflow:hidden on an ancestor clips the negative-margin compensation and
// shifts the content 12 px downward, causing an immediate spurious scrollbar).
const rightPanelRef = ref<HTMLDivElement | null>(null);
const panelHeight = ref("calc(100dvh - 79px)");

function updatePanelHeight() {
    if (!rightPanelRef.value) return;
    const top = rightPanelRef.value.getBoundingClientRect().top;
    // Use window.innerHeight (exact pixels) not 100vh (may include scrollbar width on Windows).
    // Subtract 12 px for the v-col bottom padding that Vuetify adds but does not account
    // for in the gutter layout — without this the row overflows by exactly one gutter unit.
    panelHeight.value = `${Math.floor(window.innerHeight - top) - 12}px`;
}

// — Crash recovery —
// Some browser extensions (dark mode filters, ad blockers, translators) rewrite the DOM
// out from under Cosmograph's own DOM/canvas manipulation, which throws an uncaught
// "insertBefore"/"removeChild" DOMException outside any of our try/catch blocks. We can't
// fix the extension, so we detect the crash globally and remount the instance instead.
const RENDER_CRASH_PATTERN = /insertBefore|removeChild/;
const MAX_RENDER_RETRIES = 2;
let renderRetryCount = 0;
const showRenderError = ref(false);
const renderRetriesExhausted = ref(false);
const renderErrorMessage = computed(() =>
    renderRetriesExhausted.value
        ? "Graph rendering keeps failing. This is usually caused by a browser extension that modifies the page (dark mode filter, ad blocker, translator, ...). Try disabling such extensions for this site, or reload in a private window."
        : "Graph rendering was interrupted, likely by a browser extension that modifies the page (dark mode filter, ad blocker, translator, ...). Attempting to recover automatically…",
);

function createInstance(prepared: Awaited<ReturnType<typeof prepareData>>) {
    if (!container.value) return;
    cosmographInstance.value = new Cosmograph(container.value, buildConfig(prepared));
    initialFitDone = false;
    // Give the simulation ~1 s to place nodes, then zoom in. onSimulationEnd will
    // do a final fit once the layout fully stabilises.
    setTimeout(() => fitToNodes(400), 1000);
}

function fetchEdges(minScore: number): Promise<ApiEdge[]> {
    return fetchJson<ApiEdge[]>(`get-edges?min_score=${minScore}`);
}

function fetchEdgeCount(minScore: number, maxScore: number): Promise<number> {
    return fetchJson<number>(`get-edges-count?min_score=${minScore}&max_score=${maxScore}`);
}

async function loadAndInitGraph() {
    const [nodes, edges, unimod] = await Promise.all([
        fetchJson<ApiNode[]>("get-nodes"),
        fetchEdges(scoreRange.value[0]),
        fetchJson<UnimodEntry[]>("get-unimod"),
    ]);

    allNodes.value = nodes;
    allEdges.value = edges;
    unimodEntries.value = unimod;

    const prepared = await prepareData(nodes, edges);
    createInstance(prepared);
}

function handleRenderCrash() {
    showRenderError.value = true;

    if (renderRetryCount >= MAX_RENDER_RETRIES) {
        renderRetriesExhausted.value = true;
        return;
    }
    renderRetryCount++;

    cosmographInstance.value?.destroy();
    cosmographInstance.value = null;
    // Reuse the last prepared dataset if we have one — avoids redundant refetching and
    // reproduces the graph as it was right before the crash.
    setTimeout(() => {
        if (storedPrepared) createInstance(storedPrepared);
        else void loadAndInitGraph();
    }, 150);
}

function handleWindowError(event: ErrorEvent) {
    if (!RENDER_CRASH_PATTERN.test(event.message ?? "")) return;
    event.preventDefault();
    handleRenderCrash();
}

// Cosmograph catches this exact crash internally (inside its own _rebuildGraph) and only
// console.logs it — it never becomes an uncaught error/rejection, so window.onerror never
// fires. It does surface as a "🚨 ..." message it renders into its own container, though,
// so we watch for that instead of relying on a global error listener for this specific case.
let renderCrashObserver: MutationObserver | null = null;

function watchCosmographMessageElement() {
    if (!container.value) return;
    renderCrashObserver = new MutationObserver(() => {
        if (RENDER_CRASH_PATTERN.test(container.value?.textContent ?? "")) handleRenderCrash();
    });
    renderCrashObserver.observe(container.value, {
        childList: true,
        subtree: true,
        characterData: true,
    });
}

// — Lifecycle —
onMounted(async () => {
    if (!container.value) return;

    window.addEventListener("error", handleWindowError);
    watchCosmographMessageElement();

    // Measure available height before data loading so the layout is stable.
    // nextTick ensures DOM is rendered, but the navbar logo (height: 80px) may not yet be
    // loaded — the image loads asynchronously and shifts the toolbar to its final height
    // only after the load event. We re-measure once after all resources finish loading so
    // that the initial measurement (taken at compact toolbar height ~48 px) is corrected.
    await nextTick();
    updatePanelHeight();
    if (document.readyState !== "complete") {
        window.addEventListener("load", updatePanelHeight, { once: true });
    }
    window.addEventListener("resize", updatePanelHeight);

    await loadAndInitGraph();
});

onBeforeUnmount(() => {
    window.removeEventListener("resize", updatePanelHeight);
    window.removeEventListener("error", handleWindowError);
    renderCrashObserver?.disconnect();
    clearTimeout(scoreFetchTimer);
    clearTimeout(countFetchTimer);
    cosmographInstance.value?.destroy();
    cosmographInstance.value = null;
});

watch(proteinFilterField, () => {
    selectedProteins.value = [];
});
watch([scoreRange, selectedProteins, selectedMods, proteinFilterField], updateGraph, {
    deep: true,
});
watch(colorScheme, updateColors);

// The backend only ever returns edges with score >= min_score, so lowering the slider's
// minimum needs a fresh fetch, not just client-side filtering of what's already loaded.
// Debounced so dragging the handle doesn't fire a request per pixel.
let scoreFetchTimer: ReturnType<typeof setTimeout> | undefined;
watch(
    () => scoreRange.value[0],
    (min) => {
        clearTimeout(scoreFetchTimer);
        scoreFetchTimer = setTimeout(async () => {
            allEdges.value = await fetchEdges(min);
            await updateGraph();
        }, 300);
    },
);

// Lightweight live count for the current range, independent of the (heavier, debounced above)
// actual edge fetch — cheap enough to update on every drag tick without waiting for it to settle.
let countFetchTimer: ReturnType<typeof setTimeout> | undefined;
watch(
    scoreRange,
    ([a, b]) => {
        clearTimeout(countFetchTimer);
        countFetchTimer = setTimeout(async () => {
            edgeCount.value = await fetchEdgeCount(Math.min(a, b), Math.max(a, b));
        }, 150);
    },
    { deep: true, immediate: true },
);
</script>

<template lang="pug">
v-row()
    v-col(cols="10" md="9")
        v-alert(
            v-if="showRenderError"
            type="warning"
            variant="tonal"
            density="compact"
            closable
            class="mb-2"
            @click:close="showRenderError = false"
        )
            | {{ renderErrorMessage }}
        div(ref="container" class="cosmograph-container")
    v-col(cols="2" md="3")
        div.right-panel(ref="rightPanelRef" style="padding: 16px; border-radius: 8px;")
            div()
                .d-flex.align-center.justify-space-between
                    .d-flex.align-center.ga-1
                        h4 Score
                        v-tooltip(text="Signed Distance Correlation" location="top")
                            template(v-slot:activator="{ props }")
                                v-icon(
                                    v-bind="props"
                                    icon="mdi-information-outline"
                                    size="14"
                                    class="text-medium-emphasis"
                                )
                    span.text-caption.text-medium-emphasis(v-if="edgeCount !== null") ~{{ formatCount(edgeCount) }} edges
                v-range-slider(
                    v-model="scoreRange"
                    :step="0.1"
                    :max="1"
                    :min="DATA_MIN_SCORE"
                    class="alingn-center"
                    hide-details

                )
                    template(v-slot:prepend)
                        v-text-field(
                            v-model="scoreRange[0]"
                            density="compact"
                            style="width: 70px; margin-right: 10px"
                            type="number"
                            step="0.1"
                            variant="outlined"
                            hide-details
                            single-line
                        )
                    template(v-slot:append)
                        v-text-field(
                            v-model="scoreRange[1]"
                            density="compact"
                            style="width: 70px; margin-left: 10px"
                            type="number"
                            step="0.1"
                            variant="outlined"
                            hide-details
                            single-line
                        )
            div(style="margin-top: 20px;")
                .d-flex.align-center.justify-space-between.mb-1
                    h4.mb-0 {{ proteinFilterField === 'accession' ? 'Accession' : 'Gene' }}
                    v-btn-toggle(
                        v-model="proteinFilterField"
                        mandatory
                        density="compact"
                        color="primary"
                        variant="outlined"
                        style="margin-bottom: 10px;"
                    )
                        v-btn(value="accession" size="small") Accession
                        v-btn(value="gene_name" size="small") Gene
                v-autocomplete(
                    clearable
                    closable-chips
                    multiple
                    chips
                    v-model="selectedProteins"
                    :items="proteinOptions"
                )
            div
                h4 Modification
                v-autocomplete(
                    clearable
                    closable-chips
                    multiple
                    chips
                    v-model="selectedMods"
                    :items="modificationOptions"
                    item-title="title"
                    item-value="value"
                )

            v-divider.my-3(style="padding-bottom: 10px;")

            div(style="padding-bottom: 10px;")
                h4(style="margin-bottom: 5px;") Colour by
                v-btn-toggle(
                    v-model="colorScheme"
                    mandatory
                    density="compact"
                    color="primary"
                    variant="outlined"
                    class="mb-3"
                    style="margin-bottom: 10px;"
                )
                    v-btn(value="degree" size="small") Degree
                    v-btn(value="modification" size="small") Modification

                div(v-if="colorScheme === 'degree'")
                    .legend-gradient
                    .d-flex.justify-space-between.text-caption.mt-1
                        span {{ degreeRange.min }} edge{{ degreeRange.min === 1 ? '' : 's' }}
                        span {{ degreeRange.max }} edges

                div(v-else)
                    div.d-flex.align-center.ga-2.mb-1(
                        v-for="item in modLegendItems"
                        :key="item.name"
                    )
                        div.legend-dot(:style="{ background: item.color }")
                        span.text-caption {{ item.name }}

            v-divider.my-3()

            v-row.mt-5(style="padding-top: 20px; padding-bottom: 20px;")
                v-col(cols="12" md="6")
                    v-btn.action-btn(block @click="resetFilters") Reset filters
                v-col(cols="12" md="6")
                    v-btn.action-btn(block @click="resetZoom") Reset zoom
                v-col(cols="12")
                    v-btn.action-btn(block @click="downloadImage") Download image

            v-divider.my-3(v-if="selectedNode || selectedEdge")

            div(v-if="selectedNode")
                h4(class="selected-node-title") Selected node
                table.node-info-table
                    tbody
                        tr
                            td.info-label Name
                            td.info-value {{ formatPipedLabel(nodeDisplayLabel(selectedNode)) }}
                        tr
                            td.info-label {{ proteinFilterField === 'gene_name' ? 'Gene' : 'Protein' }}
                            td.info-value {{ nodeProteinDisplay(selectedNode) }}
                        tr
                            td.info-label Position
                            td.info-value {{ selectedNode.position }}
                        tr
                            td.info-label Residue
                            td.info-value {{ selectedNode.residue }}
                        tr
                            td.info-label Modification
                            td.info-value {{ selectedNodeModDisplay }}
                        tr
                            td.info-label Connected edges
                            td.info-value {{ connectedEdges.length }}
                div(v-if="connectedEdges.length")
                    v-btn.action-btn.mt-2(block size="small" variant="outlined" @click="downloadConnectedEdges")
                        v-icon(icon="mdi-download" size="16" class="mr-1")
                        | Download data
                    div(v-if="histogramBins" style="padding: 10px 0;")
                        p.text-caption.text-medium-emphasis.mb-1 Edge score distribution
                        div(ref="histogramRef")

                    div.edge-row(v-for="edge in connectedEdges" :key="edge.node_a + edge.node_b")
                        span.text-caption.edge-node
                            template(v-for="(part, i) in splitLabel(edgeEndpointLabel(edge.node_a))" :key="i")
                                span.lsep(v-if="i > 0") |
                                span(:class="`lpart-${i}`") {{ part }}
                        span.edge-score.text-caption {{ edge.score.toFixed(3) }}
                        span.text-caption.edge-node
                            template(v-for="(part, i) in splitLabel(edgeEndpointLabel(edge.node_b))" :key="i")
                                span.lsep(v-if="i > 0") |
                                span(:class="`lpart-${i}`") {{ part }}

            div(v-if="selectedEdge")
                h5 Selected edge
                p.text-body-2 Source: {{ edgeEndpointLabel(selectedEdge.node_a) }}
                p.text-body-2 Target: {{ edgeEndpointLabel(selectedEdge.node_b) }}
                p.text-body-2 Score: {{ selectedEdge.score }}
</template>

<style lang="scss" scoped>
.cosmograph-container {
    width: 100%;
    height: v-bind(panelHeight);
    border-radius: 8px;
}

.right-panel {
    height: v-bind(panelHeight);
    background-color: rgb(var(--v-theme-surface));
    overflow-y: auto;
    overflow-x: hidden;
    padding-right: 6px;

    // Thin styled scrollbar (Webkit/Blink)
    &::-webkit-scrollbar {
        width: 4px;
    }
    &::-webkit-scrollbar-track {
        background: transparent;
    }
    &::-webkit-scrollbar-thumb {
        background: rgba(var(--v-theme-on-surface), 0.2);
        border-radius: 2px;
    }
}

.action-btn {
    white-space: normal;
    height: auto !important;
    min-height: 36px;
}

:deep(.action-btn .v-btn__content) {
    text-wrap: auto !important;
}

.legend-gradient {
    height: 14px;
    border-radius: 3px;
    background: linear-gradient(to right, #c6dbef, #08306b);
}

.legend-dot {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    flex-shrink: 0;
}
.selected-node-title {
    color: rgb(var(--v-theme-primary));
    font-weight: 800;
    margin-bottom: 5px;
    margin-top: 10px;
}
.node-info-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.8125rem;

    tr:nth-child(odd) {
        background-color: rgba(var(--v-theme-on-surface), 0.04);
    }
}
.info-label {
    padding: 4px 8px 4px 4px;
    font-family: "Courier New", monospace;
    font-weight: 600;
    color: rgba(var(--v-theme-on-surface), 0.7);
    white-space: nowrap;
    vertical-align: top;
    width: 1%;
}
.info-value {
    padding: 4px 4px 4px 8px;
    color: rgb(var(--v-theme-on-surface));
    word-break: break-word;
}
.edge-row {
    display: grid;
    grid-template-columns: 1fr auto 1fr;
    align-items: center;
    gap: 4px;
    padding: 2px 0;
}
.edge-node {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
.edge-node:last-child {
    text-align: right;
}
.edge-score {
    color: #888;
    white-space: nowrap;
    text-align: center;
}

.lsep {
    color: #999;
    margin: 0 1px;
}
.lpart-0 {
    color: inherit;
}
.lpart-1 {
    color: #2196f3;
}
.lpart-2 {
    color: #ff7043;
}
.lpart-3 {
    color: #7c4dff;
}
</style>

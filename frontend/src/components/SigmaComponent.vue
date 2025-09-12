<script setup>
import { useTemplateRef, ref, watch, watchEffect, onMounted, onBeforeMount } from 'vue'
import Graph from "graphology";
import Sigma from "sigma";
import forceAtlas2 from "graphology-layout-forceatlas2";
import circular from "graphology-layout/circular";
import ForceSupervisor from "graphology-layout-force/worker";
import noverlap from 'graphology-layout-noverlap';

const baseApiUrl = 'http://localhost:5600/api/v1/'

const dataEdges = ref(null)
const dataNodes = ref(null)
const renderer = ref(null)
const score = ref(null)
const pval = ref(null)
const modifications = ref([])
const modificationsVmodel = ref([])
const state = {
    hoveredNode: null,
    searchQuery: null,
    selectedNode: null,
    hoveredNeighbors: null
}

const graph = new Graph();

watch(
    () => dataNodes.value,
    () => {
        setModifications()
        addDataToGraph()
        console.log('data changed')
        setGraph()
    }
)
watch(
    () => modificationsVmodel.value,
    () => {
        console.log('modifications v model changed')
        graph.forEachNode((node, {modification}) => {
            console.log('node',node)
            console.log(modification)
            // if(modificationsVmodel.value.includes(modification)) {
            graph.setNodeAttribute(node, 'hidden', !modificationsVmodel.value.includes(modification))
            // }
        })
        renderer.value.refresh({
            // We don't touch the graph data so we can skip its reindexation
            skipIndexation: true,
        });
    }
)
const setGraph = () => {
    const containerHtml = document.getElementById("sigma-network")
    let hoveredEdge = null
    console.log(containerHtml)
    circular.assign(graph);
    const settings = forceAtlas2.inferSettings(graph)
    forceAtlas2.assign(graph, { settings, iterations: 600 });

    const loader = document.getElementById("loader")
    loader.style.display = "none"
    
    renderer.value = new Sigma(
        graph,
        containerHtml, 
        {
            enableEdgeEvents: true,
            zIndex: true
        }
    );
    
    // Bind graph interactions:
    renderer.value.on("enterNode", ({ node }) => {
        console.log('enterNode')
        setHoveredNode(node);
    });
    renderer.value.on("leaveNode", () => {
        setHoveredNode(undefined);
    });

    renderer.value.on("enterEdge", ({ edge }) => {
        console.log('enterEdge',)
        hoveredEdge = edge;
        renderer.value.refresh();
    });
    renderer.value.on("leaveEdge", ({ edge }) => {
        hoveredEdge = null;
        renderer.value.refresh();
    });
    renderer.value.setSetting('nodeReducer', (node, data) => {
        const res = {...data}
        if(state.hoveredNeighbors && !state.hoveredNeighbors.has(node) && state.hoveredNode !== node){
            res.label = ''
            res.color = '#f6f6f6'
            res.zIndex = 0
        }

        if(state.selectedNode === node) {
            res.highlighted = true
        } 
        // else if(state.suggestions) {
        // }
        return res
    })
    renderer.value.setSetting('edgeReducer', (edge, data) => {
        const res = {...data}
        if(state.hoveredNode && !graph.extremities(edge).every((n) => n === state.hoveredNode || graph.areNeighbors(n, state.hoveredNode))) {
            res.hidden =true
        }
        // if (state.suggestions && (!state.suggestions.has(graph.source(edge)) || !state.suggestions.has(graph.target(edge)))) {
        //     res.hidden = true;
        // }
        else if (graph.hasExtremity(edge, state.hoveredNode)) {
            res.color = "#990000"
            res.size = 4
            res.zIndex = 1
        }
        if (edge === hoveredEdge) {
            // console.log(edge)
            res.color = "#990000"
            res.size = 4
        }

        return res;
    })

}
const getMouseLayer = () => {
  return document.querySelector(".sigma-mouse");
}
const setHoveredNode = (node) => {
    if (node) {
      state.hoveredNode = node;
      state.hoveredNeighbors = new Set(graph.neighbors(node));
    }

    if (!node) {
      state.hoveredNode = undefined;
      state.hoveredNeighbors = undefined;
    }

    // Refresh rendering
    renderer.value.refresh({
      // We don't touch the graph data so we can skip its reindexation
      skipIndexation: true,
    });
}
onBeforeMount(async () => {
  console.log('onBeforeMount')
  await getDataEdges()
})
onMounted(() => {
    console.log('onMounted')

})
const addDataToGraph = () => {
    dataNodes.value.forEach((line, index) => {
        if(index > 0) {
            graph.addNode(line[0], {size: 10, label: line[0], modification: line[4]})
        }
    });

    dataEdges.value.forEach((line, index) => {
        if(index > 0) {
            graph.addEdge(line[0], line[1], {type: 'line', label: line[2], color: '#cccccc', weight: 1})
        }
    })
    // graph.nodes().forEach((node, i) => {
    //     const angle = (i * 2 * Math.PI) / graph.order;
    //     graph.setNodeAttribute(node, "x", 100 * Math.cos(angle))
    //     graph.setNodeAttribute(node, "y", 100 * Math.sin(angle))
    // });
    const degrees = graph.nodes().map((node) => graph.degree(node))
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
        )
    })
    graph.forEachNode((node, attributes) =>{
        let color = node.includes('ORF') ? '#ff3433' : '#04cccc'
        graph.setNodeAttribute(node, "color", color)
    });

}
const getDataEdges = async () => {
  console.log('getdata')
  const url = baseApiUrl + 'get-data-edges'
  try {
      const response = await fetch(url)
      if(!response.ok) {
          throw new Error(`Response status: ${response.status}`)
      }
      const res_json = await response.json()
      dataEdges.value = res_json[0]
      dataNodes.value = res_json[1]
      console.log('dataEdges', dataEdges.value)
  } catch (error) {
      console.log(error.message)
  }
}
const setModifications = () => {
    console.log('setModifications')
    dataNodes.value.forEach( row => {
        if(!modifications.value.includes(row[4])){
            modifications.value.push(row[4])
        }
    })
    modifications.value.sort()
    console.log(modifications.value)
}
const getDataNodes = async () => {
  console.log('getdatanodes')
  const url = baseApiUrl + 'get-data-nodes'
  try {
      const response = await fetch(url)
      // console.log(response)
      if(!response.ok) {
          throw new Error(`Response status: ${response.status}`)
      }
      const res_json = await response.json()
      dataNodes.value = res_json
      console.log('data', dataNodes.value)
  } catch (error) {
      console.log(error.message)
  }
}
const toggleModifications = () => {
    console.log('modifications vmodel', modificationsVmodel.value)
}

</script>

<template lang="pug">
v-row
    .v-col-10
        div(id="loader")
            v-progress-circular(model-value="20")
        div(id="sigma-network")
    //- div(ref="container")
    .v-col-2
        div
            v-slider(
                v-model="score"
                label="score"
            )
            v-slider(
                v-model="pval"
                label="pval"
            )
        v-expansion-panels
            v-expansion-panel
                v-expansion-panel-title(collapse-icon="mdi-minus" expand-icon="mdi-plus")
                    | Modifications
                v-expansion-panel-text
                    v-list
                        v-list-item(v-for="item in modifications" :key="item")
                            v-checkbox(
                                v-model="modificationsVmodel"
                                :value="item"
                            )
                                template(
                                    v-slot:label
                                )
                                    | {{ item }}
                    
        | {{ modificationsVmodel }}

                    
                        


    
</template>

<style lang="scss" scoped>
#sigma-network {
  width: 100%;
  height: 1000px;
}

</style>


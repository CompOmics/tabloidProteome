<script setup>
import { useTemplateRef, ref, reactive, watch, watchEffect, onMounted, onBeforeMount } from 'vue'
import Graph from "graphology";
import Sigma from "sigma";
import forceAtlas2 from "graphology-layout-forceatlas2";
import circular from "graphology-layout/circular";
import ForceSupervisor from "graphology-layout-force/worker";
import noverlap from 'graphology-layout-noverlap';

const baseApiUrl = 'http://localhost:5600/api/v1/'

const dataEdges = ref(null)
const dataNodes = ref(null)
const dataUnimod = ref(null)
const renderer = ref(null)
const score = ref([0.6, 1])
const modifications = ref([])
const positions = ref([])
const residues = ref([])
const proteins = ref([])
const modificationsVmodel = ref([])
const positionsVmodel = ref([])
const residuesVmodel = ref([])
const proteinNameModel = ref([])
const pval = ref(null)
const hoveredEdge = ref(null)
const state = reactive({
    hoveredNode: null,
    hoveredNeighbors: null,
    selectedNode: null
})
// const filterState = reactive({
//     modifications: [],
//     score: null,
//     pval: null,
//     protein: []
// })
const filterState = reactive({
    modifications: modificationsVmodel,
    proteins: proteinNameModel,
    pval: pval, 
    score: score
})
const graph = new Graph()

watch(filterState, 
    (newValue, oldValue) => {
        console.log('filterState changed')
        console.log('newVAl', newValue)
        console.log('oldVAl', oldValue)
        const {modifications, proteins, pval, score} = filterState
        console.log('modifications', modifications)
        console.log('prots', proteins)
        console.log('score', score)
        console.log('score old', oldValue.score)
        if(modifications.length > 0 || proteins.length > 0) {
            if(modifications.length > 0 && proteins.length == 0) {
                console.log('*')
                graph.forEachNode((node, {modification, protein}) => {
                    graph.setNodeAttribute(node, 'hidden', !modifications.includes(modification))
                })
            } else if (modifications.length > 0 && proteins.length > 0) {
                console.log('**')
                graph.forEachNode((node, {modification, protein}) => {
                    graph.setNodeAttribute(node, 'hidden', !modifications.includes(modification) || !proteins.includes(protein))
                })
            } else if(modifications.length == 0 && proteins.length > 0) {
                console.log('***')
                graph.forEachNode((node, {modification, protein}) => {
                    graph.setNodeAttribute(node, 'hidden', !proteins.includes(protein))
                })
            }
        } else {
            resetGraph()
        }
        if(pval !== null && pval != oldValue.pval.value) {
            updateGraphByPval()
        }
        if(score != oldValue.score.value) {
            updateGraphByScore(score)
        }
    }
)

watch(
    state,
    (newValue, oldValue) => {
    console.log('state changed')
    console.log(newValue)
    console.log(state.hoveredNode)
    if(state.hoveredNode !== undefined) {
        console.log('hoveredNode', state.hoveredNode)
        renderer.value.setSetting('nodeReducer', (node, data) => {
            const res = {...data}
            if(state.hoveredNeighbors && !state.hoveredNeighbors.has(node) && state.hoveredNode !== node){
                res.label = ''
                res.color = '#f6f6f6'
                res.zIndex = 0
            }
            if(state.selectedNode === node) {
                console.log('selected')
                res.highlighted = true
            } 
            return res
        })
        renderer.value.setSetting('edgeReducer', (edge, data) => {
            // console.log(edge)
            const res = {...data}
            if(state.hoveredNode && !graph.extremities(edge).every((n) => n === state.hoveredNode || graph.areNeighbors(n, state.hoveredNode))) {
                res.hidden =true
            } else if (graph.hasExtremity(edge, state.hoveredNode)) {
                console.log('set edges to color')
                res.color = "#990000"
                res.size = 4
                res.zIndex = 1
            }
            return res
        })
        renderer.value.refresh({
            // We don't touch the graph data so we can skip its reindexation
            skipIndexation: true,
        });
    }
})
watch(
    () => hoveredEdge.value,
    () => {
        console.log('hoveredEdge changed')
        renderer.value.setSetting('edgeReducer', (edge, data) => {
            const res = {...data}

            if (edge == hoveredEdge.value) {
                console.log('hoveredEdge')
                res.color = "#054cb7"
                res.size = 4
                res.label = data.score + ', ' + data.pval
            }
            return res;
        })
        renderer.value.refresh({
            // We don't touch the graph data so we can skip its reindexation
            skipIndexation: true,
        });
    }
)
watch(
    () => dataNodes.value,
    () => {
        setModifications()
        // setPositions()
        // setResidues()
        setFiltersAttributes()
        addDataToGraph()
        console.log('data changed')
        setGraph()
    }
)

const updateGraphByFilters = () => {

    console.log('modsVmodel', modificationsVmodel.value)
    console.log('proteinNameModel.value', proteinNameModel.value)
    // console.log('filterType', filterType)
    updateGraphByModification()
    updateGraphByProteinName()
    // console.log(filterState[filterType])
    // if(modificationsVmodel.value.length > 0 && proteinNameModel.value.length == 0) {
    //     graph.forEachNode((node, {modification}) => {
    //         console.log(graph)
    //         let nodeAttributes = graph.getNodeAttributes(node)
    //         console.log(nodeAttributes)
    //         //console.log(!modificationsVmodel.value[modification], !proteinNameModel.value[protein])
            
    //         //console.log(!modificationsVmodel.value[modification] || !proteinNameModel.value[protein])
    //         graph.setNodeAttribute(node, 'hidden', !modificationsVmodel.value.includes(modification))
    //         let nodeHidden = graph.getNodeAttribute(node, 'hidden')
    //         console.log('hidden', nodeHidden)
    //     })
    // } else if(modificationsVmodel.value.length > 0  && proteinNameModel.value.length > 0) {
    //     graph.forEachNode((node, {modification, protein}) => {
    //         //console.log(!modificationsVmodel.value[modification], !proteinNameModel.value[protein])
            
    //         //console.log(!modificationsVmodel.value[modification] || !proteinNameModel.value[protein])
    //         graph.setNodeAttribute(node, 'hidden', 
    //             (!modificationsVmodel.value.includes(modification) || !proteinNameModel.value.includes(protein))
    //         )
    //     })
    // }
    // else {
    //     resetGraph()
    // }
    // graph.forEachNode((node, {modification, protein}) => {
    //     console.log(!modificationsVmodel.value[modification], !proteinNameModel.value[protein])
        
    //     console.log(!modificationsVmodel.value[modification] || !proteinNameModel.value[protein])
    //     graph.setNodeAttribute(node, 'hidden', 
    //         (!modificationsVmodel.value[modification] || !proteinNameModel.value[protein])
    //     )
    // })
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
const setGraph = () => {
    const containerHtml = document.getElementById("sigma-network")
    circular.assign(graph);
    const settings = forceAtlas2.inferSettings(graph)
    forceAtlas2.assign(graph, { settings, iterations: 600 })

    const loader = document.getElementById("loader")
    loader.style.display = "none"
    
    renderer.value = new Sigma(
        graph,
        containerHtml, 
        {
            enableEdgeEvents: true,
            renderEdgeLabels: true,
            zIndex: true
        }
    );
    // Bind graph interactions:
    renderer.value.on("enterNode", ({ node }) => {
        console.log('enterNode')
        setHoveredNode(node);
    });
    renderer.value.on("leaveNode", () => {
        setHoveredNode(undefined)
    })
    renderer.value.on("clickNode", ({node}) => {
        console.log('clickNode')
    })

    renderer.value.on("enterEdge", ({ edge }) => {
        console.log('enterEdge',)
        hoveredEdge.value = edge
        renderer.value.refresh()
    });
    renderer.value.on("leaveEdge", ({ edge }) => {
        hoveredEdge.value = null
        renderer.value.refresh()
    });
    renderer.value.setSetting('nodeReducer', (node, data) => {
        const res = {...data}
        //if(state.value.hoveredNeighbors && !state.value.hoveredNeighbors.has(node) && state.value.hoveredNode !== node){
        if(state.hoveredNeighbors && !state.hoveredNeighbors.has(node) && state.hoveredNode !== node){
            res.label = ''
            res.color = '#f6f6f6'
            res.zIndex = 0
        }
        if(state.selectedNode === node) {
            console.log('selected')
            res.highlighted = true
        } 
        return res
    })
    renderer.value.setSetting('edgeReducer', (edge, data) => {
        const res = {...data}
        if(state.hoveredNode && !graph.extremities(edge).every((n) => n === state.hoveredNode || graph.areNeighbors(n, state.hoveredNode))) {
            res.hidden =true
        } else if (graph.hasExtremity(edge, state.hoveredNode)) {
            console.log('set edges to color')
            res.color = "#990000"
            res.size = 4
            res.zIndex = 1,
            res.label=''
        }
        // if (edge == hoveredEdge.value) {
        //     console.log('hoveredEdge')
        //     res.color = "#054cb7"
        //     res.size = 4
        //     res.label = data.score + ', ' + data.pval
        // }

        return res;
    })
    filterState.score = score.value
    updateGraphByScore(score.value)

}
const setHoveredNode = (node) => {
    console.log('setHoveredNode')
    if (node) {
    //   state.value.hoveredNode = node;
    //   state.value.hoveredNeighbors = new Set(graph.neighbors(node));
      state.hoveredNode = node
      state.hoveredNeighbors = new Set(graph.neighbors(node))
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
const updateFilters = (filterType, modelValue) => {
    console.log('updateFilters',modelValue)
    filterState[filterType] = modelValue

}
const updateGraphByPosition = () => {
    console.log('updateGraphByPosition', positionsVmodel.value)
    if(positionsVmodel.value !== null && positionsVmodel.value.length !== 0){
        graph.forEachNode((node, {position}) => {
            graph.setNodeAttribute(node, 'hidden', !positionsVmodel.value.includes(position))
        })
        renderer.value.refresh({
            skipIndexation: true,
        })
    } else {
        graph.forEachNode((node) => {
            graph.setNodeAttribute(node, 'hidden', false)
        })
        renderer.value.refresh({
            // We don't touch the graph data so we can skip its reindexation
            skipIndexation: true,
        })
    }
}
const updateGraphByProteinName = () => {
    console.log('updateGraphByPosition', proteinNameModel.value)
    if(proteinNameModel.value !== null && proteinNameModel.value.length !== 0){
        graph.forEachNode((node, {protein}) => {
            const isHidden = graph.getNodeAttribute(node, 'hidden')
            if(isHidden == undefined || !isHidden) {
                graph.setNodeAttribute(node, 'hidden', !proteinNameModel.value.includes(protein))
            }
        })
        renderer.value.refresh({
            skipIndexation: true,
        })
    } else {
        resetGraph()
        if(modificationsVmodel.value.length > 0){
            updateGraphByModification()
        }
    }
}

const updateGraphByResidue = () => {
    console.log('updateGraphByPosition', residuesVmodel.value)
    if(residuesVmodel.value !== null && residuesVmodel.value.length !== 0){
        graph.forEachNode((node, {residue}) => {
            graph.setNodeAttribute(node, 'hidden', !residuesVmodel.value.includes(residue))
        })
        renderer.value.refresh({
            skipIndexation: true,
        })
    } else {
        graph.forEachNode((node) => {
            graph.setNodeAttribute(node, 'hidden', false)
        })
        renderer.value.refresh({
            // We don't touch the graph data so we can skip its reindexation
            skipIndexation: true,
        })
    }
}
// const decrement = () => {
//     score.value = score.value > 0 ? score.value - 0.1 : 0
//     updateGraphByScore(score.value)
// }
// const increment = () => {
//     score.value = score.value < 1 ? score.value + 0.1 : 1
//     updateGraphByScore(score.value)
// }
const updateGraphByScore = (score) => {
    renderer.value.setSetting('edgeReducer', (edge, data) => {
        const res = {...data}
        // console.log(res)
        if(res.score >= score[0] && res.score <= score[1]){
            res.hidden = true
        }
        return res;
    })
}
const updateGraphByPval = () => {
    renderer.value.setSetting('edgeReducer', (edge, data) => {
        const res = {...data}
        if(res.pval >= pval.value){
            res.hidden = true
        }
        return res;
    })
}
const updateGraphByModification = () => {
    if(modificationsVmodel.value !== null && modificationsVmodel.value.length > 0) {
        graph.forEachNode((node, {modification}) => {
            // console.log(node)
            const isHidden = graph.getNodeAttribute(node, 'hidden')
            console.log('isHidden',isHidden)
            if(isHidden == undefined || !isHidden) {
                graph.setNodeAttribute(node, 'hidden', !modificationsVmodel.value.includes(modification))
            }
        })
        // updateGraphByScore(score.value)
        renderer.value.refresh({
            // We don't touch the graph data so we can skip its reindexation
            skipIndexation: true,
        });
    } else {
        resetGraph()
        if(proteinName.value.length > 0) {
            updateGraphByProteinName()
        }
    }
}
const resetGraph = () => {
    graph.forEachNode((node) => {
        graph.setNodeAttribute(node, 'hidden', undefined)
    })
    renderer.value.refresh({
        // We don't touch the graph data so we can skip its reindexation
        skipIndexation: true,
    })
}
const getMouseLayer = () => {
  return document.querySelector(".sigma-mouse");
}

const addDataToGraph = () => {
    dataNodes.value.forEach((line, index) => {
        if(index > 0) {
            graph.addNode(line[0], {size: 10, label: line[0], protein: line[1], modification: line[4], position: line[2], residue: line[3]})
        }
    });

    dataEdges.value.forEach((line, index) => {
        if(index > 0) {
            graph.addEdge(line[0], line[1], {type: 'line', label: '', color: '#cccccc', weight: 1, score: Number.parseFloat(line[2]), pval: Number.parseFloat(line[4])})
        }
    })
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
      // console.log('dataEdges', dataEdges.value)
  } catch (error) {
      console.log(error.message)
  }
}
const getDataModifications = async () => {
    console.log('getmodifications')
    const url = baseApiUrl + 'get-data-modifications'
    try {
        const response = await fetch(url)
        if(!response.ok) {
            throw new Error(`Response status: ${response.status}`)
        }
        dataUnimod.value = await response.json()
        // console.log('dataUnimod', dataUnimod.value)
    } catch (error) {
        console.log(error.message)
    }

}
const setFiltersAttributes = () => {
    dataNodes.value.forEach( (row, index) => {
        if(index > 0) {
            if(!positions.value.includes(row[2])){
                positions.value.push(row[2])
            }
            if(!residues.value.includes(row[3])){
                residues.value.push(row[3])
            }
            if(!proteins.value.includes(row[1])){
                proteins.value.push(row[1])
            }
        }
    })
}
const setModifications = async() => {
    await getDataModifications()
    // console.log('setModifications', dataNodes.value)
    dataNodes.value.forEach( (row, index) => {
        if(index > 0) {
            if(!modifications.value.includes(row[4])){
                modifications.value.push(row[4])
            }
        }
    })
    modifications.value.sort(compareNumbers)
    modifications.value.forEach((value, index) => {
        // console.log('modVal in forEach',value)
        const foundUnimod = dataUnimod.value.filter((el) => {
            return el[0] == value
        })
        // console.log('foundUnimod',foundUnimod)
        modifications.value[index] = foundUnimod[0]
    })
    // console.log('modifications',modifications.value)
}
const toggleModifications = () => {
    console.log('modifications vmodel', modificationsVmodel.value)
}

const compareNumbers = (a, b) => {
  return a - b;
}

</script>

<template lang="pug">
v-row
    .v-col-9
        div(id="loader")
            .loader
        div(id="sigma-network")
    //- div(ref="container")
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
            h5 PVal
            v-radio-group(
                v-model="pval"
            )
                v-radio(
                    value="0.05"
                    label="< 0.05"
                )
                v-radio(
                    value="0.01"
                    label="< 0.01"
                )
                v-radio(
                    value="0.001"
                    label="< 0.001"
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
            //- @update:modelValue="updateGraphByFilters"
        v-expansion-panels
            v-expansion-panel
                v-expansion-panel-title(collapse-icon="mdi-minus" expand-icon="mdi-plus")
                    | Modifications
                v-expansion-panel-text.extension-panel
                    v-list
                        v-list-item(v-for="item in modifications" :key="item[0]")
                            v-checkbox(
                                v-model="modificationsVmodel"
                                :value="item[0]"
                                
                            )
                                //- @update:modelValue="updateGraphByFilters"
                                template(
                                    v-slot:label
                                )
                                    | {{ item[0] }} {{item[1]}} {{item[3] }}
            v-expansion-panel
                v-expansion-panel-title(collapse-icon="mdi-minus" expand-icon="mdi-plus")
                    | Positions
                v-expansion-panel-text.extension-panel
                    v-autocomplete(
                        clearable
                        closable-chips
                        chips
                        v-model="positionsVmodel"
                        :items="positions"
                        multiple
                        @update:modelValue="updateGraphByPosition"
                    )
            v-expansion-panel
                v-expansion-panel-title(collapse-icon="mdi-minus" expand-icon="mdi-plus")
                    | Residues
                v-expansion-panel-text.extension-panel
                    v-list
                        v-list-item(v-for="item in residues" :key="item")
                            v-checkbox(
                                v-model="residuesVmodel"
                                :value="item"
                                @update:modelValue="updateGraphByResidue"
                            )
                                template(
                                    v-slot:label
                                )
                                    | {{ item }}
                
        //- | {{ modificationsVmodel }}

                    
                        


    
</template>

<style lang="scss" scoped>
#sigma-network {
  width: 100%;
  height: 1000px;
}
.extension-panel {
    max-height: 500px;
    overflow-y: scroll;
}

</style>


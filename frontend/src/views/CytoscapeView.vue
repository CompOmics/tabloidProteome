<script setup>
import { useTemplateRef, ref, watch, onMounted, onBeforeMount } from 'vue'
import TheWelcome from '../components/SigmaComponent.vue'
import cytoscape from 'cytoscape'

const baseApiUrl = 'http://localhost:5600/api/v1/'
const data = ref(null)
watch(
  () => data.value,
  () => {
    console.log('data changed')
    // const cy = cytoscape({
    //   container: document.getElementById('cy'),
    //   elements: data.value,
    //   style: [ // the stylesheet for the graph
    //     {
    //       selector: 'node',
    //       width: "100",
    //       height: "100",
    //       style: {
    //         'background-color': '#dbf709',
    //         'label': 'data(id)'
    //       }
    //     },
    //     {
    //       selector: 'edge',
    //       style: {
    //         'width': 10,
    //         'line-color': '#35c4c1',
    //         // 'target-arrow-color': '#c43535',
    //         // 'target-arrow-shape': 'triangle',
    //         'curve-style': 'bezier'
    //       }
    //     }
    //   ],
    //   layout: {
    //     name: 'cose',
    //     rows: 1
    //   }
    // })
  }
)

onBeforeMount(async () => {
  console.log('onBeforeMount')
  await getData()
})
onMounted(() => {
  console.log('onMounted')
  // const cy = cytoscape({
  //   container: document.getElementById('cy'),
  //   elements: data.value,
  //   style: [ // the stylesheet for the graph
  //     {
  //       selector: 'node',
  //       width: "100",
  //       height: "100",
  //       style: {
  //         'background-color': '#dbf709',
  //         'label': 'data(id)'
  //       }
  //     },

  //     {
  //       selector: 'edge',
  //       style: {
  //         'width': 10,
  //         'line-color': '#35c4c1',
  //         // 'target-arrow-color': '#c43535',
  //         // 'target-arrow-shape': 'triangle',
  //         'curve-style': 'bezier'
  //       }
  //     }
  //   ],
  //   layout: {
  //     name: 'cose',
  //     rows: 1
  //   }
  // })
})

const getData = async () => {
  console.log('getdata')
  const url = baseApiUrl + 'get-data'
  try {
      const response = await fetch(url)
      // console.log(response)
      if(!response.ok) {
          throw new Error(`Response status: ${response.status}`)
      }
      const res_json = await response.json()
      data.value = res_json
      console.log('data', data.value)
  } catch (error) {
      console.log(error.message)
  }
}

</script>

<template lang="pug">
v-container(style="margin-top:200px")
  p home page
  div
    div(id="cy")
    
</template>

<style lang="scss" scoped>
#cy {
  width: 100%;
  height: 500px;
}

</style>

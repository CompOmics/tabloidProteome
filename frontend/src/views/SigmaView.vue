<script setup>
// import { useTemplateRef, ref, watch, onMounted, onBeforeMount } from 'vue'
import SigmaComponent from '../components/SigmaComponent.vue'

// const baseApiUrl = 'http://localhost:5600/api/v1/'
// const data = ref(null)
// watch(
//   () => data.value,
//   () => {
//     console.log('data changed')
//   }
// )

// const getData = async () => {
//   console.log('getdata')
//   const url = baseApiUrl + 'get-data'
//   try {
//       const response = await fetch(url)
//       // console.log(response)
//       if(!response.ok) {
//           throw new Error(`Response status: ${response.status}`)
//       }
//       const res_json = await response.json()
//       data.value = res_json
//       console.log('data', data.value)
//   } catch (error) {
//       console.log(error.message)
//   }
// }

</script>

<template lang="pug">
v-container(fluid style="margin-top:100px")
    SigmaComponent

</template>

<style lang="scss" scoped>
#cy {
  width: 100%;
  height: 500px;
}

</style>

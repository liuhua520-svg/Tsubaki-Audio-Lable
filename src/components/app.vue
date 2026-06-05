<script lang="ts">
import { defineComponent } from 'vue'

export const App = defineComponent({
  name: 'App',
  props: {
    backend: String,
    baseURL: String,
  },
  emits: ['mount:app'],
  mounted() {
    this.$emit('mount:app', this)
  }
})

export default App
</script>

<template>
  <div class="app">
    <header class="app-header">
      <h1>Tsubaki Audio Lable</h1>
      <p>音频标注与音高处理工作室</p>
    </header>
    <main class="app-main">
      <div class="content">
        <h2>欢迎使用 Tsubaki Audio Lable</h2>
        <p>后端: {{ backend }}</p>
        <p>API URL: {{ baseURL }}</p>
      </div>
    </main>
  </div>
</template>
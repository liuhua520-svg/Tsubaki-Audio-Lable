import { defineComponent } from 'vue'

const App = defineComponent({
  name: 'App',
  props: {
    backend: String,
    baseURL: String,
  },
  template: `
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
  `,
  mounted() {
    this.$emit('mount:app', this)
  }
})

export { App }
export default App

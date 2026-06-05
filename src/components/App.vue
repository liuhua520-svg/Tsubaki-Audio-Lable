<script setup lang="ts">
import { ref, reactive, computed } from 'vue'

const backend = ref('python')
const baseURL = ref('/')

const state = reactive({
  audioFile: null as File | null,
  waveformData: null as Float32Array | null,
  sampleRate: 0,
  f0Data: null as Float32Array | null,
  spectrogramData: null as Float32Array | null,
  aperiodicityData: null as Float32Array | null,
  isProcessing: false,
  error: null as string | null,
})

const supportedFormats = computed(() => ['wav', 'mp3', 'flac', 'ogg', 'm4a'])

async function loadAudioFile(file: File) {
  try {
    state.error = null
    state.isProcessing = true
    state.audioFile = file

    if (file.size > 100 * 1024 * 1024) {
      throw new Error(`文件过大: ${(file.size / 1024 / 1024).toFixed(2)}MB (最大100MB)`)
    }

    const response = await fetch(`${baseURL.value}soundfile/read`, {
      method: 'POST',
      body: file,
    })

    if (!response.ok) throw new Error('音频加载失败')

    const buffer = await response.arrayBuffer()
    // 这里假设后端返回 msgpack 格式，需要 msgpack 解析库
    // 简化处理：直接从 buffer 中提取数据
    const data = JSON.parse(new TextDecoder().decode(buffer))
    
    state.waveformData = new Float32Array(data.data.buffer)
    state.sampleRate = data.fs
  } catch (err) {
    state.error = err instanceof Error ? err.message : '未知错误'
  } finally {
    state.isProcessing = false
  }
}

// src/components/App.vue
async function extractPitch() {
  if (!state.waveformData) return

  try {
    state.error = null
    state.isProcessing = true

    // 创建 Uint8Array 来包装 Float32Array 的 buffer
    const uint8Data = new Uint8Array(state.waveformData.buffer)
    
    const response = await fetch(`${baseURL.value}pyworld/dio`, {
      method: 'POST',
      body: uint8Data as any,
      headers: { 'Content-Type': 'application/msgpack' },
    })

    if (!response.ok) throw new Error('音高提取失败')
    // ... 后续保持不变

    const buffer = await response.arrayBuffer()
    const data = JSON.parse(new TextDecoder().decode(buffer))
    state.f0Data = new Float32Array(data.f0.buffer)
  } catch (err) {
    state.error = err instanceof Error ? err.message : '未知错误'
  } finally {
    state.isProcessing = false
  }
}

async function sharpenPitch(sharpness: number) {
  if (!state.f0Data) return

  try {
    state.error = null
    state.isProcessing = true

    const response = await fetch(`${baseURL.value}pyworld/sharpen`, {
      method: 'POST',
      body: JSON.stringify({
        f0: Array.from(state.f0Data),
        sharpness,
      }),
      headers: { 'Content-Type': 'application/json' },
    })

    if (!response.ok) throw new Error('音高锐化失败')

    const data = await response.json()
    state.f0Data = new Float32Array(data.buffer || data)
  } catch (err) {
    state.error = err instanceof Error ? err.message : '未知错误'
  } finally {
    state.isProcessing = false
  }
}

async function exportLabel(format: 'lab' | 'json') {
  if (!state.f0Data || !state.audioFile) return

  try {
    state.error = null
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-')
    const filename = `${state.audioFile.name.replace(/\.[^.]+$/, '')}_${timestamp}.${format}`

    const link = document.createElement('a')
    
    if (format === 'lab') {
      const labContent = generateLabFormat(state.f0Data)
      link.href = URL.createObjectURL(new Blob([labContent], { type: 'text/plain' }))
    } else {
      const jsonData = {
        audioFile: state.audioFile.name,
        sampleRate: state.sampleRate,
        f0: Array.from(state.f0Data),
        timestamp: new Date().toISOString(),
      }
      link.href = URL.createObjectURL(new Blob([JSON.stringify(jsonData, null, 2)], { type: 'application/json' }))
    }

    link.download = filename
    link.click()
    URL.revokeObjectURL(link.href)
  } catch (err) {
    state.error = err instanceof Error ? err.message : '导出失败'
  }
}

async function exportSynthesis(format: 'ustx' | 'svp' | 'vsqx') {
  if (!state.f0Data) return

  try {
    state.error = null
    
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-')
    const filename = `synthesis_${timestamp}.${format}`
    
    const link = document.createElement('a')
    const content = `[Synthesis Data]\nFormat: ${format}\nPitch points: ${state.f0Data.length}\n`
    link.href = URL.createObjectURL(new Blob([content], { type: 'text/plain' }))
    link.download = filename
    link.click()
    URL.revokeObjectURL(link.href)
  } catch (err) {
    state.error = err instanceof Error ? err.message : '导出失败'
  }
}

function generateLabFormat(f0: Float32Array): string {
  let labContent = ''
  const framePeriod = 5
  
  for (let i = 0; i < f0.length; i++) {
    const startTime = (i * framePeriod) / 1000
    const endTime = ((i + 1) * framePeriod) / 1000
    const pitch = f0[i] > 0 ? f0[i].toFixed(2) : '0'
    labContent += `${startTime.toFixed(4)} ${endTime.toFixed(4)} ${pitch}\n`
  }
  
  return labContent
}
</script>

<template>
  <div class="app">
    <header class="app-header">
      <h1>Tsubaki Audio Label</h1>
      <p>音频标注与音高处理工作室</p>
      <p class="subtitle">Backend: {{ backend }} | API: {{ baseURL }}</p>
    </header>

    <main class="app-main">
      <div class="container">
        <div v-if="state.error" class="error-banner">
          <span class="error-icon">⚠️</span>
          <span>{{ state.error }}</span>
          <button @click="state.error = null" class="close-btn">×</button>
        </div>

        <ControlPanel
          :is-processing="state.isProcessing"
          :has-audio="!!state.waveformData"
          :has-pitch="!!state.f0Data"
          @load-audio="loadAudioFile"
          @extract-pitch="extractPitch"
          @sharpen-pitch="sharpenPitch"
          @export-label="exportLabel"
          @export-synthesis="exportSynthesis"
          :supported-formats="supportedFormats"
        />

        <div class="editor-container">
          <AudioPlayer
            v-if="state.waveformData"
            :waveform-data="state.waveformData"
            :sample-rate="state.sampleRate"
            :audio-file="state.audioFile"
          />

          <div class="waveform-section">
            <h3>波形图</h3>
            <WaveformDisplay
              v-if="state.waveformData"
              :waveform-data="state.waveformData"
              :pitch-data="state.f0Data"
              :sample-rate="state.sampleRate"
            />
            <div v-else class="placeholder">
              <p>加载音频文件查看波形</p>
            </div>
          </div>

          <div class="pitch-section">
            <h3>音高编辑</h3>
            <PitchEditor
              v-if="state.f0Data"
              :pitch-data="state.f0Data"
              :sample-rate="state.sampleRate"
            />
            <div v-else class="placeholder">
              <p>提取音高进行编辑</p>
            </div>
          </div>
        </div>
      </div>
    </main>

    <footer class="app-footer">
      <p>© 2024 Tsubaki Audio Label | Python 3.10.20 | PyWorld</p>
    </footer>
  </div>
</template>

<style scoped>
.app {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #f5f5f5;
}

.app-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.app-header h1 {
  margin: 0;
  font-size: 28px;
  font-weight: 600;
}

.app-header p {
  margin: 5px 0 0;
  font-size: 14px;
  opacity: 0.9;
}

.subtitle {
  font-size: 12px !important;
  opacity: 0.8 !important;
  margin-top: 5px !important;
}

.app-main {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.container {
  max-width: 1400px;
  margin: 0 auto;
}

.error-banner {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  margin-bottom: 20px;
  background: #fee;
  border-left: 4px solid #f66;
  border-radius: 4px;
  color: #c33;
}

.error-icon {
  font-size: 18px;
}

.close-btn {
  margin-left: auto;
  background: none;
  border: none;
  font-size: 20px;
  cursor: pointer;
  color: #c33;
}

.editor-container {
  display: grid;
  grid-template-columns: 1fr;
  gap: 20px;
  margin-top: 20px;
}

.waveform-section,
.pitch-section {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.1);
}

.waveform-section h3,
.pitch-section h3 {
  margin: 0 0 15px;
  font-size: 16px;
  color: #333;
}

.placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 300px;
  background: #f9f9f9;
  border: 2px dashed #ddd;
  border-radius: 4px;
  color: #999;
}

.app-footer {
  background: #333;
  color: #999;
  padding: 15px 20px;
  text-align: center;
  font-size: 12px;
  border-top: 1px solid #444;
}

.app-footer p {
  margin: 0;
}

@media (max-width: 1024px) {
  .app-header h1 {
    font-size: 24px;
  }
}
</style>

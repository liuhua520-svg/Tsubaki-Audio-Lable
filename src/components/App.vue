<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import FileUploadPanel from './FileUploadPanel.vue'
import WaveformViewer from './WaveformViewer.vue'
import PitchEditor from './PitchEditor.vue'
import PitchExtractor from './PitchExtractor.vue'
import ExportPanel from './ExportPanel.vue'

const state = reactive({
  // Audio data
  audioFile: null as File | null,
  waveformData: null as Float32Array | null,
  sampleRate: 0,
  duration: 0,
  
  // Pitch data
  f0Data: null as Float32Array | null,
  f0Backup: null as Float32Array | null, // Backup for undo
  timeAxis: null as Float32Array | null,
  
  // LAB data
  labContent: null as string | null,
  labFile: null as File | null,
  
  // UI state
  isProcessing: false,
  error: null as string | null,
  success: null as string | null,
  activeTab: 'waveform' as 'waveform' | 'pitch' | 'export',
  
  // Settings
  f0Algorithm: 'dio' as 'dio' | 'harvest',
  pitchSharpness: 0.5,
  baseFrequency: 60,
})

const baseURL = ref('http://127.0.0.1:6701/')
const isAudioLoaded = computed(() => !!state.waveformData)
const isPitchExtracted = computed(() => !!state.f0Data)
const canExport = computed(() => !!state.f0Data || !!state.labContent)

// File upload handlers
async function handleAudioUpload(file: File) {
  try {
    state.error = null
    state.success = null
    state.isProcessing = true
    
    if (file.size > 500 * 1024 * 1024) {
      throw new Error('音频文件过大 (最大500MB)')
    }

    const response = await fetch(`${baseURL.value}soundfile/read`, {
      method: 'POST',
      body: file,
    })

    if (!response.ok) throw new Error('音频加载失败')

    const buffer = await response.arrayBuffer()
    // Backend returns msgpack format, need to decode
    const decoder = new TextDecoder()
    const data = JSON.parse(decoder.decode(buffer))
    
    state.audioFile = file
    state.waveformData = new Float32Array(data.data.buffer)
    state.sampleRate = data.fs
    state.duration = state.waveformData.length / state.sampleRate
    state.f0Data = null // Reset pitch data
    state.labContent = null
    
    state.success = `成功加载: ${file.name} (${(state.duration).toFixed(2)}s)`
  } catch (err) {
    state.error = err instanceof Error ? err.message : '未知错误'
  } finally {
    state.isProcessing = false
  }
}

async function handleLabUpload(file: File) {
  try {
    state.error = null
    state.success = null
    
    const content = await file.text()
    state.labFile = file
    state.labContent = content
    
    // Parse LAB file to extract pitch data
    parseLabFile(content)
    
    state.success = `成功导入 LAB 文件: ${file.name}`
  } catch (err) {
    state.error = err instanceof Error ? err.message : '导入失败'
  }
}

function parseLabFile(content: string) {
  try {
    const lines = content.trim().split('\n')
    const f0Data: number[] = []
    
    for (const line of lines) {
      const parts = line.trim().split(/\s+/)
      if (parts.length >= 3) {
        const pitch = parseFloat(parts[2])
        f0Data.push(pitch)
      }
    }
    
    if (f0Data.length > 0) {
      state.f0Data = new Float32Array(f0Data)
      state.activeTab = 'pitch'
    }
  } catch (err) {
    console.error('LAB文件解析错误:', err)
    throw new Error('LAB文件格式错误')
  }
}

// Pitch extraction
async function extractPitch() {
  if (!state.waveformData) return

  try {
    state.error = null
    state.isProcessing = true
    state.f0Backup = state.f0Data ? new Float32Array(state.f0Data) : null

    const algorithm = state.f0Algorithm === 'dio' ? 'dio' : 'harvest'
    const endpoint = `${baseURL.value}pyworld/${algorithm}`
    
    // Convert Float32Array to Uint8Array
    const uint8Data = new Uint8Array(state.waveformData.buffer)
    
    const response = await fetch(endpoint, {
      method: 'POST',
      body: uint8Data as any,
      headers: { 'Content-Type': 'application/msgpack' },
    })

    if (!response.ok) throw new Error(`${algorithm.toUpperCase()}算法提取失败`)

    const buffer = await response.arrayBuffer()
    const data = JSON.parse(new TextDecoder().decode(buffer))
    
    state.f0Data = new Float32Array(data.f0.buffer)
    state.timeAxis = new Float32Array(data.t.buffer)
    state.activeTab = 'pitch'
    
    state.success = `${algorithm.toUpperCase()}算法提取成功`
  } catch (err) {
    state.error = err instanceof Error ? err.message : '提取失败'
  } finally {
    state.isProcessing = false
  }
}

// Pitch sharpening
async function sharpenPitch() {
  if (!state.f0Data) return

  try {
    state.error = null
    state.isProcessing = true

    const response = await fetch(`${baseURL.value}pyworld/sharpen`, {
      method: 'POST',
      body: JSON.stringify({
        f0: Array.from(state.f0Data),
        sharpness: state.pitchSharpness,
      }),
      headers: { 'Content-Type': 'application/json' },
    })

    if (!response.ok) throw new Error('音高锐化失败')

    const data = await response.json()
    state.f0Data = new Float32Array(data.buffer || data)
    
    state.success = `音高锐化成功 (锐化度: ${state.pitchSharpness})`
  } catch (err) {
    state.error = err instanceof Error ? err.message : '锐化失败'
  } finally {
    state.isProcessing = false
  }
}

// Undo last pitch operation
function undoPitchEdit() {
  if (state.f0Backup) {
    state.f0Data = new Float32Array(state.f0Backup)
    state.success = '已撤销'
  }
}

// Export handlers
async function exportAsLab() {
  if (!state.f0Data) return

  try {
    state.error = null
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-')
    const filename = `${state.audioFile?.name.replace(/\.[^.]+$/, '') || 'audio'}_${timestamp}.lab`

    const labContent = generateLabFormat(state.f0Data)
    const blob = new Blob([labContent], { type: 'text/plain' })
    
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = filename
    link.click()
    URL.revokeObjectURL(link.href)
    
    state.success = `LAB文件已导出: ${filename}`
  } catch (err) {
    state.error = err instanceof Error ? err.message : '导出失败'
  }
}

async function exportAsSynthesis(format: 'ustx' | 'svp' | 'vsqx') {
  if (!state.f0Data) return

  try {
    state.error = null
    state.isProcessing = true
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-')
    const filename = `${state.audioFile?.name.replace(/\.[^.]+$/, '') || 'audio'}_${timestamp}.${format}`

    const endpoint = `${baseURL.value}pyworld/synthesis_export`
    const response = await fetch(endpoint, {
      method: 'POST',
      body: JSON.stringify({
        f0: Array.from(state.f0Data),
        format: format,
        sampleRate: state.sampleRate,
        bpm: 120,
      }),
      headers: { 'Content-Type': 'application/json' },
    })

    if (!response.ok) throw new Error(`${format.toUpperCase()}格式导出失败`)

    const blob = await response.blob()
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = filename
    link.click()
    URL.revokeObjectURL(link.href)
    
    state.success = `${format.toUpperCase()}文件已导出: ${filename}`
  } catch (err) {
    state.error = err instanceof Error ? err.message : '导出失败'
  } finally {
    state.isProcessing = false
  }
}

function generateLabFormat(f0: Float32Array): string {
  let labContent = ''
  const framePeriod = 5 // milliseconds
  
  for (let i = 0; i < f0.length; i++) {
    const startTime = (i * framePeriod) / 1000
    const endTime = ((i + 1) * framePeriod) / 1000
    const pitch = f0[i] > 0 ? f0[i].toFixed(2) : '0'
    labContent += `${startTime.toFixed(4)} ${endTime.toFixed(4)} ${pitch}\n`
  }
  
  return labContent
}

function clearError() {
  state.error = null
}

function clearSuccess() {
  state.success = null
}
</script>

<template>
  <div class="app">
    <!-- Header -->
    <header class="app-header">
      <div class="header-content">
        <h1>🎵 Tsubaki Audio Label</h1>
        <p class="subtitle">音频标注与音高处理工作室</p>
        <p class="info">Backend: {{ baseURL }} | Status: {{ state.isProcessing ? '处理中...' : '就绪' }}</p>
      </div>
    </header>

    <!-- Main Content -->
    <main class="app-main">
      <!-- Alerts -->
      <div v-if="state.error" class="alert alert-error">
        <span>⚠️ {{ state.error }}</span>
        <button @click="clearError" class="btn-close">×</button>
      </div>
      
      <div v-if="state.success" class="alert alert-success">
        <span>✓ {{ state.success }}</span>
        <button @click="clearSuccess" class="btn-close">×</button>
      </div>

      <div class="container">
        <!-- Tabs Navigation -->
        <div class="tabs-header">
          <button
            :class="['tab-btn', { active: state.activeTab === 'waveform' }]"
            @click="state.activeTab = 'waveform'"
            :disabled="!isAudioLoaded"
          >
            📊 波形图
          </button>
          <button
            :class="['tab-btn', { active: state.activeTab === 'pitch' }]"
            @click="state.activeTab = 'pitch'"
            :disabled="!isPitchExtracted && !state.labContent"
          >
            🎼 音高编辑
          </button>
          <button
            :class="['tab-btn', { active: state.activeTab === 'export' }]"
            @click="state.activeTab = 'export'"
            :disabled="!canExport"
          >
            💾 导出
          </button>
        </div>

        <!-- Tab Content -->
        <div class="tabs-content">
          <!-- Upload & Waveform Tab -->
          <div v-if="state.activeTab === 'waveform'" class="tab-pane">
            <FileUploadPanel
              @upload-audio="handleAudioUpload"
              @upload-lab="handleLabUpload"
              :is-processing="state.isProcessing"
            />
            
            <WaveformViewer
              v-if="state.waveformData"
              :waveform-data="state.waveformData"
              :pitch-data="state.f0Data ?? undefined"
              :sample-rate="state.sampleRate"
              :duration="state.duration"
            />
          </div>

          <!-- Pitch Editor Tab -->
          <div v-if="state.activeTab === 'pitch'" class="tab-pane">
            <PitchExtractor
              :audio-loaded="isAudioLoaded"
              :pitch-extracted="isPitchExtracted"
              :algorithm="state.f0Algorithm"
              :sharpness="state.pitchSharpness"
              :base-frequency="state.baseFrequency"
              :is-processing="state.isProcessing"
              @extract-pitch="extractPitch"
              @sharpen-pitch="sharpenPitch"
              @undo="undoPitchEdit"
              @update:algorithm="(v: string) => state.f0Algorithm = v as 'dio' | 'harvest'"
              @update:sharpness="(v: number) => state.pitchSharpness = v"
              @update:baseFrequency="(v: number) => state.baseFrequency = v"
            />
            
            <PitchEditor
              v-if="state.f0Data"
              :pitch-data="state.f0Data"
              :sample-rate="state.sampleRate"
              :base-frequency="state.baseFrequency"
            />
          </div>

          <!-- Export Tab -->
          <div v-if="state.activeTab === 'export'" class="tab-pane">
            <ExportPanel
              :has-pitch="isPitchExtracted"
              :audio-file="state.audioFile"
              :is-processing="state.isProcessing"
              @export-lab="exportAsLab"
              @export-format="(format: string) => exportAsSynthesis(format as 'ustx' | 'svp' | 'vsqx')"
            />
          </div>
        </div>
      </div>
    </main>

    <!-- Footer -->
    <footer class="app-footer">
      <p>© 2024 Tsubaki Audio Label | Python 3.10.20 | PyWorld</p>
    </footer>
  </div>
</template>

<style scoped>
:root {
  --primary: #667eea;
  --secondary: #764ba2;
  --success: #48bb78;
  --error: #f56565;
  --warning: #ed8936;
  --border: #e2e8f0;
  --bg-light: #f7fafc;
  --text-dark: #2d3748;
}

* {
  box-sizing: border-box;
}

.app {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background-color: var(--bg-light);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

/* Header */
.app-header {
  background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
  color: white;
  padding: 24px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.header-content h1 {
  margin: 0 0 8px 0;
  font-size: 32px;
  font-weight: 700;
}

.header-content .subtitle {
  margin: 0;
  font-size: 14px;
  opacity: 0.95;
}

.header-content .info {
  margin: 8px 0 0;
  font-size: 12px;
  opacity: 0.8;
}

/* Main */
.app-main {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.container {
  max-width: 1600px;
  margin: 0 auto;
}

/* Alerts */
.alert {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  margin-bottom: 20px;
  border-radius: 6px;
  font-size: 14px;
  animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.alert-error {
  background-color: #fed7d7;
  border-left: 4px solid var(--error);
  color: #c53030;
}

.alert-success {
  background-color: #c6f6d5;
  border-left: 4px solid var(--success);
  color: #22543d;
}

.btn-close {
  margin-left: auto;
  background: none;
  border: none;
  font-size: 20px;
  cursor: pointer;
  padding: 0;
  color: inherit;
}

/* Tabs */
.tabs-header {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
  border-bottom: 2px solid var(--border);
  overflow-x: auto;
}

.tab-btn {
  padding: 12px 20px;
  border: none;
  background: none;
  font-size: 14px;
  font-weight: 600;
  color: #718096;
  cursor: pointer;
  border-bottom: 3px solid transparent;
  transition: all 0.3s ease;
  white-space: nowrap;
}

.tab-btn:hover:not(:disabled) {
  color: var(--text-dark);
}

.tab-btn.active {
  color: var(--primary);
  border-bottom-color: var(--primary);
}

.tab-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.tabs-content {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  overflow: hidden;
}

.tab-pane {
  padding: 24px;
  animation: fadeIn 0.3s ease-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

/* Footer */
.app-footer {
  background: var(--text-dark);
  color: #a0aec0;
  padding: 16px 24px;
  text-align: center;
  font-size: 12px;
  border-top: 1px solid var(--border);
}

.app-footer p {
  margin: 0;
}

/* Responsive */
@media (max-width: 768px) {
  .app-header {
    padding: 16px;
  }

  .app-header h1 {
    font-size: 24px;
  }

  .app-main {
    padding: 16px;
  }

  .tab-pane {
    padding: 16px;
  }

  .tabs-header {
    gap: 4px;
  }

  .tab-btn {
    padding: 10px 16px;
    font-size: 12px;
  }
}
</style>
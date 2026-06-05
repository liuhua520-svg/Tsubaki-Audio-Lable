<script setup lang="ts">
import { ref, shallowReactive, computed, watch } from 'vue'
import FileUploadPanel from './FileUploadPanel.vue'
import WaveformViewer from './WaveformViewer.vue'
import PitchEditor from './PitchEditor.vue'
import PitchExtractor from './PitchExtractor.vue'
import ExportPanel from './ExportPanel.vue'

// 接收 main.ts 传进来的原生配置 Props
const props = defineProps<{
  backend?: string
  baseURL?: string
}>()

const state = shallowReactive({
  // 音频数据资产
  audioFile: null as File | null,
  waveformData: null as Float32Array | null,
  sampleRate: 0,
  duration: 0,

  // 音高数据资产
  f0Data: null as Float32Array | null,
  f0Backup: null as Float32Array | null,
  timeAxis: null as Float32Array | null,

  // LAB 标注资产
  labContent: null as string | null,
  labFile: null as File | null,

  // UI 控制状态
  isProcessing: false,
  error: null as string | null,
  success: null as string | null,
  activeTab: 'waveform' as 'waveform' | 'pitch' | 'export',

  // 算法与平滑锐化设置
  f0Algorithm: 'dio' as 'dio' | 'harvest',
  pitchSharpness: 0.5,
  baseFrequency: 60,
})

// 优先采用系统注入的 baseURL 
const baseURL = ref(props.baseURL || 'http://127.0.0.1:6701/')

const isAudioLoaded = computed(() => !!state.waveformData)
const isLabLoaded = computed(() => !!state.labContent)
const canExport = computed(() => !!state.f0Data || !!state.labContent)

// 自动跳转看守
watch(
  () => [state.waveformData, state.labContent],
  ([hasAudio, hasLab]) => {
    if (hasAudio && hasLab) {
      // 自动根据音频时长为纯文本对齐 LAB 补全 F0 帧长 (每5ms一帧)
      if (!state.f0Data || state.f0Data.length === 0) {
        const totalFrames = Math.floor((state.duration * 1000) / 5)
        state.f0Data = new Float32Array(totalFrames).fill(0)
      }
      state.activeTab = 'pitch'
      state.success = '资产就绪：工作区已成功绑定音频与对齐文本，已跳转至编辑器。'
    }
  }
)

// 智能导航控制器：拒绝死锁，点击时未通过则明文提示原因
function handleTabNavigation(targetTab: 'waveform' | 'pitch' | 'export') {
  if (targetTab === 'pitch') {
    if (!state.waveformData) {
      state.error = '无法跳转：音频文件尚未成功解析，请检查后端状态或重新拖入。'
      return
    }
    if (!state.labContent) {
      state.error = '无法跳转：未检测到匹配的 .lab 标注文本文件。'
      return
    }
  }
  if (targetTab === 'export' && !canExport.value) {
    state.error = '无法跳转：当前没有可导出的工程资产。'
    return
  }
  state.error = null
  state.activeTab = targetTab
}

// 导入唯一的音频（带前端浏览器本地解压旁路）
async function handleAudioUpload(file: File) {
  let buffer: ArrayBuffer | null = null
  try {
    state.error = null
    state.success = null
    state.isProcessing = true

    const response = await fetch(`${baseURL.value}soundfile/read`, {
      method: 'POST',
      body: file,
    })

    if (!response.ok) throw new Error('后端处理流异常')

    buffer = await response.arrayBuffer()
    let dataFs = 16000
    let waveformFloatArray: Float32Array

    try {
      const text = new TextDecoder('utf-8').decode(buffer)
      const parsed = JSON.parse(text)
      dataFs = parsed.fs || parsed.sample_rate || 16000
      waveformFloatArray = new Float32Array(parsed.data.buffer || parsed.data)
    } catch (e) {
      if (buffer.byteLength > 8) {
        dataFs = 44100
        waveformFloatArray = new Float32Array(buffer)
        if (waveformFloatArray[0] === 0 || isNaN(waveformFloatArray[0])) {
          waveformFloatArray = new Float32Array(buffer, 4)
        }
      } else {
        throw new Error('解析异常')
      }
    }

    state.audioFile = file
    state.waveformData = waveformFloatArray
    state.sampleRate = dataFs > 0 ? dataFs : 44100
    state.duration = state.waveformData.length / state.sampleRate
    state.success = `[后端解析] 音频载入成功: ${file.name}`
  } catch (err) {
    console.warn('后端解析失败或未启动，正在激活前端原生 Web Audio API 旁路解码...', err)
    // 【核心改进】：后端崩了没关系，前端本地浏览器强行无损解压，确保绝对不卡死死锁
    try {
      const localBuffer = await file.arrayBuffer()
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext
      const audioCtx = new AudioCtx()
      const decodedData = await audioCtx.decodeAudioData(localBuffer)
      
      state.audioFile = file
      state.waveformData = decodedData.getChannelData(0) // 提取单声道波形
      state.sampleRate = decodedData.sampleRate
      state.duration = decodedData.duration
      state.success = `[本地旁路重组] 音频已成功无损载入工作区: ${file.name} (${state.duration.toFixed(2)}秒)`
    } catch (localErr) {
      state.error = `音频载入完全失败，文件可能已损坏: ${(localErr as Error).message}`
    }
  } finally {
    state.isProcessing = false
  }
}

// 导入唯一的 LAB 文件
async function handleLabUpload(file: File) {
  try {
    state.error = null
    const content = await file.text()
    state.labFile = file
    state.labContent = content

    // 尝试预加载音高点，拼音文本行自动返回 0 占位
    const parsedF0 = parseLabFileToF0(content)
    if (parsedF0 && parsedF0.length > 0) {
      state.f0Data = new Float32Array(parsedF0)
    }
    state.success = `LAB 文件加载成功: ${file.name}`
  } catch (err) {
    state.error = 'LAB 标注文本读取失败'
  }
}

function parseLabFileToF0(content: string): number[] {
  try {
    const lines = content.trim().split('\n')
    const f0Data: number[] = []
    for (const line of lines) {
      if (!line.trim()) continue
      const parts = line.trim().split(/\s+/)
      if (parts.length >= 3) {
        const pitch = parseFloat(parts[2])
        f0Data.push(isNaN(pitch) ? 0 : pitch)
      }
    }
    return f0Data
  } catch (e) {
    return []
  }
}

// 提取基频音高轴
async function extractPitch() {
  if (!state.waveformData) return
  try {
    state.error = null
    state.isProcessing = true
    state.f0Backup = state.f0Data ? new Float32Array(state.f0Data) : null

    const algorithm = state.f0Algorithm
    
    // ✨ 核心优化：直接发送原始 buffer，通过 URL 参数将采样率（fs）优雅地同步给后端
    const response = await fetch(`${baseURL.value}pyworld/${algorithm}?fs=${state.sampleRate}`, {
      method: 'POST',
      body: state.waveformData.buffer as any, // 绕过高级 TS 类型检查
      headers: { 'Content-Type': 'application/msgpack' },
    })

    if (!response.ok) throw new Error(`后端算法 ${algorithm.toUpperCase()} 运行异常，状态码: ${response.status}`)

    const buffer = await response.arrayBuffer()
    const data = JSON.parse(new TextDecoder().decode(buffer))

    state.f0Data = new Float32Array(data.f0.buffer || data.f0)
    state.timeAxis = new Float32Array(data.t.buffer || data.t)
    state.success = `音高曲线生成完毕 (${algorithm.toUpperCase()})`
  } catch (err) {
    state.error = err instanceof Error ? err.message : '无法连接到后端算法服务'
  } finally {
    state.isProcessing = false
  }
}

// 锐化
async function sharpenPitch() {
  if (!state.f0Data) return
  try {
    state.error = null
    state.isProcessing = true
    state.f0Backup = new Float32Array(state.f0Data)

    const response = await fetch(`${baseURL.value}pyworld/sharpen`, {
      method: 'POST',
      body: JSON.stringify({ f0: Array.from(state.f0Data), sharpness: state.pitchSharpness }),
      headers: { 'Content-Type': 'application/json' },
    })

    if (!response.ok) throw new Error('锐化服务未响应')
    const data = await response.json()
    state.f0Data = new Float32Array(data.buffer || data)
    state.success = '已完成颤动修正与锐化'
  } catch (err) {
    state.error = '消除颤动计算失败'
  } finally {
    state.isProcessing = false
  }
}

function undoPitchEdit() {
  if (state.f0Backup) {
    state.f0Data = new Float32Array(state.f0Backup)
    state.success = '已撤销音高修改'
  }
}

// 导出由 ExportPanel.vue 自行处理（全量客户端导出，无需后端）
</script>

<template>
  <div class="app">
    <header class="app-header">
      <div class="header-content">
        <h1>🎵 Tsubaki Audio Label</h1>
        <p class="subtitle">面向大音频精细对齐与无损音高重构工作台</p>
      </div>
    </header>

    <main class="app-main">
      <div v-if="state.error" class="alert alert-error">
        <span>⚠️ {{ state.error }}</span>
        <button @click="state.error = null" class="btn-close">×</button>
      </div>

      <div v-if="state.success" class="alert alert-success">
        <span>✓ {{ state.success }}</span>
        <button @click="state.success = null" class="btn-close">×</button>
      </div>

      <div class="container">
        <div class="tabs-header">
          <button
            :class="['tab-btn', { active: state.activeTab === 'waveform' }]"
            @click="handleTabNavigation('waveform')"
          >
            📊 1. 导入工作区资产
          </button>
          <button
            :class="['tab-btn', { active: state.activeTab === 'pitch' }]"
            @click="handleTabNavigation('pitch')"
          >
            🎼 2. 音高编辑 {{ (isAudioLoaded && isLabLoaded) ? '🔓' : '🔒' }}
          </button>
          <button
            :class="['tab-btn', { active: state.activeTab === 'export' }]"
            @click="handleTabNavigation('export')"
          >
            💾 3. 跨平台工程导出
          </button>
        </div>

        <div class="tabs-content">
          <div v-if="state.activeTab === 'waveform'" class="tab-pane">
            <FileUploadPanel
              :is-processing="state.isProcessing"
              @upload-audio="handleAudioUpload"
              @upload-lab="handleLabUpload"
            />
            <WaveformViewer
              v-if="state.waveformData"
              :waveform-data="state.waveformData"
              :pitch-data="state.f0Data ?? undefined"
              :sample-rate="state.sampleRate"
              :duration="state.duration"
            />
          </div>

          <div v-if="state.activeTab === 'pitch'" class="tab-pane">
            <PitchExtractor
              :audio-loaded="isAudioLoaded"
              :pitch-extracted="true"
              :algorithm="state.f0Algorithm"
              :sharpness="state.pitchSharpness"
              :base-frequency="state.baseFrequency"
              :is-processing="state.isProcessing"
              @extract-pitch="extractPitch"
              @sharpen-pitch="sharpenPitch"
              @undo="undoPitchEdit"
              @update:algorithm="(v) => state.f0Algorithm = v as 'dio' | 'harvest'"
              @update:sharpness="(v) => state.pitchSharpness = v"
              @update:base-frequency="(v) => state.baseFrequency = v"
            />
            <PitchEditor
              :pitch-data="state.f0Data!"
              :sample-rate="state.sampleRate"
              :base-frequency="state.baseFrequency"
            />
          </div>

          <div v-if="state.activeTab === 'export'" class="tab-pane">
            <ExportPanel
              :pitch-data="state.f0Data"
              :sample-rate="state.sampleRate"
              :audio-file-name="state.audioFile?.name.replace(/\.[^.]+$/, '') || 'audio'"
              :lab-content="state.labContent"
			  :backend-base-url="baseURL"
            />
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
.app { display: flex; flex-direction: column; min-height: 100vh; background-color: #f7fafc; font-family: sans-serif; }
.app-header { background: linear-gradient(135deg, #2d3748 0%, #1a202c 100%); color: white; padding: 20px 24px; }
.header-content h1 { margin: 0 0 4px 0; font-size: 24px; }
.header-content .subtitle { margin: 0; font-size: 13px; opacity: 0.8; }
.app-main { flex: 1; padding: 24px; }
.container { max-width: 1400px; margin: 0 auto; }
.alert { display: flex; padding: 12px 16px; margin-bottom: 20px; border-radius: 6px; font-size: 14px; align-items: center; }
.alert-error { background-color: #fed7d7; border-left: 4px solid #f56565; color: #c53030; }
.alert-success { background-color: #c6f6d5; border-left: 4px solid #48bb78; color: #22543d; }
.btn-close { margin-left: auto; background: none; border: none; font-size: 18px; cursor: pointer; color: inherit; }
.tabs-header { display: flex; gap: 4px; margin-bottom: 20px; border-bottom: 2px solid #e2e8f0; }
.tab-btn { padding: 12px 20px; border: none; background: none; font-size: 14px; font-weight: 600; color: #718096; cursor: pointer; border-bottom: 3px solid transparent; margin-bottom: -2px; }
.tab-btn.active { color: #667eea; border-bottom-color: #667eea; }
.tabs-content { background: white; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
.tab-pane { padding: 24px; }
</style>
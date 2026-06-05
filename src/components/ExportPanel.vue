<template>
  <div class="export-panel">
    <div class="panel-header">
      <h3>📥 导出文件</h3>
      <p class="hint">导出音高数据到各种格式</p>
    </div>

    <!-- 标注文件导出 -->
    <div class="export-section">
      <h4>🏷️ 标注文件</h4>
      <div class="export-buttons">
        <button
          class="export-btn lab-btn"
          @click="exportLab"
          :disabled="!pitchData"
          title="导出为 LAB 格式 (用于标注)"
        >
          📄 Lab 格式
        </button>
        <button
          class="export-btn json-btn"
          @click="exportJson"
          :disabled="!pitchData"
          title="导出为 JSON 格式"
        >
          📋 JSON 格式
        </button>
      </div>
    </div>

    <!-- 歌声合成导出 -->
    <div class="export-section">
      <h4>🎵 歌声合成格式</h4>
      <div class="synthesis-options">
        <div class="option-group">
          <label>
            BPM:
            <input v-model.number="bpm" type="number" min="40" max="300" class="input-sm" />
          </label>
          <label>
            基准音高:
            <input v-model.number="baseNote" type="number" min="0" max="127" class="input-sm" />
          </label>
        </div>
      </div>

      <div class="export-buttons">
        <button
          class="export-btn ustx-btn"
          @click="exportFormat('ustx')"
          :disabled="!pitchData || isExporting"
        >
          🎼 USTX (OpenUtau)
        </button>
        <button
          class="export-btn svp-btn"
          @click="exportFormat('svp')"
          :disabled="!pitchData || isExporting"
        >
          💿 SVP (Synthesizer V)
        </button>
        <button
          class="export-btn vsqx-btn"
          @click="exportFormat('vsqx')"
          :disabled="!pitchData || isExporting"
        >
          🎹 VSQX (Vocaloid)
        </button>
      </div>
    </div>

    <!-- 进度提示 -->
    <div v-if="isExporting" class="export-progress">
      <div class="spinner"></div>
      <span>正在生成文件...</span>
    </div>

    <!-- 成功提示 -->
    <div v-if="successMessage" class="success-message">
      <span>✓ {{ successMessage }}</span>
      <button class="close-btn" @click="successMessage = ''">✕</button>
    </div>

    <!-- 错误提示 -->
    <div v-if="errorMessage" class="error-message">
      <span>⚠️ {{ errorMessage }}</span>
      <button class="close-btn" @click="errorMessage = ''">✕</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps({
  pitchData: {
    type: Float32Array,
    required: false
  },
  waveformData: {
    type: Float32Array,
    required: false
  },
  sampleRate: {
    type: Number,
    default: 0
  },
  audioFileName: {
    type: String,
    default: 'audio'
  }
})

const emit = defineEmits(['export-format'])

const bpm = ref(120)
const baseNote = ref(60)
const isExporting = ref(false)
const successMessage = ref('')
const errorMessage = ref('')

const exportLab = () => {
  if (!props.pitchData) {
    errorMessage.value = '请先提取音高'
    return
  }

  try {
    let content = ''
    const framePeriod = 5 // ms
    
    for (let i = 0; i < props.pitchData.length; i++) {
      const startTime = (i * framePeriod) / 1000
      const endTime = ((i + 1) * framePeriod) / 1000
      const pitch = props.pitchData[i] > 0 ? props.pitchData[i].toFixed(2) : '0'
      content += `${startTime.toFixed(4)} ${endTime.toFixed(4)} ${pitch}\n`
    }

    downloadFile(content, `${props.audioFileName}.lab`, 'text/plain')
    successMessage.value = '✓ Lab 文件已导出'
    setTimeout(() => { successMessage.value = '' }, 3000)
  } catch (err) {
    errorMessage.value = err instanceof Error ? err.message : '导出失败'
  }
}

const exportJson = () => {
  if (!props.pitchData) {
    errorMessage.value = '请先提取音高'
    return
  }

  try {
    const data = {
      audioFile: props.audioFileName,
      sampleRate: props.sampleRate,
      f0: Array.from(props.pitchData),
      timestamp: new Date().toISOString(),
      metadata: {
        bpm: bpm.value,
        baseNote: baseNote.value
      }
    }

    downloadFile(
      JSON.stringify(data, null, 2),
      `${props.audioFileName}.json`,
      'application/json'
    )
    successMessage.value = '✓ JSON 文件已导出'
    setTimeout(() => { successMessage.value = '' }, 3000)
  } catch (err) {
    errorMessage.value = err instanceof Error ? err.message : '导出失败'
  }
}

const exportFormat = (format: 'ustx' | 'svp' | 'vsqx') => {
  if (!props.pitchData) {
    errorMessage.value = '请先提取音高'
    return
  }

  isExporting.value = true

  try {
    let content = ''

    if (format === 'ustx') {
      content = generateUstx()
    } else if (format === 'svp') {
      content = generateSvp()
    } else if (format === 'vsqx') {
      content = generateVsqx()
    }

    downloadFile(content, `${props.audioFileName}.${format}`, 'text/plain')
    successMessage.value = `✓ ${format.toUpperCase()} 文件已导出`
    setTimeout(() => { successMessage.value = '' }, 3000)
  } catch (err) {
    errorMessage.value = err instanceof Error ? err.message : '导出失败'
  } finally {
    isExporting.value = false
  }
}

const generateUstx = (): string => {
  // 简化的 USTX 格式
  let content = '[#USTX VERSION=0100]\n\n'
  content += '[#PROJECT]\n'
  content += `Name=${props.audioFileName}\n`
  content += `Bpm=${bpm.value}\n`
  content += 'Resolution=480\n\n'

  content += '[#TRACK]\n'
  content += 'Name=Track\n'
  content += 'Channel=0\n\n'

  content += '[#NOTE]\n'
  if (props.pitchData) {
    const framePeriod = 5 // ms
    for (let i = 0; i < Math.min(props.pitchData.length, 100); i++) {
      const frequency = props.pitchData[i]
      if (frequency > 0) {
        const midiNote = Math.round(12 * Math.log2(frequency / 440) + 69)
        const position = (i * framePeriod * bpm.value) / 1000
        content += `Position=${Math.floor(position * 480)}\n`
        content += `Duration=480\n`
        content += `Key=${Math.max(0, Math.min(127, midiNote))}\n`
        content += `Lyric=あ\n\n`
      }
    }
  }

  return content
}

const generateSvp = (): string => {
  // 简化的 SVP 格式 (JSON 基础)
  const notes: any[] = []
  
  if (props.pitchData) {
    const framePeriod = 5 // ms
    for (let i = 0; i < Math.min(props.pitchData.length, 100); i++) {
      const frequency = props.pitchData[i]
      if (frequency > 0) {
        const midiNote = Math.round(12 * Math.log2(frequency / 440) + 69)
        notes.push({
          onset: i * framePeriod,
          duration: framePeriod,
          pitch: midiNote,
          lyric: 'あ'
        })
      }
    }
  }

  return JSON.stringify({ bpm: bpm.value, notes }, null, 2)
}

const generateVsqx = (): string => {
  // 简化的 VSQX 格式
  let content = '<?xml version="1.0" encoding="utf-8"?>\n'
  content += '<vsQ version="2.0">\n'
  content += '<masterTrack>\n'
  content += `<tempo><t t="0">${bpm.value}</t></tempo>\n`
  content += '</masterTrack>\n'
  
  content += '<vsTrack type="1">\n'
  content += '<trackName>歌声合成轨道</trackName>\n'
  
  if (props.pitchData) {
    const framePeriod = 5 // ms
    for (let i = 0; i < Math.min(props.pitchData.length, 100); i++) {
      const frequency = props.pitchData[i]
      if (frequency > 0) {
        const midiNote = Math.round(12 * Math.log2(frequency / 440) + 69)
        content += '<note>\n'
        content += `<t>${i * framePeriod}</t>\n`
        content += `<duration>${framePeriod}</duration>\n`
        content += `<key>${midiNote}</key>\n`
        content += '<lyric>あ</lyric>\n'
        content += '</note>\n'
      }
    }
  }

  content += '</vsTrack>\n'
  content += '</vsQ>\n'

  return content
}

const downloadFile = (content: string, filename: string, mimeType: string) => {
  const blob = new Blob([content], { type: mimeType })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}
</script>

<style scoped>
.export-panel {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.1);
}

.panel-header {
  margin-bottom: 20px;
}

.panel-header h3 {
  margin: 0 0 8px 0;
  font-size: 16px;
  color: #333;
}

.hint {
  margin: 0;
  font-size: 12px;
  color: #999;
}

.export-section {
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid #eee;
}

.export-section h4 {
  margin: 0 0 12px 0;
  font-size: 13px;
  color: #333;
  font-weight: 500;
}

.export-buttons {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 8px;
}

.export-btn {
  padding: 10px 12px;
  border: 1px solid #ddd;
  background: white;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  transition: all 0.2s ease;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.export-btn:hover:not(:disabled) {
  border-color: #667eea;
  color: #667eea;
  background: #f0f4ff;
}

.export-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.lab-btn {
  background: #ffe8e8;
  border-color: #ffcccc;
  color: #ff6b6b;
}

.json-btn {
  background: #e8f5ff;
  border-color: #ccecff;
  color: #1890ff;
}

.ustx-btn {
  background: #f0e8ff;
  border-color: #e0ccff;
  color: #667eea;
}

.svp-btn {
  background: #e8ffe8;
  border-color: #ccffcc;
  color: #4caf50;
}

.vsqx-btn {
  background: #fff8e8;
  border-color: #ffe8cc;
  color: #ff9800;
}

.synthesis-options {
  margin-bottom: 12px;
}

.option-group {
  display: flex;
  gap: 12px;
}

.option-group label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #666;
}

.input-sm {
  width: 60px;
  padding: 4px 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 12px;
}

.export-progress {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: #f0f4ff;
  border-radius: 6px;
  color: #667eea;
  font-size: 13px;
  margin-bottom: 12px;
}

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid #ddd;
  border-top-color: #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.success-message {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #efe;
  border-left: 4px solid #4caf50;
  border-radius: 4px;
  color: #4caf50;
  font-size: 13px;
  margin-bottom: 12px;
}

.error-message {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #fee;
  border-left: 4px solid #f66;
  border-radius: 4px;
  color: #c33;
  font-size: 13px;
  margin-bottom: 12px;
}

.close-btn {
  background: none;
  border: none;
  color: inherit;
  cursor: pointer;
  font-size: 16px;
}
</style>

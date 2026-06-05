<template>
  <div class="waveform-viewer">
    <div class="viewer-header">
      <h3>📊 波形图</h3>
      <div class="controls">
        <button
          v-for="zoom in [0.5, 1, 2, 4]"
          :key="zoom"
          :class="['zoom-btn', { active: currentZoom === zoom }]"
          @click="currentZoom = zoom"
        >
          {{ zoom }}x
        </button>
      </div>
    </div>

    <div class="canvas-container">
      <canvas
        ref="waveformCanvas"
        class="waveform-canvas"
        :width="canvasWidth"
        :height="canvasHeight"
      ></canvas>
      <div class="canvas-overlay">
        <p v-if="!waveformData" class="placeholder">加载音频文件查看波形</p>
      </div>
    </div>

    <div v-if="waveformData" class="viewer-info">
      <div class="info-item">
        <span class="info-label">采样率:</span>
        <span class="info-value">{{ sampleRate }} Hz</span>
      </div>
      <div class="info-item">
        <span class="info-label">时长:</span>
        <span class="info-value">{{ formatDuration(duration) }}</span>
      </div>
      <div class="info-item">
        <span class="info-label">通道:</span>
        <span class="info-value">{{ isMonoAudio ? '单声道' : '立体声' }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'

const props = defineProps({
  waveformData: {
    type: Float32Array,
    required: false
  },
  pitchData: {
    type: Float32Array,
    required: false
  },
  sampleRate: {
    type: Number,
    default: 0
  }
})

const waveformCanvas = ref<HTMLCanvasElement>()
const currentZoom = ref(1)
const canvasWidth = ref(0)
const canvasHeight = ref(0)

const duration = ref(0)
const isMonoAudio = ref(true)

onMounted(() => {
  const container = waveformCanvas.value?.parentElement
  if (container) {
    canvasWidth.value = container.clientWidth
    canvasHeight.value = 200
  }
  drawWaveform()
})

watch([() => props.waveformData, () => currentZoom.value], () => {
  drawWaveform()
})

const drawWaveform = () => {
  if (!waveformCanvas.value || !props.waveformData) {
    drawEmptyCanvas()
    return
  }

  const canvas = waveformCanvas.value
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  const data = props.waveformData
  const width = canvas.width
  const height = canvas.height
  const centerY = height / 2

  // 计算时长
  duration.value = data.length / props.sampleRate

  // 清空画布
  ctx.fillStyle = '#fff'
  ctx.fillRect(0, 0, width, height)

  // 绘制中线
  ctx.strokeStyle = '#eee'
  ctx.lineWidth = 1
  ctx.beginPath()
  ctx.moveTo(0, centerY)
  ctx.lineTo(width, centerY)
  ctx.stroke()

  // 绘制波形
  const samplesToShow = Math.floor(data.length / currentZoom.value)
  const samplesPerPixel = samplesToShow / width

  ctx.strokeStyle = '#667eea'
  ctx.lineWidth = 1
  ctx.beginPath()

  for (let x = 0; x < width; x++) {
    const startSample = Math.floor(x * samplesPerPixel)
    const endSample = Math.floor((x + 1) * samplesPerPixel)

    let min = 0
    let max = 0

    for (let i = startSample; i < endSample && i < data.length; i++) {
      const sample = data[i]
      if (sample < min) min = sample
      if (sample > max) max = sample
    }

    const y1 = centerY - min * centerY * 0.9
    const y2 = centerY - max * centerY * 0.9

    if (x === 0) {
      ctx.moveTo(x, (y1 + y2) / 2)
    } else {
      ctx.lineTo(x, (y1 + y2) / 2)
    }
  }

  ctx.stroke()

  // 绘制音高曲线
  if (props.pitchData) {
    ctx.strokeStyle = '#ff6b6b'
    ctx.lineWidth = 2
    ctx.beginPath()

    const pitchSamplesToShow = Math.floor(props.pitchData.length / currentZoom.value)
    const pitchSamplesPerPixel = pitchSamplesToShow / width

    for (let x = 0; x < width; x++) {
      const pitchIndex = Math.floor(x * pitchSamplesPerPixel)
      if (pitchIndex < props.pitchData.length) {
        const frequency = props.pitchData[pitchIndex]
        if (frequency > 0) {
          const normalizedFreq = Math.min(frequency / 500, 1)
          const y = centerY - normalizedFreq * centerY * 0.8

          if (x === 0) {
            ctx.moveTo(x, y)
          } else {
            ctx.lineTo(x, y)
          }
        }
      }
    }

    ctx.stroke()
  }
}

const drawEmptyCanvas = () => {
  if (!waveformCanvas.value) return
  const ctx = waveformCanvas.value.getContext('2d')
  if (ctx) {
    ctx.fillStyle = '#f9f9f9'
    ctx.fillRect(0, 0, waveformCanvas.value.width, waveformCanvas.value.height)
  }
}

const formatDuration = (seconds: number): string => {
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = Math.floor(seconds % 60)

  if (hours > 0) {
    return `${hours}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`
  }
  return `${minutes}:${String(secs).padStart(2, '0')}`
}
</script>

<style scoped>
.waveform-viewer {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.1);
}

.viewer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.viewer-header h3 {
  margin: 0;
  font-size: 16px;
  color: #333;
}

.controls {
  display: flex;
  gap: 8px;
}

.zoom-btn {
  padding: 6px 12px;
  border: 1px solid #ddd;
  background: white;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.2s ease;
}

.zoom-btn.active {
  background: #667eea;
  color: white;
  border-color: #667eea;
}

.canvas-container {
  position: relative;
  border: 1px solid #eee;
  border-radius: 6px;
  overflow: hidden;
  margin-bottom: 16px;
  background: white;
}

.waveform-canvas {
  display: block;
  width: 100%;
  height: 200px;
}

.canvas-overlay {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  pointer-events: none;
}

.placeholder {
  margin: 0;
  color: #999;
  font-size: 14px;
}

.viewer-info {
  display: flex;
  gap: 24px;
  padding-top: 12px;
  border-top: 1px solid #eee;
  flex-wrap: wrap;
}

.info-item {
  display: flex;
  gap: 8px;
  align-items: center;
}

.info-label {
  font-size: 12px;
  color: #999;
  font-weight: 500;
}

.info-value {
  font-size: 12px;
  color: #333;
  font-weight: 600;
}
</style>

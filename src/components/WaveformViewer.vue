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

    <div ref="containerRef" class="canvas-container">
      <canvas ref="waveformCanvas" class="waveform-canvas" :height="180"></canvas>
      <div v-if="!waveformData" class="canvas-placeholder">
        <p>加载音频文件查看波形</p>
      </div>
    </div>

    <div v-if="waveformData" class="viewer-info">
      <div class="info-item">
        <span class="info-label">采样率:</span>
        <span class="info-value">{{ sampleRate ?? 0 }} Hz</span>
      </div>
      <div class="info-item">
        <span class="info-label">时长:</span>
        <span class="info-value">{{ formatDuration(duration ?? 0) }}</span>
      </div>
      <div class="info-item">
        <span class="info-label">帧数:</span>
        <span class="info-value">{{ waveformData.length.toLocaleString() }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
// FIX: Use TypeScript generic defineProps<Props>() instead of the options-API
// defineProps({ type: Float32Array }).
//
// With options-API style, Vue's runtime prop type resolves Float32Array through
// its own type registry, which in TypeScript 5.x creates a mismatch: the inferred
// type has `buffer: ArrayBuffer | SharedArrayBuffer` while Float32Array<ArrayBuffer>
// requires `buffer: ArrayBuffer`.
//
// With TypeScript generic style, Vue skips the runtime type coercion and lets
// TypeScript handle type-checking directly, so Float32Array matches correctly.
import { ref, watch, onMounted, onUnmounted, nextTick } from 'vue'

const props = withDefaults(defineProps<{
  waveformData?: Float32Array   // optional: parent uses `?? undefined` to convert null
  pitchData?: Float32Array
  sampleRate?: number
  duration?: number
}>(), {
  sampleRate: 0,
  duration: 0,
})

const waveformCanvas = ref<HTMLCanvasElement>()
const containerRef = ref<HTMLDivElement>()
const currentZoom = ref(1)

let resizeObserver: ResizeObserver | null = null

onMounted(async () => {
  await nextTick()
  fitCanvas()
  drawWaveform()

  if (containerRef.value) {
    resizeObserver = new ResizeObserver(() => {
      fitCanvas()
      drawWaveform()
    })
    resizeObserver.observe(containerRef.value)
  }
})

onUnmounted(() => {
  resizeObserver?.disconnect()
})

watch([() => props.waveformData, () => props.pitchData, () => currentZoom.value], () => {
  fitCanvas()
  drawWaveform()
})

function fitCanvas() {
  if (!waveformCanvas.value || !containerRef.value) return
  waveformCanvas.value.width = containerRef.value.clientWidth || 800
}

function drawWaveform() {
  if (!waveformCanvas.value) return
  const canvas = waveformCanvas.value
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  const width = canvas.width
  const height = canvas.height

  ctx.fillStyle = '#ffffff'
  ctx.fillRect(0, 0, width, height)

  if (!props.waveformData || props.waveformData.length === 0) {
    ctx.fillStyle = '#f9f9f9'
    ctx.fillRect(0, 0, width, height)
    return
  }

  const data = props.waveformData
  const centerY = height / 2

  // Center line
  ctx.strokeStyle = '#e2e8f0'
  ctx.lineWidth = 1
  ctx.beginPath()
  ctx.moveTo(0, centerY)
  ctx.lineTo(width, centerY)
  ctx.stroke()

  // Waveform
  const samplesToShow = Math.floor(data.length / currentZoom.value)
  const samplesPerPixel = samplesToShow / width

  ctx.strokeStyle = '#667eea'
  ctx.lineWidth = 1
  ctx.beginPath()

  for (let x = 0; x < width; x++) {
    const startSample = Math.floor(x * samplesPerPixel)
    const endSample = Math.min(Math.floor((x + 1) * samplesPerPixel), data.length)

    let min = 0, max = 0
    for (let i = startSample; i < endSample; i++) {
      if (data[i] < min) min = data[i]
      if (data[i] > max) max = data[i]
    }

    const y1 = centerY - max * centerY * 0.9
    const y2 = centerY - min * centerY * 0.9

    if (x === 0) {
      ctx.moveTo(x, centerY)
    }
    ctx.lineTo(x, y1)
    ctx.lineTo(x, y2)
  }
  ctx.stroke()

  // Pitch overlay
  if (props.pitchData && props.pitchData.length > 0) {
    const pitch = props.pitchData
    const pitchSamplesToShow = Math.floor(pitch.length / currentZoom.value)
    const pitchSamplesPerPixel = pitchSamplesToShow / width

    ctx.strokeStyle = 'rgba(255, 107, 107, 0.85)'
    ctx.lineWidth = 2
    ctx.beginPath()
    let moved = false

    for (let x = 0; x < width; x++) {
      const idx = Math.floor(x * pitchSamplesPerPixel)
      if (idx < pitch.length && pitch[idx] > 0) {
        const normalizedFreq = Math.min(pitch[idx] / 600, 1)
        const y = height - normalizedFreq * height * 0.85

        if (!moved) {
          ctx.moveTo(x, y)
          moved = true
        } else {
          ctx.lineTo(x, y)
        }
      } else {
        moved = false
      }
    }
    ctx.stroke()
  }
}

function formatDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
  return `${m}:${String(s).padStart(2, '0')}`
}
</script>

<style scoped>
.waveform-viewer {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
}

.viewer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.viewer-header h3 {
  margin: 0;
  font-size: 15px;
  color: #2d3748;
  font-weight: 600;
}

.controls {
  display: flex;
  gap: 6px;
}

.zoom-btn {
  padding: 5px 10px;
  border: 1px solid #e2e8f0;
  background: white;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  font-weight: 500;
  color: #718096;
  transition: all 0.15s ease;
}

.zoom-btn:hover { border-color: #667eea; color: #667eea; }
.zoom-btn.active { background: #667eea; color: white; border-color: #667eea; }

.canvas-container {
  position: relative;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  overflow: hidden;
  margin-bottom: 12px;
  background: white;
  min-height: 180px;
}

.waveform-canvas {
  display: block;
  width: 100%;
  height: 180px;
}

.canvas-placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f9f9f9;
  color: #a0aec0;
  font-size: 14px;
}

.canvas-placeholder p { margin: 0; }

.viewer-info {
  display: flex;
  gap: 24px;
  padding-top: 12px;
  border-top: 1px solid #f0f0f0;
  flex-wrap: wrap;
}

.info-item {
  display: flex;
  gap: 6px;
  align-items: center;
}

.info-label {
  font-size: 12px;
  color: #a0aec0;
  font-weight: 500;
}

.info-value {
  font-size: 12px;
  color: #2d3748;
  font-weight: 600;
}
</style>

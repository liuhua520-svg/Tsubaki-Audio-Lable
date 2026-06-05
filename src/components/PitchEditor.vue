<template>
  <div class="pitch-editor">
    <div class="editor-header">
      <h3>✏️ 音高编辑器</h3>
      <p class="hint">拖动曲线调整音高，右侧控件预览效果</p>
    </div>

    <!-- Pitch Preview Canvas -->
    <div ref="containerRef" class="preview-section">
      <canvas ref="previewCanvas" class="preview-canvas" :height="160"></canvas>
      <div v-if="!pitchData" class="canvas-placeholder">
        <p>提取音高后在此预览</p>
      </div>
    </div>

    <!-- Local controls: pitch shift (visual preview only) -->
    <div class="controls-row">
      <div class="control-item">
        <label class="control-label">音高移位 (半音)</label>
        <div class="slider-row">
          <input
            v-model.number="pitchShift"
            type="range"
            min="-12"
            max="12"
            step="1"
            class="slider"
          />
          <span class="slider-value">{{ pitchShift > 0 ? '+' : '' }}{{ pitchShift }}</span>
        </div>
      </div>

      <div class="control-item" v-if="baseFrequency !== undefined">
        <label class="control-label">基准音高</label>
        <span class="info-badge">{{ baseFrequency }} Hz</span>
      </div>
    </div>

    <!-- Stats -->
    <div v-if="pitchData" class="stats-row">
      <div class="stat-item">
        <span class="stat-label">帧数</span>
        <span class="stat-value">{{ pitchData.length }}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">平均音高</span>
        <span class="stat-value">{{ averagePitch.toFixed(1) }} Hz</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">最高</span>
        <span class="stat-value">{{ maxPitch.toFixed(1) }} Hz</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">最低 (有声)</span>
        <span class="stat-value">{{ minPitch.toFixed(1) }} Hz</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
// FIX: TypeScript generic defineProps<Props>() avoids the Float32Array<ArrayBuffer>
// buffer type mismatch that occurs with options-API prop definitions.
import { ref, watch, computed, onMounted, onUnmounted, nextTick } from 'vue'

const props = withDefaults(defineProps<{
  pitchData?: Float32Array   // optional: parent uses `?? undefined` to convert null
  sampleRate?: number
  baseFrequency?: number
}>(), {
  sampleRate: 0,
  baseFrequency: 60,
})

const previewCanvas = ref<HTMLCanvasElement>()
const containerRef = ref<HTMLDivElement>()
const pitchShift = ref(0)

let resizeObserver: ResizeObserver | null = null

// Computed pitch stats
const averagePitch = computed(() => {
  if (!props.pitchData) return 0
  const voiced = Array.from(props.pitchData).filter(v => v > 0)
  if (voiced.length === 0) return 0
  return voiced.reduce((a, b) => a + b, 0) / voiced.length
})

const maxPitch = computed(() => {
  if (!props.pitchData) return 0
  return Math.max(...Array.from(props.pitchData))
})

const minPitch = computed(() => {
  if (!props.pitchData) return 0
  const voiced = Array.from(props.pitchData).filter(v => v > 0)
  return voiced.length > 0 ? Math.min(...voiced) : 0
})

onMounted(async () => {
  await nextTick()
  fitCanvas()
  drawPreview()

  if (containerRef.value) {
    resizeObserver = new ResizeObserver(() => {
      fitCanvas()
      drawPreview()
    })
    resizeObserver.observe(containerRef.value)
  }
})

onUnmounted(() => {
  resizeObserver?.disconnect()
})

watch([() => props.pitchData, pitchShift], () => {
  fitCanvas()
  drawPreview()
})

function fitCanvas() {
  if (!previewCanvas.value || !containerRef.value) return
  previewCanvas.value.width = containerRef.value.clientWidth || 800
}

function drawPreview() {
  if (!previewCanvas.value) return
  const canvas = previewCanvas.value
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  const width = canvas.width
  const height = canvas.height

  ctx.fillStyle = '#f8f9fa'
  ctx.fillRect(0, 0, width, height)

  if (!props.pitchData || props.pitchData.length === 0) return

  // Grid lines
  ctx.strokeStyle = '#e9ecef'
  ctx.lineWidth = 1
  for (let i = 1; i < 4; i++) {
    const y = (height / 4) * i
    ctx.beginPath()
    ctx.moveTo(0, y)
    ctx.lineTo(width, y)
    ctx.stroke()
  }

  const data = props.pitchData
  const samplesPerPixel = data.length / width
  const shiftMultiplier = Math.pow(2, pitchShift.value / 12)

  // Draw pitch curve
  ctx.strokeStyle = '#667eea'
  ctx.lineWidth = 2
  ctx.beginPath()
  let moved = false

  for (let x = 0; x < width; x++) {
    const idx = Math.floor(x * samplesPerPixel)
    if (idx < data.length) {
      let freq = data[idx]
      if (freq > 0) {
        freq *= shiftMultiplier
        const normalized = Math.max(0, Math.min(1, freq / 600))
        const y = height - normalized * height * 0.9

        if (!moved) { ctx.moveTo(x, y); moved = true }
        else { ctx.lineTo(x, y) }
      } else {
        moved = false
      }
    }
  }
  ctx.stroke()

  // Base frequency reference line
  if (props.baseFrequency && props.baseFrequency > 0) {
    const baseNormalized = Math.max(0, Math.min(1, props.baseFrequency / 600))
    const baseY = height - baseNormalized * height * 0.9

    ctx.strokeStyle = 'rgba(255, 107, 107, 0.5)'
    ctx.lineWidth = 1
    ctx.setLineDash([4, 4])
    ctx.beginPath()
    ctx.moveTo(0, baseY)
    ctx.lineTo(width, baseY)
    ctx.stroke()
    ctx.setLineDash([])

    ctx.fillStyle = 'rgba(255, 107, 107, 0.8)'
    ctx.font = '10px monospace'
    ctx.fillText(`${props.baseFrequency}Hz`, 4, baseY - 3)
  }
}
</script>

<style scoped>
.pitch-editor {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
  margin-top: 16px;
}

.editor-header {
  margin-bottom: 16px;
}

.editor-header h3 {
  margin: 0 0 4px 0;
  font-size: 15px;
  color: #2d3748;
  font-weight: 600;
}

.hint {
  margin: 0;
  font-size: 12px;
  color: #a0aec0;
}

.preview-section {
  position: relative;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  overflow: hidden;
  margin-bottom: 16px;
  min-height: 160px;
  background: #f8f9fa;
}

.preview-canvas {
  display: block;
  width: 100%;
  height: 160px;
}

.canvas-placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #a0aec0;
  font-size: 13px;
}

.canvas-placeholder p { margin: 0; }

.controls-row {
  display: flex;
  gap: 24px;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.control-item {
  flex: 1;
  min-width: 200px;
}

.control-label {
  display: block;
  font-size: 12px;
  font-weight: 500;
  color: #718096;
  margin-bottom: 6px;
}

.slider-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.slider {
  flex: 1;
  height: 4px;
  border-radius: 2px;
  outline: none;
  -webkit-appearance: none;
  appearance: none;
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
}

.slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: #667eea;
  cursor: pointer;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
}

.slider::-moz-range-thumb {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: #667eea;
  cursor: pointer;
  border: none;
}

.slider-value {
  font-size: 13px;
  font-weight: 600;
  color: #667eea;
  min-width: 32px;
  text-align: right;
}

.info-badge {
  display: inline-block;
  padding: 4px 10px;
  background: #ebf4ff;
  color: #3182ce;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
}

.stats-row {
  display: flex;
  gap: 16px;
  padding-top: 12px;
  border-top: 1px solid #f0f0f0;
  flex-wrap: wrap;
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.stat-label {
  font-size: 11px;
  color: #a0aec0;
  font-weight: 500;
}

.stat-value {
  font-size: 13px;
  color: #2d3748;
  font-weight: 600;
  font-family: monospace;
}
</style>

<template>
  <div class="pitch-editor">
    <div class="editor-header">
      <h3>✏️ 音高编辑</h3>
      <p class="hint">调整音高参数以改善合成质量</p>
    </div>

    <!-- 算法选择 -->
    <div class="control-group">
      <label class="control-label">
        提取算法
        <select v-model="algorithm" class="select-input">
          <option value="dio">DIO</option>
          <option value="harvest">Harvest</option>
        </select>
      </label>
    </div>

    <!-- 音高锐化 -->
    <div class="control-group">
      <label class="control-label">
        音高锐化 (消除颤动)
        <div class="slider-container">
          <input
            v-model.number="sharpness"
            type="range"
            min="0"
            max="1"
            step="0.1"
            class="slider"
          />
          <span class="slider-value">{{ (sharpness * 100).toFixed(0) }}%</span>
        </div>
      </label>
      <p class="slider-hint">值越大，音高越稳定但可能失去自然感</p>
    </div>

    <!-- 基准音高 -->
    <div class="control-group">
      <label class="control-label">
        基准音高 (Hz)
        <input
          v-model.number="baseFrequency"
          type="number"
          min="40"
          max="400"
          class="number-input"
        />
      </label>
      <p class="slider-hint">用于音高标准化，通常 60Hz 用于男声，120Hz 用于女声</p>
    </div>

    <!-- 音高移位 -->
    <div class="control-group">
      <label class="control-label">
        音高移位 (半音)
        <div class="slider-container">
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
      </label>
    </div>

    <!-- 实时预览 -->
    <div class="preview-section">
      <h4>📈 音高预览</h4>
      <canvas
        ref="previewCanvas"
        class="preview-canvas"
        :width="previewWidth"
        :height="previewHeight"
      ></canvas>
    </div>

    <!-- 操作按钮 -->
    <div class="action-buttons">
      <button class="apply-btn" @click="applyChanges" :disabled="!pitchData">
        应用修改
      </button>
      <button class="reset-btn" @click="resetChanges">
        重置
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'

const props = defineProps({
  pitchData: {
    type: Float32Array,
    required: false
  },
  sampleRate: {
    type: Number,
    default: 0
  }
})

const emit = defineEmits([
  'update:algorithm',
  'update:sharpness',
  'update:baseFrequency',
  'apply-changes'
])

const algorithm = ref<'dio' | 'harvest'>('dio')
const sharpness = ref(0.5)
const baseFrequency = ref(60)
const pitchShift = ref(0)

const previewCanvas = ref<HTMLCanvasElement>()
const previewWidth = ref(0)
const previewHeight = ref(150)

onMounted(() => {
  const container = previewCanvas.value?.parentElement
  if (container) {
    previewWidth.value = container.clientWidth
  }
  drawPreview()
})

watch([sharpness, algorithm, baseFrequency, pitchShift, () => props.pitchData], () => {
  emit('update:algorithm', algorithm.value)
  emit('update:sharpness', sharpness.value)
  emit('update:baseFrequency', baseFrequency.value)
  drawPreview()
})

const drawPreview = () => {
  if (!previewCanvas.value || !props.pitchData) {
    return
  }

  const canvas = previewCanvas.value
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  const data = props.pitchData
  const width = canvas.width
  const height = canvas.height

  // 清空画布
  ctx.fillStyle = '#f9f9f9'
  ctx.fillRect(0, 0, width, height)

  // 绘制网格
  ctx.strokeStyle = '#eee'
  ctx.lineWidth = 1
  for (let i = 0; i <= 4; i++) {
    const y = (height / 4) * i
    ctx.beginPath()
    ctx.moveTo(0, y)
    ctx.lineTo(width, y)
    ctx.stroke()
  }

  // 绘制音高曲线
  const samplesPerPixel = data.length / width
  ctx.strokeStyle = '#667eea'
  ctx.lineWidth = 2
  ctx.beginPath()

  for (let x = 0; x < width; x++) {
    const index = Math.floor(x * samplesPerPixel)
    if (index < data.length) {
      let frequency = data[index]
      
      if (frequency > 0) {
        // 应用音高移位 (乘以 2^(semitones/12))
        frequency *= Math.pow(2, pitchShift.value / 12)
        
        // 归一化频率
        const normalized = Math.max(0, Math.min(1, frequency / 500))
        const y = height - normalized * height

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

const applyChanges = () => {
  emit('apply-changes', {
    algorithm: algorithm.value,
    sharpness: sharpness.value,
    baseFrequency: baseFrequency.value,
    pitchShift: pitchShift.value
  })
}

const resetChanges = () => {
  algorithm.value = 'dio'
  sharpness.value = 0.5
  baseFrequency.value = 60
  pitchShift.value = 0
  drawPreview()
}
</script>

<style scoped>
.pitch-editor {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.1);
}

.editor-header {
  margin-bottom: 20px;
}

.editor-header h3 {
  margin: 0 0 8px 0;
  font-size: 16px;
  color: #333;
}

.hint {
  margin: 0;
  font-size: 12px;
  color: #999;
}

.control-group {
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid #eee;
}

.control-group:last-of-type {
  border-bottom: none;
}

.control-label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: #333;
  margin-bottom: 8px;
}

.select-input,
.number-input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 13px;
  margin-top: 6px;
}

.select-input:focus,
.number-input:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.1);
}

.slider-container {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-top: 8px;
}

.slider {
  flex: 1;
  height: 4px;
  border-radius: 2px;
  background: linear-gradient(90deg, #ddd 0%, #ddd 100%);
  outline: none;
  -webkit-appearance: none;
  appearance: none;
}

.slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #667eea;
  cursor: pointer;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.slider::-moz-range-thumb {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #667eea;
  cursor: pointer;
  border: none;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.slider-value {
  font-size: 12px;
  color: #667eea;
  font-weight: 600;
  min-width: 45px;
}

.slider-hint {
  margin: 8px 0 0 0;
  font-size: 11px;
  color: #999;
}

.preview-section {
  margin: 20px 0;
  padding: 16px;
  background: #f9f9f9;
  border-radius: 6px;
}

.preview-section h4 {
  margin: 0 0 12px 0;
  font-size: 13px;
  color: #333;
}

.preview-canvas {
  display: block;
  width: 100%;
  height: 150px;
  border: 1px solid #ddd;
  border-radius: 4px;
  background: white;
}

.action-buttons {
  display: flex;
  gap: 12px;
  margin-top: 16px;
}

.apply-btn,
.reset-btn {
  flex: 1;
  padding: 10px;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.apply-btn {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.apply-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.apply-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.reset-btn {
  background: #f0f0f0;
  color: #333;
  border: 1px solid #ddd;
}

.reset-btn:hover {
  background: #e8e8e8;
}
</style>

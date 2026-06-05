<template>
  <div class="pitch-extractor">
    <div class="extractor-header">
      <h3>🎼 音高提取</h3>
      <p class="hint">选择算法提取音频的基频轨迹</p>
    </div>

    <div class="algorithm-selector">
      <label>
        <input type="radio" value="dio" v-model="selectedAlgorithm" :disabled="isExtracting" />
        <span>DIO (快速)</span>
      </label>
      <label>
        <input type="radio" value="harvest" v-model="selectedAlgorithm" :disabled="isExtracting" />
        <span>Harvest (高质量)</span>
      </label>
    </div>

    <button
      class="extract-btn"
      @click="extractPitch"
      :disabled="!waveformData || isExtracting"
    >
      <span v-if="!isExtracting">提取音高</span>
      <span v-else>处理中 {{ extractProgress }}%</span>
    </button>

    <div v-if="extractProgress > 0 && isExtracting" class="progress-bar">
      <div class="progress" :style="{ width: extractProgress + '%' }"></div>
    </div>

    <div v-if="error" class="error-message">
      <span>⚠️ {{ error }}</span>
      <button class="close-btn" @click="error = ''">✕</button>
    </div>

    <div v-if="pitchData" class="success-message">
      <span>✓ 音高提取成功！</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps({
  waveformData: {
    type: Float32Array,
    required: false
  },
  sampleRate: {
    type: Number,
    default: 0
  }
})

const emit = defineEmits(['pitch-extracted', 'error'])

const selectedAlgorithm = ref<'dio' | 'harvest'>('dio')
const isExtracting = ref(false)
const extractProgress = ref(0)
const error = ref('')
const pitchData = ref<Float32Array | null>(null)

const extractPitch = async () => {
  if (!props.waveformData || props.sampleRate === 0) {
    error.value = '请先加载音频文件'
    return
  }

  isExtracting.value = true
  extractProgress.value = 0
  error.value = ''

  try {
    const progressInterval = setInterval(() => {
      extractProgress.value = Math.min(extractProgress.value + Math.random() * 30, 90)
    }, 500)

    const endpoint = selectedAlgorithm.value === 'dio' ? '/pyworld/dio' : '/pyworld/harvest'
    
    const response = await fetch(endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/octet-stream'
      },
      body: props.waveformData.buffer
    })

    clearInterval(progressInterval)
    extractProgress.value = 100

    if (!response.ok) {
      throw new Error(`音高提取失败: ${response.statusText}`)
    }

    const buffer = await response.arrayBuffer()
    const data = JSON.parse(new TextDecoder().decode(buffer))
    
    pitchData.value = new Float32Array(data.f0.buffer)
    emit('pitch-extracted', pitchData.value)

    setTimeout(() => {
      extractProgress.value = 0
    }, 1000)
  } catch (err) {
    error.value = err instanceof Error ? err.message : '未知错误'
    emit('error', error.value)
  } finally {
    isExtracting.value = false
  }
}
</script>

<style scoped>
.pitch-extractor {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.1);
}

.extractor-header {
  margin-bottom: 16px;
}

.extractor-header h3 {
  margin: 0 0 8px 0;
  font-size: 16px;
  color: #333;
}

.hint {
  margin: 0;
  font-size: 12px;
  color: #999;
}

.algorithm-selector {
  display: flex;
  gap: 20px;
  margin-bottom: 16px;
}

.algorithm-selector label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-size: 14px;
}

.algorithm-selector input[type='radio'] {
  cursor: pointer;
}

.algorithm-selector input[type='radio']:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.extract-btn {
  width: 100%;
  padding: 12px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.3s ease;
  margin-bottom: 12px;
}

.extract-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.extract-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.progress-bar {
  width: 100%;
  height: 4px;
  background: #eee;
  border-radius: 2px;
  overflow: hidden;
  margin-bottom: 12px;
}

.progress {
  height: 100%;
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
  transition: width 0.3s ease;
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
  color: #c33;
  cursor: pointer;
  font-size: 16px;
}

.success-message {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  background: #efe;
  border-left: 4px solid #4caf50;
  border-radius: 4px;
  color: #4caf50;
  font-size: 13px;
}
</style>

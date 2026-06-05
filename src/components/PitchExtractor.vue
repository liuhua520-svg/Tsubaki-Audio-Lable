<template>
  <div class="pitch-extractor">
    <div class="extractor-header">
      <h3>🎼 音高提取控制台</h3>
      <p class="hint">选择算法并配置参数，由后端 PyWorld 完成提取</p>
    </div>

    <!-- Algorithm selector -->
    <div class="section">
      <label class="section-label">提取算法</label>
      <div class="radio-group">
        <label class="radio-option" :class="{ active: algorithm === 'dio' }">
          <input
            type="radio"
            value="dio"
            :checked="algorithm === 'dio'"
            :disabled="isProcessing"
            @change="$emit('update:algorithm', 'dio')"
          />
          <span class="radio-title">DIO</span>
          <span class="radio-desc">快速，适合实时处理</span>
        </label>
        <label class="radio-option" :class="{ active: algorithm === 'harvest' }">
          <input
            type="radio"
            value="harvest"
            :checked="algorithm === 'harvest'"
            :disabled="isProcessing"
            @change="$emit('update:algorithm', 'harvest')"
          />
          <span class="radio-title">Harvest</span>
          <span class="radio-desc">高质量，适合精确分析</span>
        </label>
      </div>
    </div>

    <!-- Sharpness slider -->
    <div class="section">
      <label class="section-label">
        音高锐化 (消除颤动)
        <span class="section-value">{{ Math.round(sharpness * 100) }}%</span>
      </label>
      <input
        type="range"
        min="0"
        max="1"
        step="0.05"
        :value="sharpness"
        :disabled="isProcessing"
        class="slider"
        @input="$emit('update:sharpness', +($event.target as HTMLInputElement).value)"
      />
      <p class="section-hint">值越大音高越稳定，但可能失去自然颤音</p>
    </div>

    <!-- Base frequency -->
    <div class="section">
      <label class="section-label">
        基准音高 (Hz)
        <span class="section-hint-inline">男声 ~60Hz，女声 ~120Hz</span>
      </label>
      <input
        type="number"
        min="40"
        max="400"
        :value="baseFrequency"
        :disabled="isProcessing"
        class="number-input"
        @change="$emit('update:baseFrequency', +($event.target as HTMLInputElement).value)"
      />
    </div>

    <!-- Action buttons -->
    <div class="actions">
      <button
        class="btn btn-primary"
        :disabled="!audioLoaded || isProcessing"
        @click="$emit('extract-pitch')"
      >
        <span v-if="isProcessing" class="btn-spinner"></span>
        <span v-else>🎯</span>
        {{ isProcessing ? '提取中...' : '提取音高' }}
      </button>

      <button
        class="btn btn-secondary"
        :disabled="!pitchExtracted || isProcessing"
        @click="$emit('sharpen-pitch')"
      >
        ✨ 音高锐化
      </button>

      <button
        class="btn btn-ghost"
        :disabled="!pitchExtracted || isProcessing"
        @click="$emit('undo')"
      >
        ↩ 撤销
      </button>
    </div>

    <!-- Status -->
    <div v-if="!audioLoaded" class="status-hint">
      <span class="status-icon">ℹ️</span> 请先在「波形图」标签页上传音频文件
    </div>
    <div v-else-if="pitchExtracted && !isProcessing" class="status-success">
      <span class="status-icon">✓</span> 音高已提取，可在下方编辑器查看
    </div>
  </div>
</template>

<script setup lang="ts">
// This component is a pure UI control panel.
// All actual pitch extraction logic lives in App.vue; this component only emits events.
// Props match exactly what App.vue passes; emits match what App.vue listens for.

defineProps<{
  audioLoaded: boolean
  pitchExtracted: boolean
  algorithm: 'dio' | 'harvest'
  sharpness: number
  baseFrequency: number
  isProcessing: boolean
}>()

defineEmits<{
  'extract-pitch': []
  'sharpen-pitch': []
  'undo': []
  'update:algorithm': [value: string]
  'update:sharpness': [value: number]
  'update:baseFrequency': [value: number]
}>()
</script>

<style scoped>
.pitch-extractor {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
  margin-bottom: 16px;
}

.extractor-header {
  margin-bottom: 20px;
}

.extractor-header h3 {
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

.section {
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid #f0f0f0;
}

.section:last-of-type {
  border-bottom: none;
}

.section-label {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
  font-weight: 600;
  color: #4a5568;
  margin-bottom: 10px;
}

.section-value {
  font-size: 13px;
  font-weight: 700;
  color: #667eea;
}

.section-hint {
  margin: 6px 0 0;
  font-size: 11px;
  color: #a0aec0;
}

.section-hint-inline {
  font-size: 11px;
  color: #a0aec0;
  font-weight: 400;
}

/* Radio group */
.radio-group {
  display: flex;
  gap: 10px;
}

.radio-option {
  flex: 1;
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 12px;
  border: 2px solid #e2e8f0;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s ease;
  position: relative;
}

.radio-option input {
  margin-top: 2px;
  cursor: pointer;
  accent-color: #667eea;
}

.radio-option input:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.radio-option.active {
  border-color: #667eea;
  background: #f0f3ff;
}

.radio-title {
  font-size: 13px;
  font-weight: 600;
  color: #2d3748;
  display: block;
}

.radio-desc {
  font-size: 11px;
  color: #a0aec0;
  display: block;
}

/* Slider */
.slider {
  width: 100%;
  height: 4px;
  border-radius: 2px;
  outline: none;
  -webkit-appearance: none;
  appearance: none;
  background: #e2e8f0;
  cursor: pointer;
}

.slider:disabled { cursor: not-allowed; opacity: 0.5; }

.slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #667eea;
  cursor: pointer;
  box-shadow: 0 1px 4px rgba(102, 126, 234, 0.4);
}

.slider::-moz-range-thumb {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #667eea;
  cursor: pointer;
  border: none;
}

/* Number input */
.number-input {
  width: 120px;
  padding: 8px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  font-size: 14px;
  color: #2d3748;
  transition: border-color 0.15s;
}

.number-input:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.number-input:disabled { opacity: 0.5; cursor: not-allowed; }

/* Actions */
.actions {
  display: flex;
  gap: 10px;
  margin-top: 4px;
  flex-wrap: wrap;
}

.btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 10px 16px;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.btn:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  flex: 1;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.btn-secondary {
  background: #ebf4ff;
  color: #3182ce;
  border: 1px solid #bee3f8;
}

.btn-secondary:hover:not(:disabled) { background: #bee3f8; }

.btn-ghost {
  background: #f7fafc;
  color: #718096;
  border: 1px solid #e2e8f0;
}

.btn-ghost:hover:not(:disabled) { background: #edf2f7; }

.btn-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.4);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

/* Status messages */
.status-hint,
.status-success {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border-radius: 6px;
  font-size: 12px;
  margin-top: 12px;
}

.status-hint {
  background: #fffbeb;
  color: #92400e;
  border: 1px solid #fde68a;
}

.status-success {
  background: #f0fff4;
  color: #276749;
  border: 1px solid #9ae6b4;
}

.status-icon { font-size: 14px; }
</style>

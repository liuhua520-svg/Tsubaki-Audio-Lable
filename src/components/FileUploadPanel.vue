<template>
  <div class="file-upload-panel">
    <div class="upload-header">
      <h3>📁 单音频与单 LAB 资产配对管理器</h3>
      <p class="hint">无文件限制。请导入【1个音频】与【1个 .lab 文件】以解锁音高对齐系统。</p>
    </div>

    <div 
      class="upload-area" 
      :class="{ dragging: dragover }"
      @dragover.prevent="dragover = true" 
      @dragleave.prevent="dragover = false" 
      @drop.prevent="handleDrop"
      @click="triggerFileInput"
    >
      <div class="upload-content">
        <div class="upload-icon">📥</div>
        <p class="upload-text">拖放或点击导入：1个音频 (WAV/MP3/FLAC) 及 1个对齐 LAB 文件</p>
        <p class="upload-subtext">重复拖入会直接覆盖更新对应类型的文件</p>
        <input
          ref="fileInput"
          type="file"
          multiple
          accept=".wav,.mp3,.flac,.lab"
          style="display: none"
          @change="handleFileSelect"
        />
      </div>
    </div>

    <div class="status-board">
      <h4>📦 工作区当前配对进度：</h4>
      <div class="asset-list">
        <div class="asset-item" :class="{ ready: currentAudio }">
          <span class="icon">{{ currentAudio ? '🎵' : '⭕' }}</span>
          <div class="info">
            <p class="name">{{ currentAudio ? currentAudio.name : '等待载入音频文件...' }}</p>
            <p class="type">格式需求: wav, flac, mp3</p>
          </div>
        </div>
        <div class="asset-item" :class="{ ready: currentLab }">
          <span class="icon">{{ currentLab ? '📄' : '⭕' }}</span>
          <div class="info">
            <p class="name">{{ currentLab ? currentLab.name : '等待载入匹配的 .lab 文件...' }}</p>
            <p class="type">格式需求: 纯文本对齐标签</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

defineProps<{
  isProcessing: boolean
}>()

const emit = defineEmits<{
  (e: 'upload-audio', file: File): void
  (e: 'upload-lab', file: File): void
}>()

const fileInput = ref<HTMLInputElement | null>(null)
const dragover = ref(false)

const currentAudio = ref<File | null>(null)
const currentLab = ref<File | null>(null)

function triggerFileInput() {
  fileInput.value?.click()
}

// 核心过滤算法：每次操作时只提取符合条件的“单音频”或“单LAB”
function filterAndCommitFiles(files: FileList) {
  for (let i = 0; i < files.length; i++) {
    const file = files[i]
    const ext = file.name.split('.').pop()?.toLowerCase()

    if (ext === 'lab') {
      currentLab.value = file
      emit('upload-lab', file)
    } else if (['wav', 'mp3', 'flac'].includes(ext || '')) {
      currentAudio.value = file
      emit('upload-audio', file)
    }
  }
}

function handleFileSelect(e: Event) {
  const target = e.target as HTMLInputElement
  if (target.files && target.files.length > 0) {
    filterAndCommitFiles(target.files)
  }
}

function handleDrop(e: DragEvent) {
  dragover.value = false
  if (e.dataTransfer && e.dataTransfer.files.length > 0) {
    filterAndCommitFiles(e.dataTransfer.files)
  }
}
</script>

<style scoped>
.file-upload-panel {
  background: #ffffff;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 20px;
}
.upload-header h3 { margin: 0 0 4px 0; color: #2d3748; font-size: 16px; }
.hint { font-size: 12px; color: #718096; margin: 0 0 16px 0; }

.upload-area {
  border: 2px dashed #e2e8f0;
  border-radius: 8px;
  padding: 36px 16px;
  text-align: center;
  background: #f7fafc;
  cursor: pointer;
  transition: all 0.2s ease;
}
.upload-area:hover, .upload-area.dragging {
  border-color: #2d3748;
  background: #edf2f7;
}

.upload-icon { font-size: 32px; margin-bottom: 8px; }
.upload-text { font-size: 14px; font-weight: 600; color: #2d3748; margin: 0 0 4px 0; }
.upload-subtext { font-size: 12px; color: #718096; margin: 0; }

.status-board {
  margin-top: 20px;
  padding: 16px;
  background: #f7fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
}
.status-board h4 { margin: 0 0 12px 0; font-size: 13px; color: #2d3748; }

.asset-list { display: flex; gap: 16px; flex-wrap: wrap; }
.asset-item {
  flex: 1;
  min-width: 240px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  transition: all 0.2s ease;
}
.asset-item.ready {
  border-color: #cbd5e0;
  background: #edf2f7;
}
.asset-item .icon { font-size: 18px; }
.asset-item .name { margin: 0; font-size: 13px; font-weight: 600; color: #4a5568; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 240px; }
.asset-item .type { margin: 2px 0 0 0; font-size: 11px; color: #a0aec0; }
</style>
<template>
  <div class="file-upload-panel">
    <div class="upload-header">
      <h3>📁 文件管理</h3>
      <p class="hint">支持上传 WAV, MP3, FLAC, OGG 格式 (最大 500MB)</p>
    </div>

    <div class="upload-area" @dragover="dragover = true" @dragleave="dragover = false" @drop="handleDrop">
      <div class="upload-content" :class="{ dragging: dragover }">
        <div class="upload-icon">📤</div>
        <p class="upload-text">将音频文件拖放到此处</p>
        <p class="upload-subtext">或点击选择文件</p>
        <input
          ref="fileInput"
          type="file"
          multiple
          accept=".wav,.mp3,.flac,.ogg"
          style="display: none"
          @change="handleFileSelect"
        />
        <button class="upload-btn" @click="(fileInput as HTMLInputElement)?.click()">选择音频文件</button>
      </div>
    </div>

    <!-- 文件列表 -->
    <div v-if="audioFiles.length > 0" class="files-list">
      <div class="list-header">
        <h4>已加载文件 ({{ audioFiles.length }})</h4>
        <button v-if="audioFiles.length > 1" class="clear-btn" @click="clearAll">清空全部</button>
      </div>

      <div v-for="(file, index) in audioFiles" :key="index" class="file-item">
        <div class="file-info">
          <span class="file-icon">🎵</span>
          <div class="file-details">
            <p class="file-name">{{ file.name }}</p>
            <p class="file-meta">{{ formatFileSize(file.size) }} • {{ file.format }}</p>
          </div>
        </div>
        <button v-if="audioFiles.length > 1" class="remove-btn" @click="removeFile(index)">✕</button>
        <button v-else class="select-btn" @click="selectFile(file)">选择</button>
      </div>
    </div>

    <!-- Lab 文件导入 -->
    <div class="lab-import-section">
      <h4>🏷️ 导入 Lab 文件 (可选)</h4>
      <div class="lab-upload-area">
        <input
          ref="labInput"
          type="file"
          accept=".lab"
          style="display: none"
          @change="handleLabSelect"
        />
        <button class="lab-upload-btn" @click="(labInput as HTMLInputElement)?.click()">选择 Lab 标注文件</button>
        <p v-if="labFile" class="lab-status">✓ 已加载: {{ labFile.name }}</p>
      </div>
    </div>

    <!-- 错误提示 -->
    <div v-if="error" class="error-message">
      <span class="error-icon">⚠️</span>
      <span>{{ error }}</span>
      <button class="error-close" @click="error = ''">✕</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

interface AudioFile {
  file: File
  name: string
  size: number
  format: string
}

const emit = defineEmits<{
  'upload-audio': [file: File]
  'upload-lab': [file: File]
  'files-loaded': [files: AudioFile[]]
}>()

const dragover = ref(false)
const audioFiles = ref<AudioFile[]>([])
const labFile = ref<File | null>(null)
const error = ref('')
const fileInput = ref<HTMLInputElement>()
const labInput = ref<HTMLInputElement>()

const handleDrop = (e: DragEvent) => {
  dragover.value = false
  e.preventDefault()
  const files = e.dataTransfer?.files
  if (files) {
    processFiles(files)
  }
}

const handleFileSelect = (e: Event) => {
  const files = (e.target as HTMLInputElement).files
  if (files) {
    processFiles(files)
  }
}

const processFiles = (files: FileList) => {
  error.value = ''
  
  for (let i = 0; i < files.length; i++) {
    const file = files[i]
    
    // 验证文件大小 (500MB)
    if (file.size > 500 * 1024 * 1024) {
      error.value = `文件 ${file.name} 过大 (最大 500MB)`
      continue
    }

    // 验证文件格式
    const ext = file.name.split('.').pop()?.toLowerCase()
    if (!['wav', 'mp3', 'flac', 'ogg'].includes(ext || '')) {
      error.value = `不支持的格式: ${ext}`
      continue
    }

    audioFiles.value.push({
      file,
      name: file.name,
      size: file.size,
      format: ext?.toUpperCase() || 'UNKNOWN'
    })

    // Emit file selected for single file
    emit('upload-audio', file)
  }

  emit('files-loaded', audioFiles.value)
}

const handleLabSelect = (e: Event) => {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (file) {
    if (!file.name.endsWith('.lab')) {
      error.value = '请选择 .lab 文件'
      return
    }
    labFile.value = file
    emit('upload-lab', file)
  }
}

const selectFile = (file: AudioFile) => {
  emit('upload-audio', file.file)
}

const removeFile = (index: number) => {
  audioFiles.value.splice(index, 1)
}

const clearAll = () => {
  audioFiles.value = []
  labFile.value = null
}

const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}
</script>

<style scoped>
.file-upload-panel {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.1);
  margin-bottom: 20px;
}

.upload-header {
  margin-bottom: 20px;
}

.upload-header h3 {
  margin: 0 0 8px 0;
  font-size: 16px;
  color: #333;
}

.hint {
  margin: 0;
  font-size: 12px;
  color: #999;
}

.upload-area {
  border: 2px dashed #ddd;
  border-radius: 8px;
  padding: 40px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
  margin-bottom: 20px;
}

.upload-area:hover {
  border-color: #667eea;
}

.upload-area.dragging {
  border-color: #667eea;
  background: #f0f4ff;
}

.upload-content {
  pointer-events: none;
}

.upload-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

.upload-text {
  margin: 0 0 4px 0;
  font-size: 14px;
  font-weight: 600;
  color: #333;
}

.upload-subtext {
  margin: 0 0 16px 0;
  font-size: 12px;
  color: #999;
}

.upload-btn {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  padding: 10px 24px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  pointer-events: auto;
  transition: transform 0.2s ease;
}

.upload-btn:hover {
  transform: translateY(-2px);
}

.files-list {
  margin-bottom: 20px;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.list-header h4 {
  margin: 0;
  font-size: 14px;
  color: #333;
}

.clear-btn {
  background: none;
  border: none;
  color: #999;
  cursor: pointer;
  font-size: 12px;
  text-decoration: underline;
}

.file-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: #f9f9f9;
  border-radius: 6px;
  margin-bottom: 8px;
}

.file-info {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
}

.file-icon {
  font-size: 20px;
}

.file-details {
  text-align: left;
}

.file-name {
  margin: 0;
  font-size: 13px;
  font-weight: 500;
  color: #333;
}

.file-meta {
  margin: 4px 0 0 0;
  font-size: 12px;
  color: #999;
}

.remove-btn,
.select-btn {
  background: none;
  border: none;
  color: #667eea;
  cursor: pointer;
  font-size: 14px;
  padding: 4px 8px;
  transition: color 0.2s ease;
}

.remove-btn:hover {
  color: #f66;
}

.select-btn:hover {
  color: #764ba2;
}

.lab-import-section {
  border-top: 1px solid #eee;
  padding-top: 16px;
  margin-top: 16px;
}

.lab-import-section h4 {
  margin: 0 0 12px 0;
  font-size: 14px;
  color: #333;
}

.lab-upload-area {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.lab-upload-btn {
  background: #f0f0f0;
  border: 1px solid #ddd;
  padding: 10px 16px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  transition: background 0.2s ease;
}

.lab-upload-btn:hover {
  background: #e8e8e8;
}

.lab-status {
  margin: 0;
  font-size: 12px;
  color: #4caf50;
}

.error-message {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: #fee;
  border-left: 4px solid #f66;
  border-radius: 4px;
  color: #c33;
  margin-top: 16px;
}

.error-icon {
  font-size: 16px;
}

.error-close {
  margin-left: auto;
  background: none;
  border: none;
  color: #c33;
  cursor: pointer;
  font-size: 18px;
}
</style>
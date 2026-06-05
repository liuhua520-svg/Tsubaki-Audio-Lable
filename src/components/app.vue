<template>
  <div class="app-container">
    <header class="app-header">
      <h1>Tsubaki Audio Label</h1>
      <p>音频处理工作室</p>
    </header>
    <main class="app-main">
      <section class="info-section">
        <h2>欢迎使用</h2>
        <p>一个现代化的音频处理工作室，用于标注文件和音高的合并处理。</p>
        <div class="features">
          <div class="feature-card">
            <h3>📁 Lab 文件导入</h3>
            <p>支持来自 GPT-SoVITS MFA Aligner 的音素对齐标注文件</p>
          </div>
          <div class="feature-card">
            <h3>🎵 音频处理</h3>
            <p>支持多种音频格式，提供高质量基频提取</p>
          </div>
          <div class="feature-card">
            <h3>📊 可视化分析</h3>
            <p>生成音频分析图表，直观查看处理结果</p>
          </div>
        </div>
      </section>
      
      <section class="status-section">
        <h2>系统状态</h2>
        <div v-if="env" class="env-info">
          <p><strong>后端：</strong> {{ env.backend || 'Python' }}</p>
          <p><strong>Python 路径：</strong> {{ env.python }}</p>
          <p><strong>基础 URL：</strong> {{ env.baseURL }}</p>
        </div>
        <div v-else class="loading">
          正在加载系统信息...
        </div>
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

interface Props {
  backend: string
  baseURL: string
  'onMount:app'?: (value: any) => void
}

const props = withDefaults(defineProps<Props>(), {
  backend: '',
  baseURL: '/'
})

const env = ref<any>(null)

onMounted(async () => {
  try {
    const response = await fetch(`${props.baseURL}env`)
    const data = await response.json()
    env.value = {
      ...data,
      backend: props.backend,
      python: data.executable
    }
  } catch (error) {
    console.error('Failed to fetch environment info:', error)
    env.value = {
      backend: props.backend,
      python: '无法连接到后端',
      baseURL: props.baseURL
    }
  }

  // Call the onMount callback if provided
  if (props['onMount:app']) {
    props['onMount:app'](this)
  }
})
</script>

<style scoped>
.app-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #333;
}

.app-header {
  background: rgba(255, 255, 255, 0.95);
  padding: 2rem;
  text-align: center;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.app-header h1 {
  margin: 0;
  color: #667eea;
  font-size: 2.5rem;
  font-weight: 700;
}

.app-header p {
  margin: 0.5rem 0 0 0;
  color: #666;
  font-size: 1rem;
}

.app-main {
  flex: 1;
  padding: 2rem;
  max-width: 1200px;
  margin: 0 auto;
  width: 100%;
}

.info-section,
.status-section {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 12px;
  padding: 2rem;
  margin-bottom: 2rem;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.info-section h2,
.status-section h2 {
  color: #667eea;
  margin-top: 0;
  font-size: 1.8rem;
}

.features {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
  margin-top: 1.5rem;
}

.feature-card {
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  border-radius: 8px;
  padding: 1.5rem;
  border-left: 4px solid #667eea;
}

.feature-card h3 {
  margin: 0 0 0.5rem 0;
  color: #667eea;
}

.feature-card p {
  margin: 0;
  color: #555;
  font-size: 0.95rem;
}

.env-info {
  background: #f5f7fa;
  border-radius: 8px;
  padding: 1.5rem;
  font-family: monospace;
  font-size: 0.9rem;
}

.env-info p {
  margin: 0.5rem 0;
  color: #555;
}

.loading {
  text-align: center;
  color: #999;
  font-style: italic;
  padding: 2rem;
}

@media (max-width: 768px) {
  .app-header h1 {
    font-size: 1.8rem;
  }

  .app-main {
    padding: 1rem;
  }

  .info-section,
  .status-section {
    padding: 1.5rem;
  }

  .features {
    grid-template-columns: 1fr;
  }
}
</style>

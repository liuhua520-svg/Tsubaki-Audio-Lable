# Tsubaki Audio Lable

一个现代化的音频处理工作室，用于标注文件和音高的合并处理，生成音乐记谱软件工程文件。

## 功能特性

### 输入支持
- **Lab 文件**: 来自 GPT-SoVITS MFA Aligner 的音素对齐标注文件 (`.lab`)
- **音频格式**: WAV、FLAC、MP3 等多种音频格式
- **大文件支持**: 支持处理大型或长时间音频文件而不失败

### 输出支持
- **Synthesizer V Studio** 工程文件
- **OpenUtau** 工程文件
- **USTX** 格式 (Utau Studio Extended)
- **SVP** 格式 (Synthesizer V Project)
- **VSQX** 格式 (Vocaloid)

### 高级功能
- **音高提取**: 使用 WORLD 声码器进行高质量基频 (F0) 估计
- **音高锐化**: 去除音高抖动和颤动现象
- **音频处理**: 支持音频分析、操作和合成

## 技术栈

- **前端**: Vue 3 + TypeScript
- **后端**: Python (Flask)
- **音频处理**: PyWORLD (WORLD 声码器 Python 包装)
- **数据序列化**: MessagePack
- **UI 框架**: view-ui-plus

## 项目结构

```
Tsubaki-Audio-Lable/
├── src/                      # 前端源代码
│   ├── components/          # Vue 组件
│   ├── koharu-label/        # 标注处理模块
│   ├── lyric-transfer/      # 歌词转换模块
│   ├── assets/              # 静态资源
│   ├── main.ts              # 应用入口
│   ├── index.html           # HTML 模板
│   └── main.css             # 全局样式
├── app.py                   # Flask 后端应用
├── package.json             # NPM 依赖配置
├── vite.config.ts          # Vite 构建配置
├── tsconfig.json           # TypeScript 配置
└── README.md               # 项目说明
```

## 安装与运行

### 环境要求
- Node.js 14+
- Python 3.8+
- Windows 10 x64 或其他现代操作系统

### 快速开始

```bash
# 安装 NPM 依赖
npm install

# 构建前端
npm run build

# 安装 Python 依赖
npm run requirements

# 启动应用
python app.py
```

应用将在 `http://127.0.0.1:6701` 打开。

### 开发模式

```bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

## 核心 API

### 音频处理接口

- `POST /soundfile/read` - 读取音频文件
- `POST /soundfile/write` - 写入音频文件
- `GET /soundfile/available/[format]` - 获取支持的音频格式

### 基频提取接口

- `POST /pyworld/dio` - DIO 算法基频提取
- `POST /pyworld/harvest` - Harvest 算法基频提取
- `POST /pyworld/all` - 完整音频分析 (F0 + 频谱包络 + 非周期性)
- `POST /pyworld/synthesize` - 音频合成

### 可视化接口

- `POST /pyworld/savefig` - 生成音频分析图表

## 与 GPT-SoVITS-MFA-Aligner 的集成

本项目设计用于与 gpt-sovits-mfa-aligner 无缝集成：

1. **Lab 文件导入**: 直接导入 GPT-SoVITS MFA Aligner 导出的 `.lab` 标注文件
2. **音频处理**: 加载对应的音频文件进行音高提取和处理
3. **文件导出**: 生成标准格式的工程文件供其他软件使用

## 许可证

MIT License

## 参考

- [PyWORLD](https://github.com/JeremyCCHsu/Python-Wrapper-for-World-Vocoder/)
- [WORLD Vocoder](https://github.com/mmorise/World/)

<template>
  <div class="export-panel">
    <div class="panel-header">
      <h3>📥 导出文件</h3>
      <p class="hint">导出音高数据到各种格式</p>
    </div>

    <!-- ── 细化音高 ── -->
    <div class="export-section">
      <h4>🎵 细化音高</h4>
      <label class="quantize-toggle">
        <input type="checkbox" v-model="quantizeEnabled" :disabled="hasLab" />
        <span class="toggle-text">
          <template v-if="hasLab">
            🏷️ 已加载 LAB 标注文件 — 自动按音素边界对齐，音高取每段平均值
          </template>
          <template v-else>
            启用音高量化 — 将连续音高吸附到最近的 MIDI 半音
          </template>
        </span>
      </label>
      <p class="section-hint">
        <template v-if="hasLab">
          ✅ LAB 模式：每个音素段对应一个 MIDI 音符，歌词自动填入音标
        </template>
        <template v-else-if="quantizeEnabled">
          ✅ 已启用：导出时每段音高精确对齐到半音音阶，音符更整齐
        </template>
        <template v-else>
          ⬜ 未启用：按有声/无声段合并，每段取平均音高作为 MIDI 音符
        </template>
      </p>
      <p v-if="hasPitch" class="note-preview">
        预计生成 <strong>{{ noteCount }}</strong> 个 MIDI 音符
        <span v-if="noteCount > 0" class="note-range">
          ({{ lowestNote }} ~ {{ highestNote }})
        </span>
      </p>
    </div>

    <!-- ── 标注文件 ── -->
    <div class="export-section">
      <h4>🏷️ 标注文件</h4>
      <div class="export-buttons">
        <button
          class="export-btn lab-btn"
          @click="exportLab"
          :disabled="!hasPitch"
          title="导出为 LAB 格式（帧级连续音高，用于标注对齐）"
        >
          📄 Lab 格式
        </button>
        <button
          class="export-btn json-btn"
          @click="exportJson"
          :disabled="!hasPitch"
          title="导出为 JSON 格式（含完整元数据）"
        >
          📋 JSON 格式
        </button>
      </div>
    </div>

    <!-- ── 歌声合成格式 ── -->
    <div class="export-section">
      <h4>🎵 歌声合成格式</h4>
      <div class="synthesis-options">
        <div class="option-group">
          <label>
            BPM:
            <input v-model.number="bpm" type="number" min="40" max="300" class="input-sm" />
          </label>
          <label>
            基准音高:
            <input v-model.number="baseNote" type="number" min="0" max="127" class="input-sm" />
          </label>
        </div>
      </div>
      <div class="export-buttons">
        <button
          class="export-btn ustx-btn"
          @click="exportFormat('ustx')"
          :disabled="!hasPitch || isExporting"
          title="OpenUtau 工程格式 (YAML)"
        >
          🎼 USTX (OpenUtau)
        </button>
        <button
          class="export-btn svp-btn"
          @click="exportFormat('svp')"
          :disabled="!hasPitch || isExporting"
          title="Synthesizer V 工程格式 (JSON)"
        >
          💿 SVP (Synthesizer V)
        </button>
        <button
          class="export-btn vsqx-btn"
          @click="exportFormat('vsqx')"
          :disabled="!hasPitch || isExporting"
          title="Vocaloid 4 工程格式 (XML)"
        >
          🎹 VSQX (Vocaloid)
        </button>
      </div>
    </div>

    <div v-if="isExporting" class="export-progress">
      <div class="spinner"></div>
      <span>正在生成文件...</span>
    </div>

    <div v-if="successMessage" class="success-message">
      <span>✓ {{ successMessage }}</span>
      <button class="close-btn" @click="successMessage = ''">✕</button>
    </div>

    <div v-if="errorMessage" class="error-message">
      <span>⚠️ {{ errorMessage }}</span>
      <button class="close-btn" @click="errorMessage = ''">✕</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, type PropType } from 'vue'

// ──────────────────────────────────────────────
//  Props
// ──────────────────────────────────────────────
const props = defineProps({
  pitchData: {
    type: Object as PropType<Float32Array | null>,
    default: null,
  },
  waveformData: {
    type: Object as PropType<Float32Array | null>,
    default: null,
  },
  sampleRate:    { type: Number, default: 0 },
  audioFileName: { type: String, default: 'audio' },
  /** LAB 标注文件内容 (MFA phoneme LAB 或 F0 LAB) */
  labContent:    { type: String as PropType<string | null>, default: null },
  backendBaseUrl: { type: String, default: '' }, // 新增
})

// ──────────────────────────────────────────────
//  Reactive state
// ──────────────────────────────────────────────
const bpm             = ref(120)
const baseNote        = ref(60)
const quantizeEnabled = ref(false)
const isExporting     = ref(false)
const successMessage  = ref('')
const errorMessage    = ref('')

/** PyWorld DIO / Harvest 默认帧周期 5 ms */
const FRAME_PERIOD_MS = 5.0

// ──────────────────────────────────────────────
//  Pitch math helpers
// ──────────────────────────────────────────────
function freqToMidi(freq: number): number {
  if (freq <= 0) return -1
  return Math.round(12 * Math.log2(freq / 440) + 69)
}

function midiToNoteName(midi: number): string {
  const names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
  return names[((midi % 12) + 12) % 12] + (Math.floor(midi / 12) - 1)
}

// ──────────────────────────────────────────────
//  LAB segment parser
// ──────────────────────────────────────────────
interface LabSeg {
  startSec: number
  endSec:   number
  phoneme:  string
}

/**
 * 解析 MFA / HTK phoneme LAB 文件。
 * 自动检测时间单位（100ns HTK 格式 vs 秒格式）。
 * 如果第三列全为数字（F0 LAB），返回空数组。
 */
function parseLabSegments(content: string): LabSeg[] {
  const SILENCE = new Set(['sil', 'sp', 'spn', '#', '<sil>', '<sp>'])
  const segs: LabSeg[] = []

  for (const rawLine of content.trim().split('\n')) {
    const line = rawLine.trim()
    if (!line) continue
    const parts = line.split(/\s+/)
    if (parts.length < 3) continue

    const phoneme = parts[2]
    // 如果第三列是数字则是 F0 LAB，跳过
    if (/^-?\d+(\.\d+)?$/.test(phoneme)) continue

    let start = parseFloat(parts[0])
    let end   = parseFloat(parts[1])
    if (isNaN(start) || isNaN(end)) continue

    // HTK 格式：单位为 100ns（值通常 > 10000）
    if (start > 10000) {
      start /= 10_000_000
      end   /= 10_000_000
    }

    if (SILENCE.has(phoneme.toLowerCase())) continue
    segs.push({ startSec: start, endSec: end, phoneme })
  }
  return segs
}

// ──────────────────────────────────────────────
//  Note building
// ──────────────────────────────────────────────
interface NoteMs {
  startMs:    number
  durationMs: number
  midi:       number
  lyric:      string   // 歌词/音素标签
}

/**
 * 【LAB 模式】每个音素段 → 一个音符。
 * 音高取该段内所有有声帧的平均值；若段内无有声帧则跳过。
 */
function buildNotesFromLab(f0: Float32Array, segs: LabSeg[]): NoteMs[] {
  const notes: NoteMs[] = []
  for (const seg of segs) {
    const startFrame = Math.floor((seg.startSec * 1000) / FRAME_PERIOD_MS)
    const endFrame   = Math.ceil((seg.endSec  * 1000) / FRAME_PERIOD_MS)

    let f0Sum = 0, f0Count = 0
    for (let i = Math.max(0, startFrame); i < Math.min(f0.length, endFrame); i++) {
      if (f0[i] > 0) { f0Sum += f0[i]; f0Count++ }
    }

    // 若段内有声帧不足 20%，跳过（避免纯辅音/噪声产生游离音符）
    const segFrames = endFrame - startFrame
    if (f0Count === 0 || f0Count < segFrames * 0.2) continue

    const avgF0 = f0Sum / f0Count
    const midi  = freqToMidi(avgF0)
    if (midi < 0 || midi > 127) continue

    notes.push({
      startMs:    seg.startSec * 1000,
      durationMs: (seg.endSec - seg.startSec) * 1000,
      midi,
      lyric: seg.phoneme,
    })
  }
  return notes
}

/**
 * 【F0 模式】（无 LAB 时的回退）按有声/无声段合并，每段取平均音高。
 * quantize=true 时逐帧拆分到最小半音粒度（保留原有行为）。
 */
function buildNotesFromF0(f0: Float32Array, quantize: boolean): NoteMs[] {
  const notes: NoteMs[] = []
  let i = 0
  const len = f0.length

  while (i < len) {
    if (f0[i] <= 0) { i++; continue }
    const startMidi = freqToMidi(f0[i])
    if (startMidi < 0 || startMidi > 127) { i++; continue }

    let j = i + 1
    let midiSum = startMidi
    while (j < len && f0[j] > 0) {
      const nextMidi = freqToMidi(f0[j])
      if (nextMidi < 0 || nextMidi > 127) break
      if (quantize && nextMidi !== startMidi) break
      midiSum += nextMidi
      j++
    }

    const midi = quantize ? startMidi : Math.round(midiSum / (j - i))
    notes.push({
      startMs:    i * FRAME_PERIOD_MS,
      durationMs: (j - i) * FRAME_PERIOD_MS,
      midi:       Math.max(0, Math.min(127, midi)),
      lyric:      'a',
    })
    i = j
  }
  return notes
}

// ──────────────────────────────────────────────
//  Computed
// ──────────────────────────────────────────────
const hasPitch = computed(() => !!props.pitchData && props.pitchData.length > 0)
const hasLab   = computed(() => {
  if (!props.labContent) return false
  return parseLabSegments(props.labContent).length > 0
})

const computedNotes = computed<NoteMs[]>(() => {
  if (!hasPitch.value) return []
  const f0 = props.pitchData!

  // LAB モード優先
  if (props.labContent) {
    const segs = parseLabSegments(props.labContent)
    if (segs.length > 0) {
      return buildNotesFromLab(f0, segs)
    }
  }
  return buildNotesFromF0(f0, quantizeEnabled.value)
})

const noteCount   = computed(() => computedNotes.value.length)
const lowestNote  = computed(() => {
  if (!computedNotes.value.length) return '—'
  return midiToNoteName(Math.min(...computedNotes.value.map(n => n.midi)))
})
const highestNote = computed(() => {
  if (!computedNotes.value.length) return '—'
  return midiToNoteName(Math.max(...computedNotes.value.map(n => n.midi)))
})

// ──────────────────────────────────────────────
//  Timing converters
// ──────────────────────────────────────────────
/** ms → MIDI ticks (resolution 480) */
function msToTicks(ms: number, bpmVal: number): number {
  return Math.round((ms * bpmVal * 480) / 60000)
}

/** ms → SVP blicks (1 quarter = 705 600 000 blicks) */
const SV_QUARTER = 705600000
function msToBlicks(ms: number, bpmVal: number): number {
  return Math.round((ms * bpmVal * SV_QUARTER) / 60000)
}

// ──────────────────────────────────────────────
//  Export: Lab
// ──────────────────────────────────────────────
const exportLab = () => {
  if (!hasPitch.value) { errorMessage.value = '请先提取音高'; return }
  try {
    let content = ''
    const f0 = props.pitchData!
    for (let i = 0; i < f0.length; i++) {
      const t0    = ((i * FRAME_PERIOD_MS) / 1000).toFixed(4)
      const t1    = (((i + 1) * FRAME_PERIOD_MS) / 1000).toFixed(4)
      const pitch = f0[i] > 0 ? f0[i].toFixed(2) : '0'
      content += `${t0} ${t1} ${pitch}\n`
    }
    downloadText(content, `${props.audioFileName}.lab`, 'text/plain')
    showSuccess(`Lab 文件已导出 (${f0.length} 帧)`)
  } catch (e) { errorMessage.value = String(e) }
}

// ──────────────────────────────────────────────
//  Export: JSON
// ──────────────────────────────────────────────
const exportJson = () => {
  if (!hasPitch.value) { errorMessage.value = '请先提取音高'; return }
  try {
    const f0   = props.pitchData!
    const data = {
      audioFile:     props.audioFileName,
      sampleRate:    props.sampleRate,
      framePeriodMs: FRAME_PERIOD_MS,
      frames:        f0.length,
      f0:            Array.from(f0),
      metadata:      { bpm: bpm.value, baseNote: baseNote.value },
      timestamp:     new Date().toISOString(),
    }
    downloadText(JSON.stringify(data, null, 2), `${props.audioFileName}.json`, 'application/json')
    showSuccess(`JSON 文件已导出 (${f0.length} 帧)`)
  } catch (e) { errorMessage.value = String(e) }
}

// ──────────────────────────────────────────────
//  Export: synthesis formats dispatcher
// ──────────────────────────────────────────────
const exportFormat = async (format: 'ustx' | 'svp' | 'vsqx') => {
  if (!hasPitch.value) {
    errorMessage.value = '请先提取音高'
    return
  }

  isExporting.value = true
  try {
    const notes = computedNotes.value
    if (notes.length === 0) {
      errorMessage.value = '未检测到有效音高帧，请确认音高已成功提取'
      return
    }

    // 先尝试走 Python 后端
    if (props.backendBaseUrl && props.backendBaseUrl.trim()) {
const framePeriodMs = 5
const payload = {
  audioFileName: props.audioFileName,
  bpm: bpm.value,
  notes: notes.map(n => ({
    start_100ns: Math.round(n.startMs * 10000),
    end_100ns: Math.round((n.startMs + n.durationMs) * 10000),
    phoneme: n.lyric,
  })),
  pitch_points: Array.from(props.pitchData ?? []).map((f0, i) => ({
    time_100ns: Math.round(i * framePeriodMs * 10000),
    freq: Number(f0) || 0,
  })),
}

      const url = `${props.backendBaseUrl.replace(/\/?$/, '/') }api/export/${format}`
      const resp = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })

      if (resp.ok) {
        const blob = await resp.blob()
        downloadBlob(blob, `${props.audioFileName}.${format}`)
        showSuccess(`${format.toUpperCase()} 工程文件已导出 (${notes.length} 个音符)`)
        return
      }

      // 后端返回错误时，继续走前端 fallback
      const errText = await resp.text().catch(() => '')
      throw new Error(errText || `后端导出失败: ${resp.status}`)
    }

    // 前端 fallback：保留你原来的本地生成逻辑
    let content: string
    let mime: string
    if (format === 'ustx') {
      content = generateUstx(notes)
      mime = 'text/yaml'
    } else if (format === 'svp') {
      content = generateSvp(notes)
      mime = 'application/json'
    } else {
      content = generateVsqx(notes)
      mime = 'text/xml'
    }

    downloadText(content, `${props.audioFileName}.${format}`, mime)
    showSuccess(`${format.toUpperCase()} 工程文件已导出 (${notes.length} 个音符)`)
  } catch (e) {
    errorMessage.value = e instanceof Error ? e.message : String(e)
  } finally {
    isExporting.value = false
  }
}

// ──────────────────────────────────────────────
//  USTX  (OpenUtau — YAML 格式)
// ──────────────────────────────────────────────
function generateUstx(notes: NoteMs[]): string {
  const res = 480
  const b   = bpm.value
  // 计算 voicePart 总时长（最后一个音符结束位置）
  const lastNote   = notes[notes.length - 1]
  const durTick    = msToTicks(lastNote.startMs + lastNote.durationMs, b)

  let y = `name: ${escapeYaml(props.audioFileName)}\n`
  y += `comment: ""\n`
  y += `outputDir: Vocal\n`
  y += `cacheDir: UCache\n`
  y += `ustxVersion: "0.6"\n`
  y += `bpm: ${b}\n`
  y += `beatPerBar: 4\n`
  y += `beatUnit: 4\n`
  y += `resolution: ${res}\n`
  y += `expressions: {}\n`
  y += `tracks:\n`
  y += `- mute: false\n`
  y += `  solo: false\n`
  y += `  renderEnabled: false\n`
  y += `  volume: 0.0\n`
  y += `  pan: 0.0\n`
  y += `  trackName: ""\n`
  y += `  trackColor: Blue\n`
  y += `  singer: ""\n`          // ← OpenUtau 必须字段
  y += `  phonemizer: ""\n`
  y += `  renderer: ""\n`
  y += `voiceParts:\n`
  y += `- name: Part 1\n`
  y += `  comment: ""\n`
  y += `  trackNo: 0\n`
  y += `  position: 0\n`
  y += `  durTick: ${durTick}\n`
  y += `  notes:\n`
  for (const n of notes) {
    const pos = msToTicks(n.startMs, b)
    const dur = Math.max(1, msToTicks(n.durationMs, b))
    y += `  - position: ${pos}\n`
    y += `    duration: ${dur}\n`
    y += `    tone: ${n.midi}\n`
    y += `    lyric: ${escapeYaml(n.lyric)}\n`
    y += `    phonemeOverride: false\n`
    y += `    vibrato: {}\n`
  }
  y += `waveParts: []\n`
  return y
}

// ──────────────────────────────────────────────
//  SVP  (Synthesizer V — JSON 格式)
// ──────────────────────────────────────────────
function generateSvp(notes: NoteMs[]): string {
  const b = bpm.value
  const svpNotes = notes.map(n => ({
    onset:      msToBlicks(n.startMs, b),
    duration:   Math.max(1, msToBlicks(n.durationMs, b)),
    pitch:      n.midi,
    detune:     0,
    attributes: {},
    lyrics:     n.lyric,
    phonemes:   n.lyric,
  }))

  // 防止相邻音符重叠（SVP 要求音符间有间隔）
  for (let i = 0; i < svpNotes.length - 1; i++) {
    const cur  = svpNotes[i]
    const next = svpNotes[i + 1]
    if (next.onset < cur.onset + cur.duration) {
      cur.duration = Math.max(1, next.onset - cur.onset)
    }
  }

  const doc = {
    version: 120,
    time: {
      meter: [{ index: 0, numerator: 4, denominator: 4 }],
      tempo: [{ position: 0, bpm: b }],
    },
    library: [],
    tracks: [{
      name:          props.audioFileName,
      dispColor:     'ff7db235',
      dispOrder:     0,
      renderEnabled: false,
      mixer: { gainDecibel: 0, pan: 0, mute: false, solo: false, display: true },
      mainRef: {
        groupID:         '00000000-0000-0000-0000-000000000000',
        blickOffset:     0,
        pitchOffset:     0,
        isInstrumental:  false,
        database:        { name: '', language: '', phoneset: '' },
        dictionary:      '',
        voice:           {},
      },
      mainGroup: {
        name:    'main',
        uuid:    '00000000-0000-0000-0000-000000000000',
        comment: '',
        parameters: {
          pitchDelta:  { mode: 'linear', points: [] },
          vibratoEnv:  { mode: 'cubic',  points: [] },
          loudness:    { mode: 'cubic',  points: [] },
          tension:     { mode: 'cubic',  points: [] },
          breathiness: { mode: 'cubic',  points: [] },
          voicing:     { mode: 'cubic',  points: [] },
          gender:      { mode: 'cubic',  points: [] },
          toneShift:   { mode: 'cubic',  points: [] },
        },
        notes:        svpNotes,
        renderConfig: null,
      },
    }],
    renderConfig: { headRoomDecibel: -3, exportMixDown: true },
  }
  return JSON.stringify(doc, null, 2)
}

// ──────────────────────────────────────────────
//  VSQX  (Vocaloid 4 — XML 格式)
//
//  ⚠️  VSQX4 使用缩写标签，与 VSQX3 完全不同：
//      位置   <posTick> → <t>
//      音高   <noteNum> → <n>
//      力度   <velocity> → <v>
//      歌词   <lyric>   → <y>  (需 CDATA)
//      音素   <phnms>   → <p>  (需 CDATA)
//      拍号m  <posMes>  → <m>
//      速度v  <bpm>     → <v>  (= BPM × 100)
//  另须包含 <mixer>、<sPlug>、<pStyle>、<monoTrack>、<stTrack>、<aux>。
// ──────────────────────────────────────────────
function generateVsqx(notes: NoteMs[]): string {
  const b   = bpm.value
  const res = 480

  // playTime = 最后一个音符结束 tick
  const totalTicks = notes.length
    ? msToTicks(notes[notes.length - 1].startMs + notes[notes.length - 1].durationMs, b)
    : 0

  // 防止音符重叠：缩短前一个音符到下一个音符开始处
  const safeNotes = notes.map(n => ({ ...n }))
  for (let i = 0; i < safeNotes.length - 1; i++) {
    const curEnd  = msToTicks(safeNotes[i].startMs + safeNotes[i].durationMs, b)
    const nextPos = msToTicks(safeNotes[i + 1].startMs, b)
    if (curEnd > nextPos) {
      safeNotes[i].durationMs = Math.max(1 / (b * 480 / 60000),
        safeNotes[i + 1].startMs - safeNotes[i].startMs)
    }
  }

  const noteXml = safeNotes.map(n => {
    const pos = msToTicks(n.startMs, b)
    const dur = Math.max(1, msToTicks(n.durationMs, b))
    // <y> = 歌词, <p> = 音素（均需 CDATA）
    return (
      `\t\t\t<note>\n` +
      `\t\t\t\t<t>${pos}</t>\n` +
      `\t\t\t\t<dur>${dur}</dur>\n` +
      `\t\t\t\t<n>${n.midi}</n>\n` +
      `\t\t\t\t<v>64</v>\n` +
      `\t\t\t\t<y><![CDATA[${n.lyric}]]></y>\n` +
      `\t\t\t\t<p><![CDATA[${n.lyric}]]></p>\n` +
      `\t\t\t\t<nStyle><v id="accent">50</v></nStyle>\n` +
      `\t\t\t</note>`
    )
  }).join('\n')

  return `<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<vsq4 xmlns="http://www.yamaha.co.jp/vocaloid/schema/vsq4/"
      xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
      xsi:schemaLocation="http://www.yamaha.co.jp/vocaloid/schema/vsq4/ vsq4.xsd">
\t<vender><![CDATA[Yamaha corporation]]></vender>
\t<version><![CDATA[4.0.0.3]]></version>
\t<vVoiceTable>
\t\t<vVoice>
\t\t\t<bs>0</bs>
\t\t\t<pc>0</pc>
\t\t\t<id><![CDATA[VOICEID]]></id>
\t\t\t<name><![CDATA[Voice]]></name>
\t\t\t<vPrm>
\t\t\t\t<bre>0</bre><bri>0</bri><cle>0</cle><gen>0</gen><ope>0</ope>
\t\t\t</vPrm>
\t\t</vVoice>
\t</vVoiceTable>
\t<mixer>
\t\t<masterUnit>
\t\t\t<oDev>0</oDev><rLvl>0</rLvl><vol>0</vol>
\t\t</masterUnit>
\t\t<vsUnit>
\t\t\t<tNo>0</tNo><iGin>0</iGin><sLvl>-898</sLvl><sEnable>0</sEnable>
\t\t\t<m>0</m><s>0</s><pan>64</pan><vol>0</vol>
\t\t</vsUnit>
\t\t<monoUnit>
\t\t\t<iGin>0</iGin><sLvl>-898</sLvl><sEnable>0</sEnable>
\t\t\t<m>0</m><s>0</s><pan>64</pan><vol>0</vol>
\t\t</monoUnit>
\t\t<stUnit>
\t\t\t<iGin>0</iGin><m>0</m><s>0</s><vol>-129</vol>
\t\t</stUnit>
\t</mixer>
\t<masterTrack>
\t\t<seqName><![CDATA[${escapeXml(props.audioFileName)}]]></seqName>
\t\t<comment><![CDATA[New VSQ File]]></comment>
\t\t<resolution>${res}</resolution>
\t\t<preMeasure>0</preMeasure>
\t\t<timeSig><m>0</m><nu>4</nu><de>4</de></timeSig>
\t\t<tempo><t>0</t><v>${Math.round(b * 100)}</v></tempo>
\t</masterTrack>
\t<vsTrack>
\t\t<tNo>0</tNo>
\t\t<name><![CDATA[${escapeXml(props.audioFileName)}]]></name>
\t\t<comment><![CDATA[Track]]></comment>
\t\t<vsPart>
\t\t\t<t>0</t>
\t\t\t<playTime>${totalTicks}</playTime>
\t\t\t<name><![CDATA[Part 1]]></name>
\t\t\t<comment><![CDATA[New Musical Part]]></comment>
\t\t\t<sPlug>
\t\t\t\t<id><![CDATA[ACA9C502-A04B-42b5-B2EB-5CEA36D16FCE]]></id>
\t\t\t\t<name><![CDATA[VOCALOID2 Compatible Style]]></name>
\t\t\t\t<version><![CDATA[3.0.0.1]]></version>
\t\t\t</sPlug>
\t\t\t<pStyle>
\t\t\t\t<v id="accent">50</v>
\t\t\t\t<v id="bendDep">8</v>
\t\t\t\t<v id="bendLen">0</v>
\t\t\t\t<v id="decay">50</v>
\t\t\t\t<v id="fallPort">0</v>
\t\t\t\t<v id="opening">127</v>
\t\t\t\t<v id="risePort">0</v>
\t\t\t</pStyle>
\t\t\t<singer>
\t\t\t\t<t>0</t>
\t\t\t\t<bs>0</bs>
\t\t\t\t<pc>0</pc>
\t\t\t</singer>
${noteXml}
\t\t</vsPart>
\t</vsTrack>
\t<monoTrack></monoTrack>
\t<stTrack></stTrack>
\t<aux>
\t\t<id><![CDATA[AUX_VST_HOST_CHUNK_INFO]]></id>
\t\t<content><![CDATA[VlNDSwAAAAADAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=]]></content>
\t</aux>
</vsq4>`
}

// ──────────────────────────────────────────────
//  Utility
// ──────────────────────────────────────────────
function escapeXml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

/** 简单 YAML 字符串转义（单词含特殊字符时加引号） */
function escapeYaml(s: string): string {
  if (/[:#\[\]{},\|>&!*'"]/.test(s) || s.includes(' ') || s === '') {
    return `"${s.replace(/"/g, '\\"')}"`
  }
  return s
}

function downloadText(content: string, filename: string, mime: string) {
  const blob = new Blob([content], { type: mime })
  const url  = URL.createObjectURL(blob)
  const a    = document.createElement('a')
  a.href = url; a.download = filename
  document.body.appendChild(a); a.click()
  document.body.removeChild(a); URL.revokeObjectURL(url)
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

function showSuccess(msg: string) {
  successMessage.value = msg
  setTimeout(() => { successMessage.value = '' }, 3000)
}
</script>

<style scoped>
.export-panel {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.1);
}

.panel-header { margin-bottom: 20px; }
.panel-header h3 { margin: 0 0 8px 0; font-size: 16px; color: #333; }
.hint { margin: 0; font-size: 12px; color: #999; }

.export-section {
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid #eee;
}
.export-section:last-of-type { border-bottom: none; }
.export-section h4 { margin: 0 0 12px 0; font-size: 13px; color: #333; font-weight: 500; }

.quantize-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-size: 13px;
  color: #444;
  margin-bottom: 6px;
}
.quantize-toggle input[type='checkbox'] {
  accent-color: #667eea; width: 15px; height: 15px; flex-shrink: 0; cursor: pointer;
}
.toggle-text { line-height: 1.4; }
.section-hint { margin: 4px 0 0; font-size: 11px; color: #888; }
.note-preview {
  margin: 8px 0 0;
  font-size: 12px;
  color: #4a5568;
  background: #f0f4ff;
  border-radius: 5px;
  padding: 6px 10px;
  display: inline-block;
}
.note-preview strong { color: #667eea; }
.note-range { margin-left: 6px; color: #888; font-size: 11px; }

.export-buttons {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 8px;
}

.export-btn {
  padding: 10px 12px;
  border: 1px solid #ddd;
  background: white;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  transition: all 0.2s ease;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.export-btn:hover:not(:disabled) { border-color: #667eea; color: #667eea; background: #f0f4ff; }
.export-btn:disabled { opacity: 0.45; cursor: not-allowed; }

.lab-btn  { background: #ffe8e8; border-color: #ffcccc; color: #ff6b6b; }
.json-btn { background: #e8f5ff; border-color: #ccecff; color: #1890ff; }
.ustx-btn { background: #f0e8ff; border-color: #e0ccff; color: #667eea; }
.svp-btn  { background: #e8ffe8; border-color: #ccffcc; color: #4caf50; }
.vsqx-btn { background: #fff8e8; border-color: #ffe8cc; color: #ff9800; }

.synthesis-options { margin-bottom: 12px; }
.option-group { display: flex; gap: 12px; flex-wrap: wrap; }
.option-group label { display: flex; align-items: center; gap: 6px; font-size: 12px; color: #666; }
.input-sm { width: 64px; padding: 4px 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 12px; }

.export-progress {
  display: flex; align-items: center; gap: 12px;
  padding: 12px 16px; background: #f0f4ff;
  border-radius: 6px; color: #667eea; font-size: 13px; margin-bottom: 12px;
}
.spinner {
  width: 16px; height: 16px;
  border: 2px solid #ddd; border-top-color: #667eea;
  border-radius: 50%; animation: spin 1s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.success-message, .error-message {
  display: flex; justify-content: space-between; align-items: center;
  padding: 12px 16px; border-radius: 4px; font-size: 13px; margin-bottom: 12px;
}
.success-message { background: #efe; border-left: 4px solid #4caf50; color: #2e7d32; }
.error-message   { background: #fee; border-left: 4px solid #f66; color: #c33; }
.close-btn { background: none; border: none; color: inherit; cursor: pointer; font-size: 16px; }
</style>

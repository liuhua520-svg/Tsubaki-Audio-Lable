# svpWrite.py （修复版）
import json, math

def freq_to_midi(f):
    """将频率 f (Hz) 转换为最近的 MIDI 音高编号（四舍五入）"""
    if f <= 0:
        return 0
    return int(round(69 + 12 * math.log2(f / 440.0)))

def write_svp(lab_segments, pitch_continuous, output_path, bpm=120):
    """
    - lab_segments: [(start_tick100ns, end_tick100ns, phoneme_str), ...]
    - pitch_continuous: {time100ns: freq, ...}（连续 F0，可以按需求取值）
    - 输出为 SynthV SVP 格式（JSON）。
    """
    # 基本项目结构
    svp = {
        "version": 120,
        "time": {"tempo": [{"position": 0, "bpm": bpm}]},
        "tracks": [],
        "renderConfig": None
    }
    track = {
        "name": "Track1",
        "dispColor": "ff7db235",
        "dispOrder": 0,
        "renderEnabled": True,
        "mixer": {"gainDecibel": 0, "pan": 0, "mute": False, "solo": False},
        "mainRef": {"groupID": "default", "pitchOffset": 0, "isInstrumental": False},
        "mainGroup": {"name": "Group1", "notes": []}
    }
    # 时间转换：1 tick = (bpm/60 * 480) per second, lab 单位 100ns
    ticks_per_sec = bpm * 480.0 / 60.0  # 960 for bpm=120
    for start, end, phoneme in lab_segments:
        # 计算音符起始位置和时长（SynthV 用纳秒，此处简用样例）
        onset = start  # 假定直接使用 100ns 单位, SynthV 导出可按需要调整
        duration = end - start
        # 取该段音高（可取平均或起始点）
        # 若启用量化：nearest = freq_to_midi(freq)
        freq = pitch_continuous.get(start, 0.0)
        midi_pitch = freq_to_midi(freq)
        # 微调：detune = 1200*log2(freq/nearest_freq)
        detune = 0
        if freq > 0 and midi_pitch > 0:
            nearest_freq = 440.0 * (2 ** ((midi_pitch - 69) / 12.0))
            detune = int(round(1200 * math.log2(freq / nearest_freq))) if freq > 0 else 0
        note = {
            "onset": onset,
            "duration": duration,
            "pitch": midi_pitch,
            "detune": detune,
            "attributes": {},
            "lyrics": phoneme if phoneme != "-" else "",
            "phonemes": phoneme if phoneme != "-" else ""
        }
        track["mainGroup"]["notes"].append(note)
    svp["tracks"].append(track)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(svp, f, indent=2, ensure_ascii=False)

# vsqxWrite.py （修复版）
import xml.etree.ElementTree as ET, math

def freq_to_midi(f):
    if f <= 0: return 0
    return int(round(69 + 12 * math.log2(f / 440.0)))

def write_vsqx(lab_segments, pitch_continuous, output_path, bpm=120):
    """
    - lab_segments: [(start_100ns, end_100ns, phoneme), ...]
    - pitch_continuous: {time100ns: freq, ...}
    """
    ns = "http://www.yamaha.co.jp/vocaloid/schema/vsq4/"
    ET.register_namespace("", ns)
    root = ET.Element(f"{{{ns}}}vsq4")
    ET.SubElement(root, "version").text = "<![CDATA[4.0.0.3]]>"  # 版本
    # Voice Table
    vTable = ET.SubElement(root, "vVoiceTable")
    v = ET.SubElement(vTable, "vVoice")
    # 填充语音信息（示例：使用初音中文库）
    ET.SubElement(v, "bs").text = "4"
    ET.SubElement(v, "pc").text = "14"
    ET.SubElement(v, "id").text = "<![CDATA[BNGE7CP7EMTRSNC3]]>"
    ET.SubElement(v, "name").text = "<![CDATA[MIKU_V4_Chinese]]>"
    vPrm = ET.SubElement(v, "vPrm")
    for attr in ["bre","bri","cle","gen","ope"]:
        ET.SubElement(vPrm, attr).text = "0"
    # Tempo & Time signature
    tHead = ET.SubElement(root, "tHead")
    resolution = ET.SubElement(tHead, "resolution")
    resolution.text = "480"
    meter = ET.SubElement(tHead, "meter")
    meter.text = "4"
    tempo = ET.SubElement(tHead, "tempo")
    tempo.text = str(bpm)
    # Track and notes
    track = ET.SubElement(root, "vsTrack")
    ET.SubElement(track, "vsTrackNo").text = "0"
    tone_list = ET.SubElement(track, "tones")
    ticks_per_sec = bpm * 480.0 / 60.0
    for start, end, phoneme in lab_segments:
        t = int(round(start * 1e-7 * ticks_per_sec))
        dur = int(round((end - start) * 1e-7 * ticks_per_sec))
        freq = pitch_continuous.get(start, 0.0)
        midi_pitch = freq_to_midi(freq)
        note = ET.SubElement(tone_list, "vsTone")
        ET.SubElement(note, "t").text = str(t)
        ET.SubElement(note, "dur").text = str(dur)
        ET.SubElement(note, "n").text = str(midi_pitch)
        ET.SubElement(note, "v").text = "64"
        # 歌词文本
        y = ET.SubElement(note, "y")
        p = ET.SubElement(note, "p")
        # 若是虚音，用-；否则写入音素文本
        y.text = phoneme if phoneme != "-" else "-"
        p.text = phoneme if phoneme != "-" else "-"
        ET.SubElement(note, "nStyle")
    # 写入文件
    tree = ET.ElementTree(root)
    tree.write(output_path, encoding="UTF-8", xml_declaration=True)

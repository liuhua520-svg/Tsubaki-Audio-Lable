# -*- coding: utf-8 -*-
import json
import math

def freq_to_midi(f):
    if f <= 0:
        return 0
    return int(round(69 + 12 * math.log2(f / 440.0)))

def write_ustx(lab_segments, pitch_continuous, output_path, bpm=120):
    """
    - lab_segments: [(start_100ns, end_100ns, phoneme), ...]
    - pitch_continuous: {time100ns: freq, ...}
    """
    ustx = {
        "version": "0.5.0",
        "tempo": bpm,
        "tracks": [
            {
                "name": "Track1",
                "notes": []
            }
        ]
    }

    for start, end, phoneme in lab_segments:
        freq = pitch_continuous.get(start, 0)
        midi_pitch = freq_to_midi(freq)
        note = {
            "start": int(start),
            "end": int(end),
            "pitch": midi_pitch,
            "phoneme": phoneme if phoneme != "-" else ""
        }
        ustx["tracks"][0]["notes"].append(note)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(ustx, f, indent=2, ensure_ascii=False)
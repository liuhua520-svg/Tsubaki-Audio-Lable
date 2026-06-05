# -*- coding: utf-8 -*-
import os
import sys
import json
import socket
import webbrowser
from threading import Thread
from time import sleep
from functools import wraps
from tempfile import SpooledTemporaryFile as TempFile, NamedTemporaryFile

import numpy as np
import pyworld as pw
import msgpack as mp
import soundfile as sf
from flask import Flask, request, jsonify, render_template, Response
from flask_cors import CORS

# 让 backend 目录可被稳定导入
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

try:
    from backend.vsqxWrite import write_vsqx
except Exception as e:
    write_vsqx = None
    _vsqx_import_error = e

try:
    from backend.svpWrite import write_svp
except Exception as e:
    write_svp = None
    _svp_import_error = e

try:
    from backend.ustxWrite import write_ustx
except Exception as e:
    write_ustx = None
    _ustx_import_error = e

app = Flask(
    __name__, template_folder="./dist", static_folder="./dist", static_url_path="/"
)
max_size = 128 * 1024 * 1024
app.config["MAX_CONTENT_LENGTH"] = max_size
CORS(app, supports_credentials=True)


def packNdarray(array: np.ndarray):
    """将 NumPy 数组打包为 JSON 可直接序列化的纯 List"""
    return array.tolist()


def unpackNdarray(array) -> np.ndarray:
    """从各种前端输入格式安全地解包为 NumPy 数组"""
    if isinstance(array, np.ndarray):
        return array
    if isinstance(array, list):
        return np.array(array)
    if isinstance(array, dict):
        if "buffer" in array:
            if isinstance(array["buffer"], bytes):
                return np.ndarray(**array, order="C")
            elif isinstance(array["buffer"], list):
                return np.array(array["buffer"])
    return np.array(array)


@app.route("/")
def index():
    return render_template("index.html", backend="python")


@app.route("/env", methods=["GET"])
def env():
    """获取环境信息"""
    return jsonify(
        executable=sys.executable,
        byteorder=sys.byteorder,
        path=sys.path,
        modules=list(sys.modules.keys()),
    )


@app.route("/soundfile/available/", methods=["GET"])
@app.route("/soundfile/available/<format>", methods=["GET"])
def soundfile_available(format=None):
    """获取支持的音频格式"""
    if format is None:
        data = sf.available_formats()
    else:
        data = sf.available_subtypes(format=format)
    return jsonify(data)


@app.route("/soundfile/read", methods=["POST"])
def soundfile_read():
    """读取音频文件"""
    with TempFile(max_size=max_size) as file:
        file.write(request.get_data())
        file.seek(0)
        info = dict(**sf.info(file).__dict__)
        file.seek(0)
        data, fs = sf.read(file)

    info.pop("verbose", None)
    info.pop("name", None)
    if data.ndim == 2:
        data = data.swapaxes(0, 1)

    return jsonify({"fs": fs, "info": info, "data": packNdarray(data)})


@app.route("/soundfile/write", methods=["POST"])
def soundfile_write():
    """写入音频文件"""
    raw_data = request.get_data()
    try:
        requ_body = json.loads(raw_data.decode("utf-8"))
    except Exception:
        requ_body = mp.unpackb(raw_data)

    with TempFile(max_size=max_size) as file:
        sf.write(
            file=file,
            data=unpackNdarray(requ_body["data"]),
            samplerate=requ_body["fs"],
            format=requ_body.get("format"),
            subtype=requ_body.get("subtype"),
        )
        file.seek(0)
        data = file.read()
    return data, 200, {"Content-Type": "application/octet-stream"}


def wrap_msgpack(func):
    """智能响应装饰器：兼容 JSON 与原始二进制字节流"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        import inspect

        raw_data = request.get_data()
        requ_body = None

        if request.is_json:
            try:
                requ_body = request.get_json()
            except Exception:
                pass

        if requ_body is None:
            try:
                requ_body = json.loads(raw_data.decode("utf-8"))
            except Exception:
                requ_body = raw_data

        if isinstance(requ_body, dict):
            resp_body = func(**requ_body)
        else:
            sig = inspect.signature(func)
            params = list(sig.parameters.keys())
            waveform = np.frombuffer(requ_body, dtype=np.float32).astype(np.float64)

            kwargs_to_pass = {}
            if len(params) > 0:
                kwargs_to_pass[params[0]] = waveform

            if len(params) > 1:
                url_fs = request.args.get(
                    "fs", request.args.get("sampleRate", type=int), type=int
                )
                default_fs = sig.parameters[params[1]].default

                if url_fs is not None:
                    kwargs_to_pass[params[1]] = url_fs
                elif default_fs != inspect.Parameter.empty:
                    kwargs_to_pass[params[1]] = default_fs
                else:
                    kwargs_to_pass[params[1]] = 16000

            resp_body = func(**kwargs_to_pass)

        return jsonify(resp_body)

    return wrapper


@app.route("/pyworld/dio", methods=["POST"])
@wrap_msgpack
def dio(data, fs):
    """DIO 算法基频提取"""
    data = unpackNdarray(data).astype(float)
    _f0, t = pw.dio(data, fs)
    f0 = pw.stonemask(data, _f0, t, fs)
    return {"t": packNdarray(t), "f0": packNdarray(f0)}


@app.route("/pyworld/harvest", methods=["POST"])
@wrap_msgpack
def harvest(data, fs):
    """Harvest 算法基频提取"""
    data = unpackNdarray(data).astype(float)
    _f0, t = pw.harvest(data, fs)
    f0 = pw.stonemask(data, _f0, t, fs)
    return {"t": packNdarray(t), "f0": packNdarray(f0)}


@app.route("/pyworld/all", methods=["POST"])
@wrap_msgpack
def all(data, fs):
    """完整音频 analysis (F0 + 频谱包络 + 非周期性)"""
    data = unpackNdarray(data).astype(float)
    _f0, t = pw.dio(data, fs)
    f0 = pw.stonemask(data, _f0, t, fs)
    sp = pw.cheaptrick(data, f0, t, fs)
    ap = pw.d4c(data, f0, t, fs)
    return {
        "t": packNdarray(t),
        "f0": packNdarray(f0),
        "sp": packNdarray(sp),
        "ap": packNdarray(ap),
    }


@app.route("/pyworld/synthesize", methods=["POST"])
@wrap_msgpack
def synthesize(f0, sp, ap, fs):
    """音频合成"""
    f0 = unpackNdarray(f0)
    sp = unpackNdarray(sp).copy()
    ap = unpackNdarray(ap).copy()
    data = pw.synthesize(f0, sp, ap, fs)
    return packNdarray(data)


@app.route("/pyworld/sharpen", methods=["POST"])
@wrap_msgpack
def sharpen(f0, sharpness=0.5):
    """音高锐化处理"""
    f0 = unpackNdarray(f0)
    from scipy.ndimage import gaussian_filter1d

    f0_sharpened = f0.copy()
    voiced_mask = f0 > 0
    if voiced_mask.any():
        f0_voiced = f0[voiced_mask]
        smoothing_sigma = max(1, 5 * (1 - sharpness))
        f0_smoothed = gaussian_filter1d(f0_voiced, sigma=smoothing_sigma)
        f0_sharpened[voiced_mask] = f0_smoothed
    return packNdarray(f0_sharpened)


@app.route("/pyworld/savefig", methods=["POST"])
def savefig():
    """生成音频分析图表"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    EPSILON = 1e-8

    raw_data = request.get_data()
    try:
        requ_body = json.loads(raw_data.decode("utf-8"))
    except Exception:
        requ_body = mp.unpackb(raw_data)

    log = requ_body.get("log", True)
    figlist = list(map(lambda x: unpackNdarray(x), requ_body["figlist"]))
    n = len(figlist)

    f = figlist[0]
    if len(f.shape) == 1:
        plt.figure()
        for i, f in enumerate(figlist):
            plt.subplot(n, 1, i + 1)
            if len(f.shape) == 1:
                plt.plot(f)
                plt.xlim([0, len(f)])
    elif len(f.shape) == 2:
        plt.figure()
        for i, f in enumerate(figlist):
            plt.subplot(n, 1, i + 1)
            if log:
                x = np.log(f + EPSILON)
            else:
                x = f + EPSILON
            plt.imshow(
                x.T,
                origin="lower",
                interpolation="none",
                aspect="auto",
                extent=(0, x.shape[0], 0, x.shape[1]),
            )
    else:
        raise ValueError("Input dimension must < 3.")

    with TempFile(max_size=max_size) as file:
        plt.savefig(file, format="png")
        plt.close()
        file.seek(0)
        data = file.read()
    return data, 200, {"Content-Type": "image/png"}


def _normalize_lab_segments(payload):
    """
    支持两种输入：
    1) payload["lab_segments"] = [[start, end, phoneme], ...]
    2) payload["notes"] = [{"start_100ns":..., "end_100ns":..., "phoneme":...}, ...]
    """
    if "lab_segments" in payload and payload["lab_segments"]:
        segs = []
        for item in payload["lab_segments"]:
            if len(item) < 3:
                continue
            start, end, phoneme = item[0], item[1], item[2]
            segs.append((int(start), int(end), str(phoneme)))
        return segs

    if "notes" in payload and payload["notes"]:
        segs = []
        for item in payload["notes"]:
            start = item.get("start_100ns", item.get("start", None))
            end = item.get("end_100ns", item.get("end", None))
            phoneme = item.get("phoneme", item.get("lyric", "-"))
            if start is None or end is None:
                continue
            segs.append((int(start), int(end), str(phoneme)))
        return segs

    return []


def _normalize_pitch_map(payload):
    """
    支持两种输入：
    1) payload["pitch_continuous"] = {time100ns: freq, ...}
    2) payload["pitch_points"] = [{"time_100ns":..., "freq":...}, ...]
    """
    if "pitch_continuous" in payload and isinstance(payload["pitch_continuous"], dict):
        out = {}
        for k, v in payload["pitch_continuous"].items():
            try:
                out[int(k)] = float(v)
            except Exception:
                continue
        return out

    if "pitch_points" in payload and payload["pitch_points"]:
        out = {}
        for item in payload["pitch_points"]:
            t = item.get("time_100ns", item.get("time", None))
            f = item.get("freq", item.get("pitch", None))
            if t is None or f is None:
                continue
            out[int(t)] = float(f)
        return out

    return {}


def _write_temp_file(writer_func, output_ext, lab_segments, pitch_continuous, bpm):
    if writer_func is None:
        raise RuntimeError("writer function is not available")

    with NamedTemporaryFile(delete=False, suffix=output_ext) as tmp:
        tmp_path = tmp.name

    try:
        writer_func(lab_segments, pitch_continuous, tmp_path, bpm=bpm)
        with open(tmp_path, "rb") as f:
            return f.read()
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass


@app.route("/api/export/vsqx", methods=["POST"])
def export_vsqx():
    if write_vsqx is None:
        return jsonify(
            {
                "error": "backend.vsqxWrite import failed",
                "detail": str(globals().get("_vsqx_import_error", "")),
            }
        ), 500

    payload = request.get_json(force=True)
    lab_segments = _normalize_lab_segments(payload)
    pitch_continuous = _normalize_pitch_map(payload)
    bpm = float(payload.get("bpm", 120))

    if not lab_segments:
        return jsonify({"error": "lab_segments 为空"}), 400

    try:
        data = _write_temp_file(write_vsqx, ".vsqx", lab_segments, pitch_continuous, bpm)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    filename = f'{payload.get("audioFileName", "audio")}.vsqx'
    return Response(
        data,
        mimetype="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.route("/api/export/svp", methods=["POST"])
def export_svp():
    if write_svp is None:
        return jsonify(
            {
                "error": "backend.svpWrite import failed",
                "detail": str(globals().get("_svp_import_error", "")),
            }
        ), 500

    payload = request.get_json(force=True)
    lab_segments = _normalize_lab_segments(payload)
    pitch_continuous = _normalize_pitch_map(payload)
    bpm = float(payload.get("bpm", 120))

    if not lab_segments:
        return jsonify({"error": "lab_segments 为空"}), 400

    try:
        data = _write_temp_file(write_svp, ".svp", lab_segments, pitch_continuous, bpm)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    filename = f'{payload.get("audioFileName", "audio")}.svp'
    return Response(
        data,
        mimetype="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.route("/api/export/ustx", methods=["POST"])
def export_ustx():
    if write_ustx is None:
        return jsonify(
            {
                "error": "backend.ustxWrite import failed",
                "detail": str(globals().get("_ustx_import_error", "")),
            }
        ), 500

    payload = request.get_json(force=True)
    lab_segments = _normalize_lab_segments(payload)
    pitch_continuous = _normalize_pitch_map(payload)
    bpm = float(payload.get("bpm", 120))

    if not lab_segments:
        return jsonify({"error": "lab_segments 为空"}), 400

    try:
        data = _write_temp_file(write_ustx, ".ustx", lab_segments, pitch_continuous, bpm)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    filename = f'{payload.get("audioFileName", "audio")}.ustx'
    return Response(
        data,
        mimetype="text/yaml",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def isPortOpen(host, port):
    """检查端口是否开放"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            s.connect((host, port))
    except socket.error:
        return False
    else:
        return True


def open_browser(host, port):
    """打开浏览器"""
    sleep(1)
    while not isPortOpen(host, port):
        sleep(0.5)
    webbrowser.open(url=f"http://{host}:{port}")


def main(host="127.0.0.1", port=6701):
    """主函数"""
    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        thread = Thread(target=open_browser, args=(host, port), daemon=True)
        thread.start()
    app.run(host=host, port=port, debug=True, use_reloader=False)


if __name__ == "__main__":
    main()
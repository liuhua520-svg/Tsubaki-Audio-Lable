# -*- coding: utf-8 -*-
import os
import sys
import socket
import webbrowser
import json
from threading import Thread
from time import sleep, time
from functools import wraps
from tempfile import SpooledTemporaryFile as TempFile
import numpy as np, pyworld as pw, msgpack as mp, soundfile as sf
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

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
        
    # ✨ 修复：不再使用 msgpack，直接返回标准的 JSON 响应
    return jsonify({"fs": fs, "info": info, "data": packNdarray(data)})


@app.route("/soundfile/write", methods=["POST"])
def soundfile_write():
    """写入音频文件"""
    raw_data = request.get_data()
    try:
        requ_body = json.loads(raw_data.decode('utf-8'))
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
    """智能响应装饰器：保持原名称，但内部全面改用 JSON 与前端完美对接"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        import numpy as np
        import inspect

        raw_data = request.get_data()
        requ_body = None
        
        # 1. 优先尝试将其解析为标准 JSON (兼容前端的 sharpen 等接口)
        if request.is_json:
            try:
                requ_body = request.get_json()
            except Exception:
                pass
        
        if requ_body is None:
            try:
                requ_body = json.loads(raw_data.decode('utf-8'))
            except Exception:
                # 如果不是 JSON，说明是前端直接传过来的 Float32Array 原始二进制字节流 (如 dio/harvest 接口)
                requ_body = raw_data

        # 2. 智能化参数匹配与兼容
        if isinstance(requ_body, dict):
            # 如果解包出来是标准字典，按原样执行调用
            resp_body = func(**requ_body)
        else:
            # 如果是 bytes（即前端在提取音高时发送的原始音频数据流）
            sig = inspect.signature(func)
            params = list(sig.parameters.keys())
            
            # 将前端传来的 Float32Array 字节流转换为 pyworld 要求的 float64 数组
            waveform = np.frombuffer(requ_body, dtype=np.float32).astype(np.float64)
            
            kwargs_to_pass = {}
            if len(params) > 0:
                kwargs_to_pass[params[0]] = waveform  # 第一个参数通常是 data 
                
            if len(params) > 1:
                # 第二个参数采样率 fs
                url_fs = request.args.get('fs', request.args.get('sampleRate', type=int), type=int)
                default_fs = sig.parameters[params[1]].default
                
                if url_fs is not None:
                    kwargs_to_pass[params[1]] = url_fs
                elif default_fs != inspect.Parameter.empty:
                    kwargs_to_pass[params[1]] = default_fs
                else:
                    kwargs_to_pass[params[1]] = 16000  # 默认兜底
                    
            resp_body = func(**kwargs_to_pass)
            
        # ✨ 核心修复：一律采用 Flask 的 jsonify 返回标准 JSON，彻底干掉 '' 报错
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
        requ_body = json.loads(raw_data.decode('utf-8'))
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


def isPortOpen(host, port):
    """检查端口是否开放"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            s.connect((host, port))
    except socket.error as e:
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
    if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        thread = Thread(target=open_browser, args=(host, port), daemon=True)
        thread.start()
    app.run(host=host, port=port, debug=True, use_reloader=False)


if __name__ == "__main__":
    main()
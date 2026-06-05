# -*- coding: utf-8 -*-
import sys
import socket
import webbrowser
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


def packNdarray(array: np.ndarray) -> dict:
    """将 NumPy 数组打包为字典"""
    return {
        "shape": array.shape,
        "dtype": str(array.dtype),
        "buffer": array.tobytes("C"),
    }


def unpackNdarray(array: dict) -> np.ndarray:
    """从字典解包 NumPy 数组"""
    return np.ndarray(**array, order="C")


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
    return mp.packb(data), 200, {"Content-Type": "application/x-msgpack"}


@app.route("/soundfile/read", methods=["POST"])
def soundfile_read():
    """读取音频文件"""
    with TempFile(max_size=max_size) as file:
        file.write(request.get_data())
        file.seek(0)
        info = dict(**sf.info(file).__dict__)
        file.seek(0)
        data, fs = sf.read(file)

    info.pop("verbose")
    info.pop("name")
    if data.ndim == 2:
        data = data.swapaxes(0, 1)
    return (
        mp.packb({"fs": fs, "info": info, "data": packNdarray(data)}),
        200,
        {"Content-Type": "application/x-msgpack"},
    )


@app.route("/soundfile/write", methods=["POST"])
def soundfile_write():
    """写入音频文件"""
    requ_body = mp.unpackb(request.get_data())
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
    """MessagePack 响应装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        requ_body = mp.unpackb(request.get_data())
        start = time()
        resp_body = func(**requ_body)
        dur = int((time() - start) * 1000)
        return (
            mp.packb(resp_body),
            200,
            {
                "Content-Type": "application/x-msgpack",
                "Server-Timing": f"cpu;dur={dur}",
            },
        )

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
    """完整音频分析 (F0 + 频谱包络 + 非周期性)"""
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


@app.route("/pyworld/savefig", methods=["POST"])
def savefig():
    """生成音频分析图表"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    EPSILON = 1e-8

    requ_body = mp.unpackb(request.get_data())
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
    thread = Thread(target=open_browser, args=(host, port), daemon=True)
    thread.start()
    app.run(host=host, port=port)


if __name__ == "__main__":
    main()

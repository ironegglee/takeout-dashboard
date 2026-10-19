"""真正的工作 wrapper：启动 gen_data_v4.py 并同步等待它完成。"""
import os
import sys
import subprocess
import threading
import time

import socket
WORKDIR = r"C:\Users\CYYS\WorkBuddy\2026-06-16-11-25-31"
PY = r"C:\Users\CYYS\.workbuddy\binaries\python\envs\default\Scripts\python.exe"
LOG = os.path.join(WORKDIR, "_gen_run.log")
EXC = os.path.join(WORKDIR, "_gen_exception.txt")
PID_FILE = os.path.join(WORKDIR, "_gen_pid.txt")
LOCK = os.path.join(WORKDIR, "_gen.lock")


def _pid_alive(pid):
    try:
        r = subprocess.run(["tasklist", "/FI", f"PID eq {pid}"],
                           capture_output=True, text=True, timeout=20)
        return str(pid) in r.stdout
    except Exception:
        return True  # 查不到就当作活着，避免误抢


# ── 互斥锁：本环境的「一次调用会被执行两遍」，两个 gen 同时读 700MB Excel 会 IO 抢占卡死
#    （2026-09-21 跑 2h47m、2026-10-19 跑 1h44m 仍未完成，都是这个原因）
#    用 127.0.0.1 固定端口做锁：bind 是原子的，不存在「读到空锁文件」的竞态
_LOCK_PORT = 59123
_lock_sock = None


def _take_lock():
    global _lock_sock
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
    try:
        s.bind(("127.0.0.1", _LOCK_PORT))
        s.listen(1)
    except OSError:
        s.close()
        print("另一个 gen 正在运行（端口锁已被占用），本次跳过")
        sys.exit(0)
    _lock_sock = s
    try:
        with open(LOCK, "w") as f:
            f.write(str(os.getpid()))
    except OSError:
        pass


_take_lock()

if os.path.exists(EXC):
    try:
        os.remove(EXC)
    except OSError:
        pass

env = os.environ.copy()
env["PYTHONIOENCODING"] = "utf-8"
env["PYTHONUTF8"] = "1"
env["PYTHONUNBUFFERED"] = "1"

ts = time.strftime("%Y-%m-%d %H:%M:%S")
with open(LOG, "w", encoding="utf-8", errors="replace") as f:
    f.write(f"=== START gen_data_v4.py @ {ts} ===\n")
    f.flush()

try:
    proc = subprocess.Popen(
        [PY, "-X", "utf8", "-u", "gen_data_v4.py"],
        cwd=WORKDIR,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=False,
        bufsize=0,
    )
except Exception as e:
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"\n=== Popen FAILED: {type(e).__name__}: {e} ===\n")
    try:
        os.remove(LOCK)
    except OSError:
        pass
    sys.exit(99)

with open(PID_FILE, "w") as f:
    f.write(str(proc.pid))
with open(LOG, "a", encoding="utf-8") as f:
    f.write(f"=== PID: {proc.pid} ===\n")
    f.flush()

# 同步读取所有输出（流式）
try:
    while True:
        chunk = proc.stdout.read(8192)
        if not chunk:
            if proc.poll() is not None:
                break
            continue
        try:
            text = chunk.decode("utf-8", errors="replace")
        except Exception:
            text = chunk.decode("latin-1", errors="replace")
        with open(LOG, "a", encoding="utf-8", errors="replace") as f:
            f.write(text)
            f.flush()
except Exception as e:
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"\n=== READ EXCEPTION: {type(e).__name__}: {e} ===\n")

retcode = proc.wait()
with open(LOG, "a", encoding="utf-8") as f:
    f.write(f"\n=== END retcode={retcode} (after {time.strftime('%H:%M:%S')}) ===\n")
    f.flush()

try:
    os.remove(LOCK)
except OSError:
    pass
if _lock_sock:
    try:
        _lock_sock.close()
    except OSError:
        pass
sys.exit(retcode)

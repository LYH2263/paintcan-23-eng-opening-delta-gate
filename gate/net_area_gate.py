#!/usr/bin/env python3
"""加洞净面积回落门禁（net-area regression gate）。

前置：API 已起（docker compose up --build，默认 http://localhost:9500，
可用环境变量 API_BASE 覆盖）。

调用顺序（固定）：
  1. health             GET  /api/health
  2. seed-room-detail   GET  /api/rooms -> 按名字找客厅 -> GET /api/rooms/{id}
  3. baseline-estimate  POST /api/estimate (persist=false) 净面积 == 钉选值
  4. add-window         POST /api/rooms/{id}/openings 新增已知宽高的窗
  5. reduced-estimate   POST /api/estimate (persist=false) 净面积严格回落，
                        且下降量 == 窗宽*窗高
  6. delete-window      DELETE /api/openings/{opening_id}
  7. restored-estimate  POST /api/estimate (persist=false) 净面积回到钉选值

任一步失败：打印 [GATE FAIL] step=<步骤名> 并以非零码退出。
脚本只读引擎结果，不改引擎公式，不改种子尺寸。
"""
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

API_BASE = os.environ.get("API_BASE", "http://localhost:9500").rstrip("/")
BASELINE_PATH = Path(__file__).resolve().parent / "living_room_baseline.json"

# 已知宽高的测试用窗（不得与种子开洞同尺寸，避免误删）
WINDOW = {"kind": "window", "w": 1.2, "h": 1.0}

STEP = "startup"


def fail(msg):
    print(f"[GATE FAIL] step={STEP}: {msg}", file=sys.stderr)
    sys.exit(1)


def req(method, path, body=None):
    url = API_BASE + path
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, method=method,
                               headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(r, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        fail(f"{method} {path} -> HTTP {e.code}: {e.read().decode()[:200]}")
    except urllib.error.URLError as e:
        fail(f"{method} {path} -> {e.reason}（API 未起？先 docker compose up --build）")


def eq2(a, b):
    """按引擎口径（保留两位小数）比较。"""
    return abs(round(float(a), 2) - round(float(b), 2)) < 1e-9


def estimate_net(room_id):
    est = req("POST", "/api/estimate", {"room_id": room_id, "persist": False})
    if est.get("run_id") is not None:
        fail("估漆必须不落库（persist=false 却返回 run_id）")
    return float(est["net_m2"])


def main():
    global STEP

    STEP = "health"
    req("GET", "/api/health")

    STEP = "baseline-file"
    pinned = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    room_name, pinned_net = pinned["room_name"], float(pinned["net_m2"])

    STEP = "seed-room-detail"
    rooms = req("GET", "/api/rooms")["items"]
    match = [r for r in rooms if r["name"] == room_name]
    if len(match) != 1:
        fail(f"种子房间 {room_name!r} 应恰有一个，实际 {len(match)} 个")
    room_id = match[0]["id"]
    detail = req("GET", f"/api/rooms/{room_id}")
    seeded = [(o["kind"], o["w"], o["h"]) for o in detail["openings"]]
    if ("window", WINDOW["w"], WINDOW["h"]) in [(k, float(w), float(h)) for k, w, h in seeded]:
        fail("测试窗尺寸与既有开洞冲突，请换 WINDOW 尺寸")

    STEP = "baseline-estimate"
    net0 = estimate_net(room_id)
    if not eq2(net0, pinned_net):
        fail(f"净面积 {net0} != 钉选值 {pinned_net}")

    added_id = None
    try:
        STEP = "add-window"
        created = req("POST", f"/api/rooms/{room_id}/openings", WINDOW)
        added_id = created["id"]

        STEP = "reduced-estimate"
        net1 = estimate_net(room_id)
        if not net1 < net0:
            fail(f"加洞后净面积 {net1} 未严格小于钉选值 {net0}")
        drop = round(net0 - net1, 2)
        expect = round(WINDOW["w"] * WINDOW["h"], 2)
        if not eq2(drop, expect):
            fail(f"下降量 {drop} != 窗宽*窗高 {expect}")
    finally:
        if added_id is not None:
            STEP = "delete-window"
            req("DELETE", f"/api/openings/{added_id}")

    STEP = "restored-estimate"
    net2 = estimate_net(room_id)
    if not eq2(net2, pinned_net):
        fail(f"删洞后净面积 {net2} 未回到钉选值 {pinned_net}")

    print(f"[GATE OK] 基线 {net0} -> 加窗 {net1}（回落 {drop}）-> 删窗复原 {net2}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""加洞净面积回落门禁（对运行中的 Paintcan API 做整链断言）。

前置：API 已起（docker compose up --build，默认 http://localhost:9500）。
可用环境变量 PAINTCAN_BASE_URL 覆盖地址。

链路（三次估漆均 persist=false，不落库）：
  1. 读种子「客厅」详情并估漆，净面积须等于仓库钉选值 PINNED_NET_M2；
  2. 经开洞接口为该房新增一扇已知宽高的窗，再次估漆：
     净面积须严格减小，且下降量恰为 窗宽 × 窗高；
  3. 删除该窗后第三次估漆，净面积须回到钉选值。

任一步失败即以非零码退出并点名失败步骤。本脚本只调 HTTP 接口，
不改引擎公式，也不改种子尺寸。
"""
import json
import os
import sys
import urllib.error
import urllib.request

BASE = os.environ.get("PAINTCAN_BASE_URL", "http://localhost:9500").rstrip("/")
ROOM_NAME = "客厅"

# 仓库钉选的客厅净面积：seed.py 中 5.0×4.0×2.8 的墙毛面积 50.40，
# 减门 0.9×2.1 与窗 1.5×1.4（合计 3.99）= 46.41；
# 同一数值钉在 backend/app/tests/test_calc.py。
PINNED_NET_M2 = 46.41

# 本次门禁新增窗的已知宽高（面积 1.56 m²），与种子洞口尺寸均不相同。
WIN_W, WIN_H = 1.2, 1.3
WIN_AREA = round(WIN_W * WIN_H, 2)

TOL = 1e-6


def call(method, path, payload=None):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        BASE + path, data=data, method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:300]
        raise AssertionError(f"{method} {path} -> HTTP {e.code}: {body}")
    except urllib.error.URLError as e:
        raise AssertionError(f"{method} {path} -> 无法连接 API（{BASE}）：{e.reason}")


def fail(step, msg):
    print(f"[FAIL] 步骤 {step}: {msg}", file=sys.stderr)
    sys.exit(1)


def run_step(name, fn):
    try:
        result = fn()
    except SystemExit:
        raise
    except Exception as e:
        fail(name, repr(e))
    print(f"[PASS] 步骤 {name}")
    return result


def estimate(room_id):
    """一次不落库估漆；persist=false 时 run_id 必须为 null。"""
    r = call("POST", "/api/estimate",
             {"room_id": room_id, "persist": False})
    if r.get("run_id") is not None:
        raise AssertionError(f"persist=false 却落库产生 run_id={r.get('run_id')}")
    return float(r["net_m2"])


def main():
    # 步骤 0：API 必须已就绪
    def s_api_health():
        h = call("GET", "/api/health")
        if h.get("ok") is not True:
            raise AssertionError(f"health 响应异常: {h}")
    run_step("api_health", s_api_health)

    # 步骤 1：定位种子客厅，读取房间详情
    room_id = {"v": None}
    openings0 = {"v": None}

    def s_load_living_room():
        items = call("GET", "/api/rooms")["items"]
        room = next((r for r in items if r["name"] == ROOM_NAME), None)
        if room is None:
            raise AssertionError(f"房间列表中找不到种子房间「{ROOM_NAME}」: {items}")
        room_id["v"] = room["id"]
        detail = call("GET", f"/api/rooms/{room_id['v']}")
        dims = detail["room"]
        if (dims["length"], dims["width"], dims["height"]) != (5.0, 4.0, 2.8):
            raise AssertionError(f"客厅种子尺寸与钉选基准不符: {dims}")
        openings0["v"] = detail["openings"]
    run_step("load_living_room_detail", s_load_living_room)
    rid = room_id["v"]
    base_count = len(openings0["v"])

    # 步骤 2：首次不落库估漆，净面积须等于钉选值
    def s_baseline_estimate():
        net = estimate(rid)
        if abs(net - PINNED_NET_M2) > TOL:
            raise AssertionError(
                f"基线净面积 {net} != 钉选净面积 {PINNED_NET_M2}")
    run_step("baseline_estimate_equals_pinned_net", s_baseline_estimate)

    # 步骤 3：新增一扇已知宽高的窗
    new_id = {"v": None}

    def s_add_window():
        r = call("POST", f"/api/rooms/{rid}/openings",
                 {"kind": "window", "w": WIN_W, "h": WIN_H})
        o = r["opening"]
        if (o["w"], o["h"]) != (WIN_W, WIN_H):
            raise AssertionError(f"新窗尺寸回显不符: {o}")
        new_id["v"] = o["id"]
    run_step("add_known_window", s_add_window)

    # 步骤 4：第二次估漆——净面积严格减小，下降量恰为窗宽×窗高
    def s_estimate_drops_by_window_area():
        net = estimate(rid)
        if not (net < PINNED_NET_M2):
            raise AssertionError(f"加窗后净面积 {net} 未严格小于钉选值 {PINNED_NET_M2}")
        drop = round(PINNED_NET_M2 - net, 2)
        if abs(drop - WIN_AREA) > TOL:
            raise AssertionError(
                f"净面积下降量 {drop} != 窗面积 宽{WIN_W}×高{WIN_H}={WIN_AREA}")
    run_step("estimate_drops_strictly_by_window_area", s_estimate_drops_by_window_area)

    # 步骤 5：删除该窗
    def s_delete_window():
        call("DELETE", f"/api/openings/{new_id['v']}")
        detail = call("GET", f"/api/rooms/{rid}")
        if any(o["id"] == new_id["v"] for o in detail["openings"]):
            raise AssertionError("删除后房间详情中仍能查到该窗")
        if len(detail["openings"]) != base_count:
            raise AssertionError(
                f"删除后洞口数 {len(detail['openings'])} != 基线 {base_count}")
    run_step("delete_window", s_delete_window)

    # 步骤 6：第三次估漆——净面积回到钉选值
    def s_estimate_restored():
        net = estimate(rid)
        if abs(net - PINNED_NET_M2) > TOL:
            raise AssertionError(
                f"删窗后净面积 {net} 未回到钉选值 {PINNED_NET_M2}")
    run_step("estimate_restored_to_pinned_net", s_estimate_restored)

    print(f"[ALL PASS] 加洞净面积回落门禁通过，钉选净面积 {PINNED_NET_M2} m²，"
          f"窗洞 {WIN_W}×{WIN_H}={WIN_AREA} m²")


if __name__ == "__main__":
    main()

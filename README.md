# 16-paintcan（刷墙涂料）

Paintcan — 墙面积 − 门窗开洞；按涂布率与遍数换升数

## 启动

```bash
docker compose up --build
```

| 入口 | 地址 |
| --- | --- |
| 前端 | http://localhost:4500 |
| API | http://localhost:9500 |

## 主链

房间墙面减门窗 → 涂料升数 → 用量清单

## 门禁：加洞净面积回落

`gate/net_area_gate.py` 对**已启动的 API** 做整链回归：加洞后净面积必须按窗宽×窗高精确回落，删洞后必须复原。

**前置**：须已起 API（`docker compose up --build`，默认 http://localhost:9500；可用 `API_BASE` 环境变量覆盖）。

```bash
python3 gate/net_area_gate.py
```

固定调用顺序（任一步失败即非零退出并点名步骤名）：

1. `health` — `GET /api/health`
2. `seed-room-detail` — `GET /api/rooms` 按名找客厅 → `GET /api/rooms/{id}`
3. `baseline-estimate` — `POST /api/estimate`（`persist=false`，不落库）断言净面积 == 钉选值
4. `add-window` — `POST /api/rooms/{id}/openings` 新增已知宽高（1.2×1.0）的窗
5. `reduced-estimate` — 再次不落库估漆：净面积严格小于钉选值，且下降量 == 窗宽×窗高
6. `delete-window` — `DELETE /api/openings/{opening_id}`
7. `restored-estimate` — 第三次不落库估漆：净面积回到钉选值

钉选值在 `gate/living_room_baseline.json`：客厅净面积 **46.41 m²**，由种子尺寸推出（毛墙 2×(5.0+4.0)×2.8=50.40，减门 0.9×2.1 与窗 1.5×1.4 共 3.99）。门禁只断言引擎输出，不改引擎公式、不改种子尺寸。

## 技术栈

Python 3.12 + FastAPI + SQLite；Vue 3 + Vite + Nginx。

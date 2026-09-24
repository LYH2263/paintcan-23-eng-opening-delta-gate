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

## 加洞净面积回落门禁

门禁脚本 `scripts/net_area_gate.py` 对运行中的 API 做整链断言，
只读/写业务接口，不改引擎公式，也不改种子尺寸。

### 前置：须已起 API

```bash
docker compose up --build      # API 见 http://localhost:9500
```

未用 compose 时，等价的本地起服方式：

```bash
cd backend && PYTHONPATH=. uvicorn app.main:app --host 127.0.0.1 --port 9500
```

API 地址可用 `PAINTCAN_BASE_URL` 覆盖（默认 `http://localhost:9500`）。

### 调用顺序

```bash
python3 scripts/net_area_gate.py
```

脚本按序执行，任一步失败即以非零码退出并点名失败步骤：

1. `GET /api/health` —— 确认 API 已起；
2. `GET /api/rooms`、`GET /api/rooms/{id}` —— 定位种子「客厅」并读详情；
3. `POST /api/estimate`（`persist:false`，不落库）—— 净面积须等于
   仓库钉选值 **46.41 m²**（毛墙 50.40 − 门 1.89 − 窗 2.10）；
4. `POST /api/rooms/{id}/openings` —— 新增一扇已知宽高的窗 1.2×1.3；
5. 再次 `POST /api/estimate`（不落库）—— 净面积须**严格小于** 46.41，
   且下降量恰为窗面积 1.2×1.3 = **1.56 m²**；
6. `DELETE /api/openings/{opening_id}` —— 删除该窗；
7. 第三次 `POST /api/estimate`（不落库）—— 净面积须回到 **46.41 m²**。

脚本自清理（删回新增窗），可连续重复运行。

## 技术栈

Python 3.12 + FastAPI + SQLite；Vue 3 + Vite + Nginx。

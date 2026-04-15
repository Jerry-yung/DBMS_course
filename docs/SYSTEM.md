# 系统说明

## 1. 系统定位

基于 **MongoDB** 的在线问卷系统：支持注册登录、问卷 CRUD、题型（单选/多选/文本/数字）、跳转规则、短码分发、公开填写与答卷统计导出。

## 2. 技术栈

| 层次 | 技术 |
|------|------|
| 后端 | Python 3、FastAPI、Motor（异步 MongoDB 驱动） |
| 数据 | MongoDB |
| 认证 | JWT（python-jose）、bcrypt（passlib） |
| 前端 | 静态 HTML/CSS/JS，经 FastAPI `StaticFiles` 挂载 |
| 测试 | pytest、httpx（TestClient） |

## 3. 逻辑架构

```text
浏览器 (frontend/)
    ↓ HTTP
FastAPI (app/main.py)
    ├── /api/v1/*  REST API（app/api/v1/）
    ├── 业务服务层（app/services/）
    └── Motor → MongoDB（集合见 docs/DATABASE.md）
```

- **鉴权**：除注册/登录与 `/public/*` 外，问卷管理类接口需 `Authorization: Bearer <token>`。
- **填写端**：通过问卷 `short_code` 访问 `/public/surveys/{code}` 等接口；会话用 `session_id`（前端生成 UUID）区分匿名填写。

## 4. 代码与静态资源目录（提交时可打包）

| 路径 | 说明 |
|------|------|
| `app/` | 后端应用：入口 `main.py`，路由 `api/v1/`，配置 `core/config.py`，数据访问 `db/mongo.py` |
| `app/models/` | 领域模型与索引定义（`indexes.py`） |
| `app/schemas/` | Pydantic 请求/响应模型 |
| `app/services/` | 业务逻辑（问卷、题目、填写、跳转引擎、校验、统计等） |
| `frontend/` | 登录/注册、列表、编辑、填写、统计等静态页 |
| `scripts/init_db.py` | 创建索引（运行前执行） |
| `requirements.txt` | Python 依赖 |
| `.env.example` | 环境变量模板 |
| `pytest.ini`、`tests/` | 自动化测试 |

题库、版本与跨问卷统计的业务规则见 `docs/QUESTION_BANK.md`；REST 见 `docs/API.md` 中 `/question-library` 与 `POST .../questions/from-library`。

**说明**：MongoDB 为无模式数据库，字段约定见 `docs/DATABASE.md` 与代码中的写入逻辑；索引以 `app/models/indexes.py` + `scripts/init_db.py` 为准。

## 5. 运行与配置

详见项目根目录 [`README.md`](../README.md)：虚拟环境、`pip install`、复制 `.env`、`init_db.py`、`uvicorn`。

验收入口：

- 站点根路径：`http://127.0.0.1:8000/`
- OpenAPI：`http://127.0.0.1:8000/docs`

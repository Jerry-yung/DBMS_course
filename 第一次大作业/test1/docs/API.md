# API 说明

基础路径：`/api/v1`。认证：`Authorization: Bearer <access_token>`。

统一响应：`{ "code": 200, "message": "success", "data": { ... } }`。错误时 HTTP 状态码 4xx/5xx，`detail` 中含 `code`、`message`。

## 认证

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/auth/register` | 注册 `{ username, password }` |
| POST | `/auth/login` | 登录，返回 `access_token` |
| GET | `/auth/me` | 当前用户 |

## 问卷（需登录）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/surveys` | 创建 |
| GET | `/surveys` | 我的列表 |
| GET | `/surveys/{id}` | 详情 |
| PUT | `/surveys/{id}` | 更新 |
| DELETE | `/surveys/{id}` | 删除 |
| POST | `/surveys/{id}/publish` | 发布（有跳转环则失败） |
| POST | `/surveys/{id}/close` | 关闭 |

## 题目（需登录）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/surveys/{id}/questions` | 列表 |
| POST | `/surveys/{id}/questions` | 添加 |
| PUT | `/surveys/{id}/questions/{qid}` | 更新 |
| DELETE | `/surveys/{id}/questions/{qid}` | 删除 |
| POST | `/surveys/{id}/questions/reorder` | `{ "question_ids": [...] }` |

## 跳转规则（需登录）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/surveys/{id}/jump-rules` | 添加 |
| GET | `/surveys/{id}/jump-rules` | 列表 |
| PUT | `/surveys/{id}/jump-rules/{rule_id}` | 更新 |
| DELETE | `/surveys/{id}/jump-rules/{rule_id}` | 删除 |

请求体中 `condition` 示例：

- 无条件跳转：`{ "type": "always", "params": {} }`（答完源题即跳转到目标题）。
- 选项等于：`{ "type": "option_match", "params": { "option_value": "A" } }`。
- 其它数值/多选条件见 `docs/LOGIC.md`。

## 公开填写

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/public/surveys/{code}` | 问卷信息与首题 |
| GET | `/public/surveys/{code}/next?session_id=` | 下一题（服务端会话） |
| POST | `/public/surveys/{code}/answer` | `{ session_id, question_id, value }` |
| POST | `/public/surveys/{code}/submit` | `{ session_id }` |

可选请求头：`Authorization: Bearer ...`（登录用户填写时绑定 `user_id`，用于防重复）。

## 统计（需登录）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/surveys/{id}/statistics` | 全卷统计 |
| GET | `/surveys/{id}/statistics/{qid}` | 单题 |
| GET | `/surveys/{id}/export?format=json|csv` | 导出统计；`csv` 列为中文「题目、题型、统计项、统计值」；表头下一行为整卷 **总人数（total_responses）**；其后各题统计，选择题展示选项文案，UTF-8 带 BOM |

OpenAPI：`http://localhost:8000/docs`（启动服务后）。

## 相关文档

- 系统架构与目录：`docs/SYSTEM.md`
- 库表与索引：本文档同目录 `DATABASE.md`
- 跳转/校验/填写等细节：`docs/LOGIC.md`

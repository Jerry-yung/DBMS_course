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
| POST | `/surveys/{id}/questions/from-library` | 草稿问卷从题库复制一题：`{ "library_question_id" }` |

已发布/已关闭问卷：**不可** `PUT`/`DELETE` 题目，**不可** `POST` 新增题目（仅可 `reorder`）。规则见 `docs/QUESTION_BANK.md`。

## 题库与共享（需登录）

前缀：`/question-library`。

### 库题版本

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/question-library/items` | 新建首版本（`title,type,required,options,validation`，**必填** `bank_ids: string[]` 至少一个，创建后自动加入对应题库） |
| GET | `/question-library/items` | 本人拥有 + 被共享的库题列表（每条含 `owner_id`、`lineage_id` 等，便于前端区分「我的 / 共享」） |
| GET | `/question-library/items/{id}` | 详情（需可读权限） |
| POST | `/question-library/items/{id}/versions` | 基于该版本新建下一版本（完整新内容 + **必填** `bank_ids`，新版本自动加入所选题库） |
| POST | `/question-library/items/{id}/restore-as-new` | 以该版本内容为模板再插入新版本 |
| POST | `/question-library/items/from-survey-question` | `{ survey_id, question_id, bank_ids }` 将问卷题目保存为库题并**同时**加入所选题库（`bank_ids` 至少一个） |

### 家族 lineage（版本链 / 使用方 / 跨卷统计）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/question-library/lineages/{lineage_id}/versions` | 版本历史 |
| GET | `/question-library/lineages/{lineage_id}/usage` | 当前用户名下问卷中引用该家族的题目 |
| GET | `/question-library/lineages/{lineage_id}/cross-statistics` | 跨问卷合并统计（仅统计本人创建的问卷） |

### 共享

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/question-library/shares` | `{ grantee_username, lineage_id }` |
| GET | `/question-library/shares/outgoing` | 我发出的共享 |
| GET | `/question-library/shares/incoming` | 共享给我的 |
| DELETE | `/question-library/shares/{share_id}` | 撤销（仅发起者） |

### 题库集合（容器）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/question-library/banks` | `{ title, description? }`；`title` 不能为空，且同一用户下不可重复 |
| GET | `/question-library/banks` | 列表 |
| GET | `/question-library/banks/{id}` | 详情 |
| PUT | `/question-library/banks/{id}` | 更新 |
| DELETE | `/question-library/banks/{id}` | 删除（含条目） |
| POST | `/question-library/banks/{id}/items` | `{ library_question_id }` 入池（按该题 `lineage_id` 去重；同一题库不可重复保存同一道题） |
| DELETE | `/question-library/banks/{id}/items/{library_question_id}` | 移出 |
| GET | `/question-library/banks/{id}/items` | 条目列表（按 `lineage_id` 关联并返回该题当前最新版本快照） |

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

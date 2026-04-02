# 数据库设计说明

数据库名由环境变量 `MONGODB_DB` 指定（默认 `questionnaire_system`）。

## 集合与主要字段（逻辑 Schema）

MongoDB 无强制表结构，以下为应用读写所依赖的字段约定。

### users

| 字段 | 说明 |
|------|------|
| `_id` | ObjectId |
| `username` | 登录名，唯一 |
| `password` | bcrypt 哈希 |
| `email` | 可选，稀疏唯一 |
| `created_at` | 创建时间 |

### surveys

| 字段 | 说明 |
|------|------|
| `_id` | ObjectId，API 中序列化为字符串 `id` |
| `title` / `description` | 标题与说明 |
| `creator_id` | 创建者用户 ID 字符串 |
| `short_code` | 8 位左右随机字符，**全局唯一**，用于公开填写 URL |
| `status` | `draft` / `published` / `closed` 分别表示 创建未发布 / 已发布 / 已关闭 |
| `settings` | `allow_multiple`、`allow_anonymous`、`deadline`、`thank_you_message` 等 |
| `question_order` | 题目 ID 字符串数组，顺序即默认出题顺序 |
| `total_responses` | 完成份数等业务计数 |
| `created_at` / `published_at` / `closed_at` | 时间戳 |

### questions

| 字段 | 说明 |
|------|------|
| `_id` | ObjectId → 字符串 `id` |
| `survey_id` | 所属问卷 ID 字符串 |
| `order` | 排序序号 |
| `type` | `single_choice` / `multiple_choice` / `text` / `number` |
| `title` / `required` | 题干与是否必答 |
| `options` | 选择题：`[{ value, label, order }, ...]` |
| `validation` | 题型相关校验参数（见校验服务） |

### jump_rules

| 字段 | 说明 |
|------|------|
| `survey_id` | 问卷 ID 字符串 |
| `source_question_id` / `target_question_id` | 源题、目标题 ID |
| `condition` | `{ type, params }`，`type` 含 `always`、`option_match` 等（见 `docs/LOGIC.md`） |
| `priority` | 整数，越大越优先 |
| `enabled` | 是否启用 |

### responses

| 字段 | 说明 |
|------|------|
| `survey_id` | 问卷 ID 字符串 |
| `user_id` | 可选，登录填写时绑定 |
| `session_id` | 匿名/会话维度 UUID 字符串 |
| `answers` | `[{ question_id, value }, ...]`，`value` 标量或数组（多选） |
| `status` | `in_progress` / `completed` |
| `completed_at` 等 | 提交与时间相关字段 |

## 集合总览

| 集合 | 说明 |
|------|------|
| users | 用户，`password` 为 bcrypt 哈希 |
| surveys | 问卷，`short_code` 唯一，`creator_id` 为创建者字符串 ID，`question_order` 为题序 |
| questions | 题目，`survey_id` 关联问卷字符串 ID |
| jump_rules | 跳转规则，`source_question_id` / `target_question_id` 为题 ID 字符串 |
| responses | 填写记录，`answers` 为 `{ question_id, value }` 数组，`status`: `in_progress` / `completed` |

## 索引

逻辑定义见 `app/models/indexes.py`。初始化脚本 `scripts/init_db.py` 会创建用户名唯一、短码唯一、常用查询复合索引等。

另对 `responses` 建立**部分唯一索引**（仅 `status=completed`）：

- `(survey_id, user_id)`：`user_id` 非空时，同一用户同一问卷仅一条完成记录（配合业务 `allow_multiple`）。
- `(survey_id, session_id)`：`session_id` 非空时同理。

开发前请执行：`python scripts/init_db.py`（在 `test1` 目录下，已配置 `PYTHONPATH` 或通过 `sys.path` 的脚本自处理）。

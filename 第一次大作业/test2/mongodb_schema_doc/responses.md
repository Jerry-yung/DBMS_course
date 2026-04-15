# 集合：responses（填写记录）

存储答卷进度与答案。实现见 `app/services/fill_service.py` 等。

## 存储约定

- `survey_id`、`user_id`、`answers[].question_id` 为 **字符串**；`user_id` 可省略或为 `null`（匿名）。
- `session_id` 为 **UUID 字符串**（匿名/会话维度）。
- 防重复提交：对 **`status: "completed"`** 建立两条 **部分唯一索引**（见下），由 `scripts/init_db.py` 创建，**不在** `RESPONSE_INDEXES` 常量列表中重复声明。

## 示例文档

```javascript
{
  "_id": ObjectId("65b1c2d3e4f5a6b7c8d9e0f6"),
  "survey_id": "65b1c2d3e4f5a6b7c8d9e0f1",
  "user_id": "65a1b2c3d4e5f6a7b8c9d0e2",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "answers": [
    { "question_id": "65b1c2d3e4f5a6b7c8d9e0f2", "value": "B" },
    { "question_id": "65b1c2d3e4f5a6b7c8d9e0f3", "value": ["A", "C"] },
    { "question_id": "65b1c2d3e4f5a6b7c8d9e0f4", "value": "这是一段文本回答" },
    { "question_id": "65b1c2d3e4f5a6b7c8d9e0f5", "value": 25 }
  ],
  "status": "completed",
  "completed_at": ISODate("2024-01-21T15:30:00Z"),
  "ip_address": "192.168.1.100",
  "user_agent": "Mozilla/5.0...",
  "fill_duration": 125,
  "created_at": ISODate("2024-01-21T15:28:00Z"),
  "updated_at": ISODate("2024-01-21T15:30:00Z")
}
```

## 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `_id` | ObjectId | 答卷记录主键 |
| `survey_id` | string | 问卷 id |
| `user_id` | string / null | 登录用户 id；匿名时为 null |
| `session_id` | string | 会话 id（UUID） |
| `answers` | array | `{ question_id, value }`；`value` 为标量或数组（多选） |
| `status` | string | `in_progress` / `completed` |
| `completed_at` | date | 完成时间 |
| `fill_duration` | number | 填写耗时（秒）等 |
| `ip_address` / `user_agent` | string | 可选 |

## 索引

### 常规（`RESPONSE_INDEXES`）

```javascript
db.responses.createIndex({ survey_id: 1, status: 1, completed_at: -1 })
db.responses.createIndex({ "answers.question_id": 1 })
db.responses.createIndex({ completed_at: -1 })
```

### 部分唯一（与 `init_db.py` 一致）

仅在 `status === "completed"` 时生效，用于同一问卷下已完成记录去重（配合业务 `allow_multiple`）：

```javascript
db.responses.createIndex(
  { survey_id: 1, user_id: 1 },
  {
    unique: true,
    partialFilterExpression: {
      status: "completed",
      user_id: { $ne: null },
    },
    name: "uniq_survey_user_completed",
  }
)
db.responses.createIndex(
  { survey_id: 1, session_id: 1 },
  {
    unique: true,
    partialFilterExpression: {
      status: "completed",
      session_id: { $ne: null },
    },
    name: "uniq_survey_session_completed",
  }
)
```

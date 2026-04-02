# 集合：responses（填写记录集合）

存储用户提交的问卷答案。

## 示例文档

```javascript
// responses 集合
{
  "_id": ObjectId("65b1c2d3e4f5a6b7c8d9e0f6"),
  "survey_id": ObjectId("65b1c2d3e4f5a6b7c8d9e0f1"),
  "user_id": ObjectId("65a1b2c3d4e5f6a7b8c9d0e2"),  // 填写者ID，匿名时为null
  "session_id": "abc123xyz",                         // 未登录用户的会话标识
  "answers": [
    {
      "question_id": ObjectId("65b1c2d3e4f5a6b7c8d9e0f2"),
      "value": "B"                                    // 单选题：选项值
    },
    {
      "question_id": ObjectId("65b1c2d3e4f5a6b7c8d9e0f3"),
      "value": ["A", "C"]                             // 多选题：选项值数组
    },
    {
      "question_id": ObjectId("65b1c2d3e4f5a6b7c8d9e0f4"),
      "value": "这是一段文本回答"                      // 文本题：字符串
    },
    {
      "question_id": ObjectId("65b1c2d3e4f5a6b7c8d9e0f5"),
      "value": 25                                     // 数字题：数值
    }
  ],
  "status": "completed",              // in_progress | completed
  "completed_at": ISODate("2024-01-21T15:30:00Z"),
  "ip_address": "192.168.1.100",
  "user_agent": "Mozilla/5.0...",
  "fill_duration": 125,               // 填写耗时（秒）
  "created_at": ISODate("2024-01-21T15:28:00Z"),
  "updated_at": ISODate("2024-01-21T15:30:00Z")
}
```

## 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `_id` | ObjectId | 填写记录唯一标识 |
| `survey_id` | ObjectId | 所属问卷 ID |
| `user_id` | ObjectId | 填写者 ID，匿名时为 null |
| `session_id` | string | 未登录用户会话标识，用于跟踪匿名填写 |
| `answers` | array | 答案数组，按提交顺序存储 |
| `answers[].question_id` | ObjectId | 题目 ID |
| `answers[].value` | mixed | 答案值，类型根据题型而定 |
| `status` | string | in_progress(填写中)/completed(已完成) |
| `completed_at` | date | 完成时间 |
| `fill_duration` | number | 填写耗时（秒），用于分析 |
| `ip_address` | string | 填写者 IP |
| `user_agent` | string | 浏览器信息 |

## 索引

```javascript
// 防重复提交检查（同一用户同一问卷只能提交一次，如果 allow_multiple=false）
db.responses.createIndex(
  { "survey_id": 1, "user_id": 1, "completed_at": 1 },
  { partialFilterExpression: { "user_id": { $ne: null } } }
)

// 匿名用户防重复
db.responses.createIndex(
  { "survey_id": 1, "session_id": 1, "completed_at": 1 }
)

// 统计查询优化
db.responses.createIndex({ "survey_id": 1, "status": 1, "completed_at": -1 })

// 按题目统计（支持快速查询某题目的所有答案）
db.responses.createIndex({ "answers.question_id": 1 })

// 按时间范围查询
db.responses.createIndex({ "completed_at": -1 })
```

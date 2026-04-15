# 集合：surveys（问卷）

存储问卷元数据与配置。实现见 `app/services/survey_service.py` 等。

## 存储约定

- `creator_id`、`question_order[]` 中题目 id 在业务层均为 **字符串**（与 API `id` 一致），**不是**嵌套的 `ObjectId` 类型字段。

## 示例文档

```javascript
{
  "_id": ObjectId("65b1c2d3e4f5a6b7c8d9e0f1"),
  "title": "2024年度员工满意度调查",
  "description": "请根据您的真实感受填写，我们将严格保密",
  "creator_id": "65a1b2c3d4e5f6a7b8c9d0e1",
  "short_code": "S7xK9mP2",
  "status": "published",
  "settings": {
    "allow_anonymous": false,
    "allow_multiple": true,
    "deadline": ISODate("2024-12-31T23:59:59Z"),
    "thank_you_message": "感谢您的参与！"
  },
  "question_order": [
    "65b1c2d3e4f5a6b7c8d9e0f2",
    "65b1c2d3e4f5a6b7c8d9e0f3",
    "65b1c2d3e4f5a6b7c8d9e0f4"
  ],
  "total_responses": 128,
  "created_at": ISODate("2024-01-20T09:00:00Z"),
  "published_at": ISODate("2024-01-21T10:00:00Z"),
  "closed_at": null
}
```

## 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `_id` | ObjectId | 问卷主键；API 序列化为字符串 `id` |
| `title` / `description` | string | 标题与说明 |
| `creator_id` | string | 创建者用户 id |
| `short_code` | string | 随机短字符串，**全局唯一**，公开填写 URL |
| `status` | string | `draft` / `published` / `closed` |
| `settings` | object | `allow_anonymous`、`allow_multiple`、`deadline`、`thank_you_message` 等 |
| `question_order` | string[] | 题目 id 有序列表，与 `questions` 对应 |
| `total_responses` | number | 完成份数等冗余计数 |
| `created_at` / `published_at` / `closed_at` | date | 时间戳 |

## 索引

见 `app/models/indexes.py` 中 `SURVEY_INDEXES`，与 [indexes.mongodb.js](./indexes.mongodb.js) 中 `surveys` 段一致。

```javascript
db.surveys.createIndex({ creator_id: 1, status: 1 })
db.surveys.createIndex({ short_code: 1 }, { unique: true })
db.surveys.createIndex({ status: 1, created_at: -1 })
db.surveys.createIndex({ "settings.deadline": 1 })
```

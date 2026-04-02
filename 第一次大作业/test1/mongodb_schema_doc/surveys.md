# 集合：surveys（问卷集合）

存储问卷的基本信息和配置。

## 示例文档

```javascript
// surveys 集合
{
  "_id": ObjectId("65b1c2d3e4f5a6b7c8d9e0f1"),
  "title": "2024年度员工满意度调查",
  "description": "请根据您的真实感受填写，我们将严格保密",
  "creator_id": ObjectId("65a1b2c3d4e5f6a7b8c9d0e1"),
  "short_code": "S7xK9mP2",          // 问卷访问短码，如 /s/S7xK9mP2
  "status": "published",              // draft | published | closed
  "settings": {
    "allow_anonymous": false,         // 是否允许匿名填写（需求要求填写需登录，故false）
    "allow_multiple": true,           // 是否允许同一人多次填写
    "deadline": ISODate("2024-12-31T23:59:59Z"),
    "thank_you_message": "感谢您的参与！"
  },
  "question_order": [                 // 题目顺序（保持题目顺序）
    ObjectId("65b1c2d3e4f5a6b7c8d9e0f2"),
    ObjectId("65b1c2d3e4f5a6b7c8d9e0f3"),
    ObjectId("65b1c2d3e4f5a6b7c8d9e0f4")
  ],
  "total_responses": 128,             // 总填写次数（冗余字段，避免每次count）
  "created_at": ISODate("2024-01-20T09:00:00Z"),
  "published_at": ISODate("2024-01-21T10:00:00Z"),
  "closed_at": null
}
```

## 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `_id` | ObjectId | 问卷唯一标识 |
| `title` | string | 问卷标题，必填 |
| `description` | string | 问卷说明/导语 |
| `creator_id` | ObjectId | 创建者 ID，关联 users |
| `short_code` | string | 6-8位随机短码，用于生成访问链接 |
| `status` | string | 状态：draft(草稿)/published(已发布)/closed(已关闭) |
| `settings` | object | 问卷配置项 |
| `settings.allow_anonymous` | boolean | 是否允许匿名（需求要求填写需登录，故false） |
| `settings.allow_multiple` | boolean | 是否允许同一用户多次填写 |
| `settings.deadline` | date | 截止时间，null表示无限制 |
| `question_order` | array | 题目 ID 有序数组，维护题目顺序 |
| `total_responses` | number | 冗余字段，缓存填写次数，避免频繁聚合查询 |
| `published_at` | date | 发布时间 |
| `closed_at` | date | 关闭时间 |

## 索引

```javascript
db.surveys.createIndex({ "creator_id": 1, "status": 1 })
db.surveys.createIndex({ "short_code": 1 }, { unique: true })
db.surveys.createIndex({ "status": 1, "created_at": -1 })
db.surveys.createIndex({ "settings.deadline": 1 })
```

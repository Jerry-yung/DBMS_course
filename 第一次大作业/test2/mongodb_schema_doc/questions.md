# 集合：questions（问卷内题目）

存储某张问卷下的题目实例。实现见 `app/services/question_service.py`。

## 存储约定

- `survey_id` 为 **字符串**。
- 从题库选用时写入：`lineage_id`（题库家族）、`source_library_version_id`（当时选用的 `library_questions._id`）。

## 示例文档

```javascript
{
  "_id": ObjectId("65b1c2d3e4f5a6b7c8d9e0f2"),
  "survey_id": "65b1c2d3e4f5a6b7c8d9e0f1",
  "title": "您的年龄段是？",
  "type": "single_choice",
  "required": true,
  "order": 1,
  "options": [
    { "value": "A", "label": "18岁以下", "order": 1 },
    { "value": "B", "label": "18-25岁", "order": 2 },
    { "value": "C", "label": "26-35岁", "order": 3 },
    { "value": "D", "label": "36岁以上", "order": 4 }
  ],
  "validation": {
    "min_select": 1,
    "max_select": 3,
    "exact_select": null,
    "min_length": null,
    "max_length": null,
    "min_value": null,
    "max_value": null,
    "integer_only": null,
    "pattern": null
  },
  "has_jump_rules": true,
  "lineage_id": null,
  "source_library_version_id": null,
  "created_at": ISODate("2024-01-20T09:05:00Z"),
  "updated_at": ISODate("2024-01-20T09:05:00Z")
}
```

## 题型示例：单选题 (single_choice)

```javascript
{
  "type": "single_choice",
  "options": [
    { "value": "A", "label": "男", "order": 1 },
    { "value": "B", "label": "女", "order": 2 }
  ],
  "validation": {}
}
```

## 题型示例：多选题 (multiple_choice)

```javascript
{
  "type": "multiple_choice",
  "options": [
    { "value": "A", "label": "苹果", "order": 1 },
    { "value": "B", "label": "香蕉", "order": 2 },
    { "value": "C", "label": "西瓜", "order": 3 }
  ],
  "validation": {
    "min_select": 1,
    "max_select": 2,
    "exact_select": null
  }
}
```

## 题型示例：文本 (text)

```javascript
{
  "type": "text",
  "options": [],
  "validation": {
    "min_length": 2,
    "max_length": 100,
    "pattern": null
  }
}
```

## 题型示例：数字 (number)

```javascript
{
  "type": "number",
  "options": [],
  "validation": {
    "min_value": 0,
    "max_value": 120,
    "integer_only": true
  }
}
```

## 索引

见 `app/models/indexes.py` 中 `QUESTION_INDEXES`。

```javascript
db.questions.createIndex({ survey_id: 1, order: 1 })
db.questions.createIndex({ survey_id: 1, has_jump_rules: 1 })
db.questions.createIndex({ type: 1 })
db.questions.createIndex({ lineage_id: 1 })
db.questions.createIndex({ source_library_version_id: 1 })
```

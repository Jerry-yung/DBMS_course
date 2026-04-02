# 集合：questions（题目集合）

存储问卷中的具体题目。

## 示例文档

```javascript
// questions 集合
{
  "_id": ObjectId("65b1c2d3e4f5a6b7c8d9e0f2"),
  "survey_id": ObjectId("65b1c2d3e4f5a6b7c8d9e0f1"),
  "title": "您的年龄段是？",
  "type": "single_choice",            // single_choice | multiple_choice | text | number
  "required": true,
  "order": 1,
  "options": [                        // 单选/多选题的选项
    { "value": "A", "label": "18岁以下", "order": 1 },
    { "value": "B", "label": "18-25岁", "order": 2 },
    { "value": "C", "label": "26-35岁", "order": 3 },
    { "value": "D", "label": "36岁以上", "order": 4 }
  ],
  "validation": {                     // 校验规则（根据题型使用不同字段）
    // 多选题专用
    "min_select": 1,
    "max_select": 3,
    "exact_select": null,
    // 文本题专用
    "min_length": null,
    "max_length": null,
    // 数字题专用
    "min_value": null,
    "max_value": null,
    "integer_only": null,
    // 通用
    "pattern": null
  },
  "has_jump_rules": true,             // 是否作为跳转源，优化查询性能
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

## 题型示例：文本填空 (text)

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

## 题型示例：数字填空 (number)

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

```javascript
db.questions.createIndex({ "survey_id": 1, "order": 1 })
db.questions.createIndex({ "survey_id": 1, "has_jump_rules": 1 })
db.questions.createIndex({ "type": 1 })
```

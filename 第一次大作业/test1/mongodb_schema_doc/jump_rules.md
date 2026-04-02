# 集合：jump_rules（跳转规则集合）

存储问卷的跳转逻辑。

## 示例文档

```javascript
// jump_rules 集合
{
  "_id": ObjectId("65b1c2d3e4f5a6b7c8d9e0f5"),
  "survey_id": ObjectId("65b1c2d3e4f5a6b7c8d9e0f1"),
  "source_question_id": ObjectId("65b1c2d3e4f5a6b7c8d9e0f2"),  // 条件源题目
  "target_question_id": ObjectId("65b1c2d3e4f5a6b7c8d9e0f4"),  // 跳转目标题目
  "condition": {
    "type": "option_match",           // 见下表
    "params": {
      "option_value": "A"             // 单选跳转：选项值匹配
    }
  },
  "priority": 10,                     // 优先级，数字越大优先级越高
  "enabled": true,
  "created_at": ISODate("2024-01-20T10:00:00Z"),
  "updated_at": ISODate("2024-01-20T10:00:00Z")
}
```

## 条件类型详解

| condition.type | params 结构 | 示例 |
|----------------|-------------|------|
| `always` | `{}` | 答完源题即跳转（实现扩展，无条件） |
| `option_match` | `{ "option_value": "A" }` | 单选选A时跳转 |
| `option_contains` | `{ "option_values": ["苹果", "香蕉"] }` | 多选包含苹果或香蕉时跳转 |
| `value_equal` | `{ "value": 18 }` | 数字填空等于18时跳转 |
| `value_greater` | `{ "value": 18 }` | 数字填空大于18时跳转 |
| `value_less` | `{ "value": 18 }` | 数字填空小于18时跳转 |
| `value_between` | `{ "min": 18, "max": 30 }` | 数字填空在18-30之间时跳转 |

## 多条件跳转示例（可选扩展）

```javascript
{
  "condition": {
    "operator": "AND",               // AND | OR
    "conditions": [
      { "type": "option_match", "params": { "option_value": "A" } },
      { "type": "value_greater", "params": { "value": 18 } }
    ]
  }
}
```

## 索引

```javascript
db.jump_rules.createIndex({ "survey_id": 1, "source_question_id": 1 })
db.jump_rules.createIndex({ "survey_id": 1, "priority": -1 })
db.jump_rules.createIndex({ "enabled": 1 })
```

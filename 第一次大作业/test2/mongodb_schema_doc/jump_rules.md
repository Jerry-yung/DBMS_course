# 集合：jump_rules（跳转规则）

存储问卷内题目间的跳转规则。实现见 `app/services/jump_engine.py` 及发布前环检测逻辑。

## 存储约定

- `survey_id`、`source_question_id`、`target_question_id` 均为 **字符串**（题目 id 与问卷 id 的字符串形式）。

## 示例文档

```javascript
{
  "_id": ObjectId("65b1c2d3e4f5a6b7c8d9e0f5"),
  "survey_id": "65b1c2d3e4f5a6b7c8d9e0f1",
  "source_question_id": "65b1c2d3e4f5a6b7c8d9e0f2",
  "target_question_id": "65b1c2d3e4f5a6b7c8d9e0f4",
  "condition": {
    "type": "option_match",
    "params": { "option_value": "A" }
  },
  "priority": 10,
  "enabled": true,
  "created_at": ISODate("2024-01-20T10:00:00Z"),
  "updated_at": ISODate("2024-01-20T10:00:00Z")
}
```

## 条件类型（当前实现）

`evaluate_condition` / `get_next_question` 仅处理 **单层** `condition: { type, params }`。支持类型包括：

| condition.type | params 说明 |
|----------------|-------------|
| `always` | 通常 `{}`，答完源题即跳转 |
| `option_match` | 如 `{ "option_value": "A" }` |
| `option_contains` | 如 `{ "option_values": ["苹果", "香蕉"] }` |
| `value_equal` / `value_greater` / `value_less` / `value_between` | 数字题，见 `jump_engine.py` |

**未实现**：多条件 AND/OR 嵌套（如下结构）；若文档中出现，当前代码路径**不会**按嵌套解析。

```javascript
// 非当前引擎入参
{
  "condition": {
    "operator": "AND",
    "conditions": [
      { "type": "option_match", "params": { "option_value": "A" } }
    ]
  }
}
```

## 索引

见 `app/models/indexes.py` 中 `JUMP_RULE_INDEXES`。

```javascript
db.jump_rules.createIndex({ survey_id: 1, source_question_id: 1 })
db.jump_rules.createIndex({ survey_id: 1, priority: -1 })
db.jump_rules.createIndex({ enabled: 1 })
```

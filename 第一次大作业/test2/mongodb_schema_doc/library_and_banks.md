# 题库相关集合

题库版本、共享、题库容器与入池条目。实现见 `app/services/library_question_service.py`、`app/services/question_bank_service.py`；业务规则见 `docs/QUESTION_BANK.md`。

---

## library_questions（库题版本，不可变）

每做一次内容修订 **插入新文档**；同一逻辑题家族共享 `lineage_id`，`parent_version_id` 指上一版本。

```javascript
{
  "_id": ObjectId("..."),
  "owner_id": "65a1b2c3d4e5f6a7b8c9d0e1",
  "lineage_id": "65b1c2d3e4f5a6b7c8d9e099",
  "parent_version_id": null,
  "title": "你的年龄",
  "type": "single_choice",
  "required": true,
  "options": [{ "value": "A", "label": "18 以下", "order": 0 }],
  "validation": {},
  "created_at": ISODate("...")
}
```

**索引**：`app/models/indexes.py` → `LIBRARY_QUESTION_INDEXES`。

---

## question_shares（按家族共享）

将某 `lineage_id` 授权给其他用户选用（服务层校验 ACL）。

```javascript
{
  "_id": ObjectId("..."),
  "grantor_id": "65a...",
  "grantee_id": "65b...",
  "lineage_id": "65c...",
  "created_at": ISODate("...")
}
```

**索引**：`QUESTION_SHARE_INDEXES`。

---

## question_banks（题库容器）

| 字段 | 说明 |
|------|------|
| `owner_id` | 所有者用户 id（字符串） |
| `title` / `description` | 名称与说明；同一 `owner_id` 下 `title` **唯一**（唯一索引） |
| `preset_kind` | 可选。值为 `shared_inbox` 时表示系统预置 **「共享库」**：不可删除、不可改名，描述固定，见 `question_bank_service.py` |
| `created_at` | 创建时间 |

```javascript
{
  "_id": ObjectId("..."),
  "owner_id": "65a...",
  "title": "常用题",
  "description": "",
  "created_at": ISODate("...")
}
```

预置共享库示例（由服务端 `ensure_shared_inbox_bank` 创建）：

```javascript
{
  "owner_id": "65a...",
  "title": "共享库",
  "description": "来自其他人的共享，本库不可删除",
  "preset_kind": "shared_inbox",
  "created_at": ISODate("...")
}
```

**索引**：`QUESTION_BANK_INDEXES`。

---

## question_bank_items（题库入池条目）

以 **`lineage_id`** 入池：同一 `(bank_id, lineage_id)` 唯一；列表展示时取该家族 **最新** `library_questions` 快照（若设置了 `display_library_question_id` 则可钉选展示版本）。

| 字段 | 说明 |
|------|------|
| `bank_id` | 题库 id（字符串） |
| `lineage_id` | 题目家族 id |
| `added_at` | 入池时间 |
| `display_library_question_id` | 可选；钉选本题库详情中展示的版本 id；为空则跟随最新版 |

```javascript
{
  "_id": ObjectId("..."),
  "bank_id": "65a...",
  "lineage_id": "65b...",
  "added_at": ISODate("..."),
  "display_library_question_id": null
}
```

**索引**：`QUESTION_BANK_ITEM_INDEXES`。

---

## 索引汇总脚本

与 [indexes.mongodb.js](./indexes.mongodb.js) 中 `library_questions` / `question_shares` / `question_banks` / `question_bank_items` 段一致。

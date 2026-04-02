# MongoDB Schema 文档包

本目录对应《完整报告》**完整 Schema 定义**（及同章内各集合索引说明），按集合拆分为独立文件，便于提交与版本管理。

| 文件 | 内容 |
|------|------|
| [users.md](./users.md) | 集合 `users` 示例文档、字段表、索引 |
| [surveys.md](./surveys.md) | 集合 `surveys` |
| [questions.md](./questions.md) | 集合 `questions`（含各题型示例） |
| [jump_rules.md](./jump_rules.md) | 集合 `jump_rules`（条件类型与扩展说明） |
| [responses.md](./responses.md) | 集合 `responses` |
| [indexes.mongodb.js](./indexes.mongodb.js) | 汇总 `createIndex`（mongosh 可 `load` 或粘贴；与报告 §2 索引一致） |
| [集合关系图.png](./集合关系图.png) | 集合关系图 |

**索引执行**：日常开发推荐仍使用仓库内 `python scripts/init_db.py`（与 `app/models/indexes.py` 同步）。`indexes.mongodb.js` 便于对照报告或手工在 shell 中建索引。

## 与实现代码的说明

报告中的示例大量使用 **ObjectId** 表示外键；当前 `test1` 实现里，API 与业务层对问卷/题目等多使用 **字符串形式的 ObjectId**（与 `docs/DATABASE.md` 一致）。语义一致，仅序列化形态不同，查库时均为 BSON ObjectId 或兼容字符串。

跳转条件类型在实现中另支持 **`always`（无条件）**，见 [jump_rules.md](./jump_rules.md) 补充行。

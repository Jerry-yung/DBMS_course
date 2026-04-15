# MongoDB Schema 文档包

本目录描述 **test2 当前实现** 中的集合字段约定与索引，与 `docs/DATABASE.md`、`app/models/indexes.py`、`scripts/init_db.py` 保持一致。

## 文件一览

| 文件 | 内容 |
|------|------|
| [users.md](./users.md) | 集合 `users` |
| [surveys.md](./surveys.md) | 集合 `surveys` |
| [questions.md](./questions.md) | 集合 `questions`（含各题型示例） |
| [jump_rules.md](./jump_rules.md) | 集合 `jump_rules` |
| [responses.md](./responses.md) | 集合 `responses`（含部分唯一索引说明） |
| [library_and_banks.md](./library_and_banks.md) | `library_questions`、`question_shares`、`question_banks`、`question_bank_items` |
| [indexes.mongodb.js](./indexes.mongodb.js) | 与 `init_db.py` 等价的 `createIndex`（mongosh 可 `load`） |
| [集合关系图.png](./集合关系图.png) | 集合关系示意（若有） |

## 实现约定（必读）

1. **数据库名**：环境变量 `MONGODB_DB`，默认 `questionnaire_system`（见 `app/core/config.py`）。
2. **外键形态**：除文档 `_id` 为 BSON `ObjectId` 外，业务层写入的 `creator_id`、`survey_id`、`question_id` 等在与 API 交互时均为 **字符串**（24 位十六进制字符串）；落库可为字符串或与驱动兼容形式，**与 `docs/DATABASE.md` 一致**。
3. **建索引**：以 **`python scripts/init_db.py`**（项目根目录）为准；索引列表来自 `app/models/indexes.py`，其中 `RESPONSE_UNIQUE_INDEXES` **未被** `init_db.py` 使用，防重复提交由脚本内两条 **partial unique** 实现（见 [responses.md](./responses.md) 与 `indexes.mongodb.js` 末尾）。
4. **跳转条件**：`jump_engine` 仅处理 **单层** `condition: { type, params }`；`always` 等类型见 `app/services/jump_engine.py`、`docs/LOGIC.md`。

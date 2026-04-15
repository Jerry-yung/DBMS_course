/**
 * 与仓库 `scripts/init_db.py` 行为一致（索引定义源：`app/models/indexes.py`）。
 * 使用：mongosh 中设置 dbName 与 .env 的 MONGODB_DB 一致后 load 本文件，或逐段粘贴。
 *
 * 说明：`app/models/indexes.py` 中的 `RESPONSE_UNIQUE_INDEXES` 未被 init_db 使用；
 * 防重复提交以本文件末尾两条「部分唯一索引」为准。
 */
const dbName = "questionnaire_system";
use(dbName);

// --- users ---
db.users.createIndex({ username: 1 }, { unique: true });
db.users.createIndex({ email: 1 }, { sparse: true, unique: true });
db.users.createIndex({ created_at: -1 });

// --- surveys ---
db.surveys.createIndex({ creator_id: 1, status: 1 });
db.surveys.createIndex({ short_code: 1 }, { unique: true });
db.surveys.createIndex({ status: 1, created_at: -1 });
db.surveys.createIndex({ "settings.deadline": 1 });

// --- questions ---
db.questions.createIndex({ survey_id: 1, order: 1 });
db.questions.createIndex({ survey_id: 1, has_jump_rules: 1 });
db.questions.createIndex({ type: 1 });
db.questions.createIndex({ lineage_id: 1 });
db.questions.createIndex({ source_library_version_id: 1 });

// --- jump_rules ---
db.jump_rules.createIndex({ survey_id: 1, source_question_id: 1 });
db.jump_rules.createIndex({ survey_id: 1, priority: -1 });
db.jump_rules.createIndex({ enabled: 1 });

// --- responses（常规查询，见 RESPONSE_INDEXES）---
db.responses.createIndex({ survey_id: 1, status: 1, completed_at: -1 });
db.responses.createIndex({ "answers.question_id": 1 });
db.responses.createIndex({ completed_at: -1 });

// --- library & banks ---
db.library_questions.createIndex({ owner_id: 1, created_at: -1 });
db.library_questions.createIndex({ lineage_id: 1, created_at: 1 });

db.question_shares.createIndex({ grantee_id: 1, lineage_id: 1 });
db.question_shares.createIndex({ grantor_id: 1 });
db.question_shares.createIndex(
  { grantee_id: 1, grantor_id: 1, lineage_id: 1 },
  { unique: true }
);

db.question_banks.createIndex({ owner_id: 1, created_at: -1 });
db.question_banks.createIndex({ owner_id: 1, title: 1 }, { unique: true });

db.question_bank_items.createIndex(
  { bank_id: 1, lineage_id: 1 },
  { unique: true }
);
db.question_bank_items.createIndex({ bank_id: 1, added_at: -1 });

// --- responses：部分唯一（与 init_db 一致，仅 status=completed）---
db.responses.createIndex(
  { survey_id: 1, user_id: 1 },
  {
    unique: true,
    partialFilterExpression: {
      status: "completed",
      user_id: { $ne: null },
    },
    name: "uniq_survey_user_completed",
  }
);
db.responses.createIndex(
  { survey_id: 1, session_id: 1 },
  {
    unique: true,
    partialFilterExpression: {
      status: "completed",
      session_id: { $ne: null },
    },
    name: "uniq_survey_session_completed",
  }
);

print("Indexes ensured on database: " + dbName);

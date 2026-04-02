/**
 * MongoDB 索引汇总（mongosh）
 * 先修改 dbName 与 .env MONGODB_DB 一致，再在 mongosh 中 load 本文件或逐段粘贴。
 */
const dbName = "questionnaire_system";
use(dbName);

db.users.createIndex({ username: 1 }, { unique: true });
db.users.createIndex({ email: 1 }, { sparse: true, unique: true });
db.users.createIndex({ created_at: -1 });

db.surveys.createIndex({ creator_id: 1, status: 1 });
db.surveys.createIndex({ short_code: 1 }, { unique: true });
db.surveys.createIndex({ status: 1, created_at: -1 });
db.surveys.createIndex({ "settings.deadline": 1 });

db.questions.createIndex({ survey_id: 1, order: 1 });
db.questions.createIndex({ survey_id: 1, has_jump_rules: 1 });
db.questions.createIndex({ type: 1 });

db.jump_rules.createIndex({ survey_id: 1, source_question_id: 1 });
db.jump_rules.createIndex({ survey_id: 1, priority: -1 });
db.jump_rules.createIndex({ enabled: 1 });

db.responses.createIndex(
  { survey_id: 1, user_id: 1, completed_at: 1 },
  { partialFilterExpression: { user_id: { $ne: null } } }
);
db.responses.createIndex({ survey_id: 1, session_id: 1, completed_at: 1 });
db.responses.createIndex({ survey_id: 1, status: 1, completed_at: -1 });
db.responses.createIndex({ "answers.question_id": 1 });
db.responses.createIndex({ completed_at: -1 });

print("Indexes ensured on database: " + dbName);

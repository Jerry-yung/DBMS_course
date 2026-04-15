"""MongoDB 索引定义"""

USER_INDEXES = [
    {"keys": [("username", 1)], "unique": True},
    {"keys": [("email", 1)], "sparse": True, "unique": True},
    {"keys": [("created_at", -1)]},
]

SURVEY_INDEXES = [
    {"keys": [("creator_id", 1), ("status", 1)]},
    {"keys": [("short_code", 1)], "unique": True},
    {"keys": [("status", 1), ("created_at", -1)]},
    {"keys": [("settings.deadline", 1)]},
]

QUESTION_INDEXES = [
    {"keys": [("survey_id", 1), ("order", 1)]},
    {"keys": [("survey_id", 1), ("has_jump_rules", 1)]},
    {"keys": [("type", 1)]},
    {"keys": [("lineage_id", 1)]},
    {"keys": [("source_library_version_id", 1)]},
]

LIBRARY_QUESTION_INDEXES = [
    {"keys": [("owner_id", 1), ("created_at", -1)]},
    {"keys": [("lineage_id", 1), ("created_at", 1)]},
]

QUESTION_SHARE_INDEXES = [
    {"keys": [("grantee_id", 1), ("lineage_id", 1)]},
    {"keys": [("grantor_id", 1)]},
    {
        "keys": [("grantee_id", 1), ("grantor_id", 1), ("lineage_id", 1)],
        "unique": True,
    },
]

QUESTION_BANK_INDEXES = [
    {"keys": [("owner_id", 1), ("created_at", -1)]},
    {"keys": [("owner_id", 1), ("title", 1)], "unique": True},
]

QUESTION_BANK_ITEM_INDEXES = [
    {"keys": [("bank_id", 1), ("lineage_id", 1)], "unique": True},
    {"keys": [("bank_id", 1), ("added_at", -1)]},
]

JUMP_RULE_INDEXES = [
    {"keys": [("survey_id", 1), ("source_question_id", 1)]},
    {"keys": [("survey_id", 1), ("priority", -1)]},
    {"keys": [("enabled", 1)]},
]

RESPONSE_INDEXES = [
    {"keys": [("survey_id", 1), ("status", 1), ("completed_at", -1)]},
    {"keys": [("answers.question_id", 1)]},
    {"keys": [("completed_at", -1)]},
]

# 未接入 init_db：防重复提交以 scripts/init_db.py 中两条 partial unique 为准（见 mongodb_schema_doc/responses.md）
RESPONSE_UNIQUE_INDEXES = [
    {
        "keys": [("survey_id", 1), ("user_id", 1), ("completed_at", 1)],
        "partialFilterExpression": {"user_id": {"$ne": None}}
    },
    {
        "keys": [("survey_id", 1), ("session_id", 1), ("completed_at", 1)]
    },
]
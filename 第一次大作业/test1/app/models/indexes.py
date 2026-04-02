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

# 可选：防重复提交索引（需要条件判断）
RESPONSE_UNIQUE_INDEXES = [
    {
        "keys": [("survey_id", 1), ("user_id", 1), ("completed_at", 1)],
        "partialFilterExpression": {"user_id": {"$ne": None}}
    },
    {
        "keys": [("survey_id", 1), ("session_id", 1), ("completed_at", 1)]
    },
]
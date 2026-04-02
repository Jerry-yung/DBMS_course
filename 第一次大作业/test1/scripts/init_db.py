"""Create MongoDB indexes. Run from test1: python scripts/init_db.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pymongo import MongoClient

from app.core.config import settings
from app.models.indexes import (
    JUMP_RULE_INDEXES,
    QUESTION_INDEXES,
    RESPONSE_INDEXES,
    SURVEY_INDEXES,
    USER_INDEXES,
)


def _create_indexes(collection, specs):
    for spec in specs:
        keys = spec["keys"]
        kwargs = {k: v for k, v in spec.items() if k != "keys"}
        collection.create_index(keys, **kwargs)


def main():
    client = MongoClient(settings.mongodb_url)
    db = client[settings.mongodb_db]

    _create_indexes(db["users"], USER_INDEXES)
    _create_indexes(db["surveys"], SURVEY_INDEXES)
    _create_indexes(db["questions"], QUESTION_INDEXES)
    _create_indexes(db["jump_rules"], JUMP_RULE_INDEXES)
    _create_indexes(db["responses"], RESPONSE_INDEXES)

    # Partial unique for completed responses: one completion per user/session per survey
    db["responses"].create_index(
        [("survey_id", 1), ("user_id", 1)],
        unique=True,
        partialFilterExpression={
            "status": "completed",
            "user_id": {"$ne": None},
        },
        name="uniq_survey_user_completed",
    )
    db["responses"].create_index(
        [("survey_id", 1), ("session_id", 1)],
        unique=True,
        partialFilterExpression={
            "status": "completed",
            "session_id": {"$ne": None},
        },
        name="uniq_survey_session_completed",
    )

    print("Indexes created OK.")
    client.close()


if __name__ == "__main__":
    main()

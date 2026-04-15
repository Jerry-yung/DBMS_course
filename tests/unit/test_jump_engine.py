from app.services.jump_engine import detect_cycle, evaluate_condition, get_next_question


def test_option_match():
    cond = {"type": "option_match", "params": {"option_value": "A"}}
    assert evaluate_condition(cond, "A") is True
    assert evaluate_condition(cond, "B") is False


def test_always_condition():
    cond = {"type": "always", "params": {}}
    assert evaluate_condition(cond, None) is True
    assert evaluate_condition(cond, "A") is True
    assert evaluate_condition(cond, 0) is True


def test_get_next_jump():
    order = ["q1", "q2", "q3"]
    rules = [
        {
            "source_question_id": "q1",
            "target_question_id": "q3",
            "condition": {"type": "option_match", "params": {"option_value": "X"}},
            "priority": 10,
            "enabled": True,
        }
    ]
    assert get_next_question(order, rules, None, {}) == "q1"
    assert (
        get_next_question(order, rules, "q1", {"q1": "X"}) == "q3"
    )
    assert get_next_question(order, rules, "q1", {"q1": "Y"}) == "q2"


def test_get_next_unconditional_always():
    order = ["q1", "q2", "q3"]
    rules = [
        {
            "source_question_id": "q1",
            "target_question_id": "q3",
            "condition": {"type": "always", "params": {}},
            "priority": 10,
            "enabled": True,
        }
    ]
    assert get_next_question(order, rules, "q1", {"q1": "A"}) == "q3"
    assert get_next_question(order, rules, "q1", {"q1": "Z"}) == "q3"


def test_detect_cycle():
    rules = [
        {
            "source_question_id": "a",
            "target_question_id": "b",
            "enabled": True,
        },
        {
            "source_question_id": "b",
            "target_question_id": "a",
            "enabled": True,
        },
    ]
    c = detect_cycle(rules)
    assert len(c) >= 1

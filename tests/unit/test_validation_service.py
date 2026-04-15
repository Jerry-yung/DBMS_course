from app.services import validation_service


def test_single_required():
    q = {"type": "single_choice", "required": True, "options": [{"value": "A", "label": "a"}]}
    ok, _ = validation_service.validate_answer(q, None)
    assert ok is False


def test_multiple_exact():
    q = {
        "type": "multiple_choice",
        "required": False,
        "options": [{"value": "A", "label": "a"}, {"value": "B", "label": "b"}],
        "validation": {"exact_select": 2},
    }
    ok, _ = validation_service.validate_answer(q, ["A"])
    assert ok is False
    ok, _ = validation_service.validate_answer(q, ["A", "B"])
    assert ok is True


def test_number_integer():
    q = {
        "type": "number",
        "required": True,
        "validation": {"integer_only": True, "min_value": 1, "max_value": 5},
    }
    ok, _ = validation_service.validate_answer(q, 3)
    assert ok is True
    ok, _ = validation_service.validate_answer(q, 3.5)
    assert ok is False

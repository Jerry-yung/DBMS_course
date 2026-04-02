import csv
import io

from app.services.statistic_service import export_csv


def _parse_csv_rows(s: str) -> list[list[str]]:
    # 解析前去掉 BOM，避免首列表头被污染
    raw = io.StringIO(s.lstrip("\ufeff"))
    return list(csv.reader(raw))


def test_export_csv_headers_and_bom():
    data = {
        "survey_id": "ignored",
        "total_responses": 5,
        "questions": [
            {
                "title": "Q1",
                "type": "single_choice",
                "options": [{"value": "A", "label": "是"}],
                "statistics": {"A": 2},
            }
        ],
    }
    out = export_csv(data)
    assert out.startswith("\ufeff")
    rows = _parse_csv_rows(out)
    assert rows[0] == ["题目", "题型", "统计项", "统计值"]
    assert rows[1] == ["（整卷汇总）", "—", "总人数（total_responses）", "5"]


def test_export_csv_total_responses_defaults_to_zero():
    data = {"survey_id": "x", "questions": []}
    rows = _parse_csv_rows(export_csv(data))
    assert rows[1] == ["（整卷汇总）", "—", "总人数（total_responses）", "0"]


def test_export_csv_single_choice_uses_option_label():
    data = {
        "survey_id": "x",
        "total_responses": 4,
        "questions": [
            {
                "title": "年龄",
                "type": "single_choice",
                "options": [
                    {"value": "A", "label": "18-25岁"},
                    {"value": "B", "label": "26-35岁"},
                ],
                "statistics": {"B": 1, "A": 3},
            }
        ],
    }
    rows = _parse_csv_rows(export_csv(data))[2:]
    # sorted keys: A before B
    assert rows[0] == ["年龄", "单选题", "18-25岁", "3"]
    assert rows[1] == ["年龄", "单选题", "26-35岁", "1"]


def test_export_csv_unknown_option_fallback():
    data = {
        "survey_id": "x",
        "total_responses": 1,
        "questions": [
            {
                "title": "T",
                "type": "single_choice",
                "options": [{"value": "A", "label": "仅A"}],
                "statistics": {"Z": 5},
            }
        ],
    }
    rows = _parse_csv_rows(export_csv(data))[2:]
    assert rows[0] == ["T", "单选题", "选项 Z", "5"]


def test_export_csv_text_and_number():
    data = {
        "survey_id": "x",
        "total_responses": 2,
        "questions": [
            {
                "title": "爱好",
                "type": "text",
                "options": [],
                "statistics": {"values": ["摄影", "健身"]},
            },
            {
                "title": "得分",
                "type": "number",
                "options": [],
                "statistics": {
                    "count": 2,
                    "avg": 4.5,
                    "min": 3,
                    "max": 6,
                    "values": [3, 6],
                },
            },
        ],
    }
    rows = _parse_csv_rows(export_csv(data))[2:]
    assert rows[0] == ["爱好", "文本题", "全部文本答案", "摄影;健身"]
    assert rows[1] == ["得分", "数字题", "作答人数", "2"]
    assert rows[2][:3] == ["得分", "数字题", "平均值"]
    assert float(rows[2][3]) == 4.5
    assert rows[3] == ["得分", "数字题", "最小值", "3"]
    assert rows[4] == ["得分", "数字题", "最大值", "6"]
    assert rows[5] == ["得分", "数字题", "全部数值", "3;6"]

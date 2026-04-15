import re
from typing import Any, Dict, List, Tuple, Union

AnswerValue = Union[str, int, float, List[Any], None]


def validate_answer(question: Dict[str, Any], answer: AnswerValue) -> Tuple[bool, str]:
    qtype = question.get("type", "")
    required = bool(question.get("required", False))
    val_rules = question.get("validation") or {}
    options = question.get("options") or []
    allowed_values = {o["value"] for o in options} if options else None

    if qtype == "single_choice":
        if answer is None or answer == "":
            if required:
                return False, "请选择一个选项"
            return True, ""
        if allowed_values is not None and str(answer) not in allowed_values:
            return False, "选项无效"
        return True, ""

    if qtype == "multiple_choice":
        if answer is None or answer == []:
            if required:
                return False, "请至少选择一个选项"
            return True, ""
        if not isinstance(answer, list):
            return False, "多选题答案格式无效"
        if allowed_values is not None:
            for a in answer:
                if str(a) not in allowed_values:
                    return False, "选项无效"
        n = len(answer)
        if val_rules.get("exact_select") is not None:
            ex = int(val_rules["exact_select"])
            if n != ex:
                return False, f"请选择{ex}个选项"
        if val_rules.get("min_select") is not None:
            mn = int(val_rules["min_select"])
            if n < mn:
                return False, f"请至少选择{mn}个选项"
        if val_rules.get("max_select") is not None:
            mx = int(val_rules["max_select"])
            if n > mx:
                return False, f"最多选择{mx}个选项"
        return True, ""

    if qtype == "text":
        s = "" if answer is None else str(answer)
        if (s == "" or s.strip() == "") and required:
            return False, "此项为必填"
        if s:
            if val_rules.get("min_length") is not None and len(s) < int(
                val_rules["min_length"]
            ):
                lo = int(val_rules["min_length"])
                hi = int(val_rules.get("max_length") or lo)
                return False, f"请输入{lo}-{hi}个字"
            if val_rules.get("max_length") is not None and len(s) > int(
                val_rules["max_length"]
            ):
                lo = int(val_rules.get("min_length") or 0)
                hi = int(val_rules["max_length"])
                return False, f"请输入{lo}-{hi}个字"
            pat = val_rules.get("pattern")
            if pat and not re.match(pat, s):
                return False, "格式不正确"
        return True, ""

    if qtype == "number":
        if answer is None or answer == "":
            if required:
                return False, "此项为必填"
            return True, ""
        try:
            num = float(answer)
        except (TypeError, ValueError):
            return False, "请输入有效数字"
        if val_rules.get("integer_only"):
            if int(num) != num:
                return False, "请输入整数"
        if val_rules.get("min_value") is not None and num < float(
            val_rules["min_value"]
        ):
            lo = val_rules["min_value"]
            hi = val_rules.get("max_value", lo)
            if val_rules.get("integer_only"):
                return False, f"请输入{int(lo)}-{int(hi)}之间的整数"
            return False, f"请输入{lo}-{hi}之间的数字"
        if val_rules.get("max_value") is not None and num > float(
            val_rules["max_value"]
        ):
            lo = val_rules.get("min_value", "")
            hi = val_rules["max_value"]
            if val_rules.get("integer_only"):
                return False, f"请输入{int(lo)}-{int(hi)}之间的整数"
            return False, f"请输入{lo}-{hi}之间的数字"
        return True, ""

    if required and (answer is None or answer == "" or answer == []):
        return False, "此项为必填"
    return True, ""

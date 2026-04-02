from collections import defaultdict
from typing import Any, Dict, List, Optional


def _answers_dict_from_list(answers_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {a["question_id"]: a.get("value") for a in answers_list}


def evaluate_condition(condition: Dict[str, Any], answer_value: Any) -> bool:
    ctype = condition.get("type")
    params = condition.get("params") or {}

    # 无条件：作答完源题后一律跳转到目标题（不依赖答案内容）
    if ctype == "always":
        return True

    if answer_value is None:
        return False

    if ctype == "option_match":
        return answer_value == params.get("option_value")

    if ctype == "option_contains":
        opts = params.get("option_values") or []
        if isinstance(answer_value, list):
            return any(o in answer_value for o in opts)
        return answer_value in opts

    if ctype == "value_equal":
        try:
            return float(answer_value) == float(params.get("value"))
        except (TypeError, ValueError):
            return False

    if ctype == "value_greater":
        try:
            return float(answer_value) > float(params.get("value"))
        except (TypeError, ValueError):
            return False

    if ctype == "value_less":
        try:
            return float(answer_value) < float(params.get("value"))
        except (TypeError, ValueError):
            return False

    if ctype == "value_between":
        try:
            v = float(answer_value)
            lo = float(params.get("min"))
            hi = float(params.get("max"))
            return lo <= v <= hi
        except (TypeError, ValueError):
            return False

    return False


def get_next_question(
    question_order: List[str],
    rules: List[Dict[str, Any]],
    current_qid: Optional[str],
    answers: Dict[str, Any],
) -> Optional[str]:
    if not question_order:
        return None

    if current_qid is None:
        return question_order[0]

    enabled_rules = [r for r in rules if r.get("enabled", True)]
    enabled_rules.sort(key=lambda r: r.get("priority", 0), reverse=True)

    for rule in enabled_rules:
        if rule.get("source_question_id") != current_qid:
            continue
        ans = answers.get(current_qid)
        cond = rule.get("condition") or {}
        if evaluate_condition(cond, ans):
            tid = rule.get("target_question_id")
            if tid:
                return tid

    try:
        idx = question_order.index(current_qid)
    except ValueError:
        return None
    if idx + 1 < len(question_order):
        return question_order[idx + 1]
    return None


def detect_cycle(rules: List[Dict[str, Any]]) -> List[List[str]]:
    graph: Dict[str, List[str]] = defaultdict(list)
    nodes: set = set()
    for r in rules:
        if not r.get("enabled", True):
            continue
        s = r.get("source_question_id")
        t = r.get("target_question_id")
        if not s or not t:
            continue
        graph[s].append(t)
        nodes.add(s)
        nodes.add(t)

    cycles: List[List[str]] = []
    visited: set = set()
    rec_stack: List[str] = []
    in_stack: set = set()

    def dfs(u: str) -> None:
        visited.add(u)
        rec_stack.append(u)
        in_stack.add(u)
        for v in graph.get(u, []):
            if v not in visited:
                dfs(v)
            elif v in in_stack:
                i = rec_stack.index(v)
                cycles.append(rec_stack[i:] + [])
        rec_stack.pop()
        in_stack.remove(u)

    for n in list(nodes):
        if n not in visited:
            dfs(n)
    return cycles

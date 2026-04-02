# 关键逻辑说明

## 1. 下一题与跳转（`app/services/jump_engine.py`）

- **题序**：以问卷文档中的 `question_order`（题目 ID 列表）为顺序基准。
- **规则匹配**：仅处理 `enabled=true` 的规则；按 `priority` **降序**遍历；源题为当前题 `source_question_id` 时，若 `evaluate_condition(condition, 当前题答案)` 为真，则下一题为 `target_question_id`。
- **条件类型**（`condition.type`）：
  - `always`：**无条件**，答完源题即匹配（不依赖答案取值）。
  - `option_match`：单选答案等于 `params.option_value`。
  - `option_contains`：多选答案（数组）与 `params.option_values` 有交集。
  - `value_equal` / `value_greater` / `value_less` / `value_between`：数字题与 `params` 中数值比较。
- **默认顺序**：若无规则命中，下一题为 `question_order` 中当前题的下一项。
- **发布校验**：`publish` 前对跳转规则构图做 **环检测**（`detect_cycle`）；存在环则拒绝发布。

## 2. 答案校验（`app/services/validation_service.py`）

按题型读取题目上的 `required`、`options`、`validation`（如多选 `min_select`/`max_select`/`exact_select`，文本 `min_length`/`max_length`，数字 `min_value`/`max_value`/`integer_only`）。  
公开接口 `POST .../answer` 在写入前校验；与前端表单规则应对齐。

## 3. 填写流程（`app/services/fill_service.py`）

1. 客户端为每次填写生成 `session_id`（UUID），随请求传递。
2. `GET .../public/surveys/{code}` 取问卷元数据；`GET .../next` 根据已有 `answers` 与跳转规则计算下一题。
3. `POST .../answer` 校验后追加或覆盖该题答案，再计算下一题。
4. `POST .../submit` 将答卷标为 `completed`；结合 `settings.allow_multiple` 与索引/业务逻辑限制重复完成（登录用户可绑定 `user_id`）。

## 4. 统计与导出（`app/services/statistic_service.py`）

- 仅统计 `responses` 中 `status=completed` 的记录。
- 单选/多选：聚合各选项出现次数。
- 文本：收集 `values` 列表。
- 数字：`count` / `avg` / `min` / `max` 及原始值列表。
- **CSV 导出**：列为中文「题目、题型、统计项、统计值」；第二行输出整卷 **总人数（total_responses）**；其后按题目分行；选择题将选项代号映射为 `options[].label`；文件带 UTF-8 BOM 便于 Excel 打开。

## 5. 问卷生命周期

- `draft` → `POST publish`（无跳转环）→ `published` → `POST close` → `closed`。
- `DELETE /surveys/{id}` 级联删除关联题目、跳转规则、答卷（见 `survey_service.delete_survey`）。

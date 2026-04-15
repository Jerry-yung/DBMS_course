# 题库、版本与跨问卷统计 — 规则说明

## 1. 答卷锚点（不变量）

- `responses.answers[].question_id` **永远**指向问卷内集合 `questions` 的 `_id`（字符串形式）。
- 公开填写、校验、跳转、单卷统计均基于该 `question_id`，不因题库变更而改变历史答卷含义。

## 2. 题库题目（`library_questions`）

- 每个文档表示**一个不可变版本**（插入后不改 `title` / `type` / `options` / `validation`）。
- `lineage_id`：同一逻辑题家族的唯一标识，所有版本共享同一 `lineage_id`。
- `parent_version_id`：上一版本的 `library_questions._id`，用于版本链（v1→v2→v3）。
- **修改内容** = 基于某版本 **新建一条**文档（新版本），不覆盖旧 `_id`。
- **恢复旧版**：以某历史版本内容为模板 **再插入**新版本（保留完整版本链，不删除新版本）。

## 3. 问卷内题目（`questions`）与题库的关系

- 从题库选用时：将库题内容**复制**为新 `questions` 文档，并写入：
  - `lineage_id`：与库题一致，供跨问卷统计与「被哪些问卷使用」查询。
  - `source_library_version_id`：选用时的库题版本 ID。
- 直接在问卷里新建的题目可无 `lineage_id`（不参与按家族聚合，除非再「保存到题库」并后续选用带 lineage 的副本）。

## 4. 已发布 / 已关闭问卷的题目锁定

- 当 `surveys.status` 为 `published` 或 `closed` 时：
  - **禁止**对问卷内题目执行 `PUT` 更新（题干、选项、题型、校验、必答等均不可改）。
  - **禁止** `DELETE` 题目（避免答卷与跳转结构不一致）。
- **允许** `POST .../questions/reorder`：仅改变展示顺序，不改变各题 `_id` 与历史答卷对应关系。

## 5. 共享（`question_shares`）

- 按 `lineage_id` 授权：被共享用户可查看该家族全部版本，并可将**任意版本**选用到自己的问卷（仍复制为新的 `questions` 文档）。
- 共享不改变 `owner_id`；库题仍由所有者维护版本链。

## 6. 题库实体（`question_banks` / `question_bank_items`）

- 使用流程上需**先创建至少一个题库**，再通过接口新建库题或从问卷「保存到题库」：上述操作均要求请求体携带 `bank_ids`（至少一个本人题库），创建成功后自动写入 `question_bank_items`。
- `question_banks.title` 在同一 `owner_id` 下唯一（不可为空、不可重复）。
- 题库条目按 `lineage_id` 去重保存：同一题库中，同一道题（同 lineage）不能重复保存。
- 题库详情返回每个 lineage 对应的**当前最新版本**快照，因此当题目产生新版本时，题库展示会自动同步更新；历史版本仍通过 `GET /question-library/lineages/{lineage_id}/versions` 查询。

## 7. 跨问卷统计（按 `lineage_id`）

- 仅在当前用户**作为创建者**的问卷范围内，收集 `questions.lineage_id` 等于给定 `lineage_id` 的所有题目实例。
- 合并这些实例对应的已完成答卷答案。
- **选择题**：按 `answers.value`（选项 `value`）聚合；若不同问卷副本的选项 `value` 不一致，则视为不同桶（不在服务端强行按 label 合并）。
- 若同一 `lineage_id` 下题目副本出现**多种题型**，返回错误提示，避免错误合并。

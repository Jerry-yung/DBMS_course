(function () {
  requireLogin();
  const params = new URLSearchParams(location.search);
  const surveyId = params.get("id");
  if (!surveyId) {
    alert("缺少问卷 id");
    location.href = "/index.html";
    return;
  }

  let survey = null;
  let questions = [];
  let jumpRules = [];
  let sortMode = false;
  let editingQuestionId = null;
  let draggedCardId = null;

  const $ = (id) => document.getElementById(id);

  function toast(msg, type) {
    const el = $("toast");
    el.textContent = msg;
    el.className = type === "error" ? "error" : "success";
    el.classList.add("show");
    clearTimeout(el._t);
    el._t = setTimeout(() => el.classList.remove("show"), 3200);
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function isoToDatetimeLocal(iso) {
    if (!iso) return "";
    const d = new Date(iso);
    if (isNaN(d.getTime())) return "";
    const p = (n) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(
      d.getHours()
    )}:${p(d.getMinutes())}`;
  }

  function datetimeLocalToIso(val) {
    if (!val || !String(val).trim()) return null;
    const d = new Date(val);
    if (isNaN(d.getTime())) return null;
    return d.toISOString();
  }

  const TYPE_LABELS = {
    single_choice: "单选",
    multiple_choice: "多选",
    text: "填空",
    number: "数字",
  };

  const STATUS_LABELS = {
    draft: "草稿",
    published: "已发布",
    closed: "已关闭",
  };

  async function loadSurvey() {
    const res = await apiJson("/surveys/" + encodeURIComponent(surveyId));
    survey = res.data;
    $("title").value = survey.title || "";
    $("description").value = survey.description || "";
    const st = survey.settings || {};
    $("deadline").value = isoToDatetimeLocal(st.deadline);
    $("allowMultiple").checked = st.allow_multiple !== false;
    $("allowAnonymous").checked = !!st.allow_anonymous;
    $("thankYouMessage").value =
      st.thank_you_message || "感谢您的参与！";
    updateCharCount();
    renderToolbar();
  }

  function updateCharCount() {
    const n = $("title").value.length;
    $("charCount").textContent = n;
  }

  function renderToolbar() {
    if (!survey) return;
    $("toolbarTitle").textContent = survey.title || "未命名问卷";
    const st = survey.status || "draft";
    const badge = $("statusBadge");
    badge.className = "status-badge status-" + st;
    $("statusText").textContent = STATUS_LABELS[st] || st;
    const scRow = $("shortcodeRow");
    if (st === "published" || st === "closed") {
      scRow.classList.remove("hidden");
      $("shortcodeValue").textContent = survey.short_code || "";
    } else {
      scRow.classList.add("hidden");
    }
    const btnClose = $("btnCloseSurvey");
    if (btnClose) {
      if (st === "published") {
        btnClose.classList.remove("hidden");
      } else {
        btnClose.classList.add("hidden");
      }
    }
  }

  async function loadQuestions() {
    const res = await apiJson(
      "/surveys/" + encodeURIComponent(surveyId) + "/questions"
    );
    questions = Array.isArray(res.data) ? res.data : [];
    questions.sort((a, b) => (a.order || 0) - (b.order || 0));
    renderQuestionCards();
    await loadJumpRulesData();
    renderJumpRules();
  }

  function renderQuestionCards() {
    const container = $("questionsContainer");
    const empty = $("questionsEmpty");
    container.innerHTML = "";
    if (!questions.length) {
      empty.classList.remove("hidden");
      return;
    }
    empty.classList.add("hidden");
    questions.forEach((q, idx) => {
      const card = document.createElement("div");
      card.className = "question-card" + (sortMode ? " sort-mode" : "");
      card.dataset.questionId = q.id;
      card.draggable = false;
      const optsSummary =
        q.options && q.options.length
          ? q.options.map((o) => o.label || o.value).join(" · ")
          : "—";
      const val = q.validation || {};
      let valSummary = "";
      if (q.type === "multiple_choice") {
        if (val.exact_select != null)
          valSummary += `精确${val.exact_select}项 `;
        if (val.min_select != null) valSummary += `最少${val.min_select} `;
        if (val.max_select != null) valSummary += `最多${val.max_select} `;
      } else if (q.type === "text") {
        if (val.min_length != null || val.max_length != null)
          valSummary += `字数 ${val.min_length ?? "—"}–${val.max_length ?? "—"}`;
      } else if (q.type === "number") {
        if (val.min_value != null || val.max_value != null)
          valSummary += `范围 ${val.min_value ?? "—"}–${val.max_value ?? "—"}`;
        if (val.integer_only) valSummary += " 整数";
      }
      card.innerHTML = `
        <div class="drag-handle" title="${sortMode ? "拖动排序" : "开启排序模式后可拖动"}">⋮⋮</div>
        <div class="q-num">${idx + 1}</div>
        <span class="q-badge">${TYPE_LABELS[q.type] || q.type}</span>
        <div class="q-body">
          <div class="q-title">${escapeHtml(q.title || "")}</div>
          <div class="q-meta">${q.required ? "必答 · " : ""}选项：${escapeHtml(
        optsSummary
      )}${valSummary ? " · " + escapeHtml(valSummary) : ""}</div>
        </div>
        <div class="q-actions">
          <button type="button" class="icon-btn" data-act="edit" data-id="${escapeHtml(
        q.id
      )}">编辑</button>
          <button type="button" class="icon-btn" data-act="copy" data-id="${escapeHtml(
        q.id
      )}">复制</button>
          <button type="button" class="icon-btn danger" data-act="del" data-id="${escapeHtml(
        q.id
      )}">删除</button>
        </div>`;
      container.appendChild(card);
    });

    container.querySelectorAll("[data-act]").forEach((btn) => {
      btn.addEventListener("click", onQuestionAction);
    });

    if (sortMode) {
      container.querySelectorAll(".question-card").forEach(bindDrag);
    }
  }

  function bindDrag(card) {
    const handle = card.querySelector(".drag-handle");
    if (!handle) return;
    handle.draggable = true;
    handle.addEventListener("dragstart", (e) => {
      draggedCardId = card.dataset.questionId;
      card.classList.add("dragging");
      e.dataTransfer.effectAllowed = "move";
      e.dataTransfer.setData("text/plain", draggedCardId);
      e.stopPropagation();
    });
    handle.addEventListener("dragend", () => {
      card.classList.remove("dragging");
      draggedCardId = null;
    });
    card.addEventListener("dragover", (e) => {
      e.preventDefault();
      e.dataTransfer.dropEffect = "move";
    });
    card.addEventListener("drop", onDropCard);
  }

  function onDropCard(e) {
    e.preventDefault();
    const targetCard = e.currentTarget;
    const targetId = targetCard.dataset.questionId;
    if (!draggedCardId || draggedCardId === targetId) return;
    const container = $("questionsContainer");
    const cards = [...container.querySelectorAll(".question-card")];
    const dragEl = [...container.querySelectorAll(".question-card")].find(
      (c) => c.dataset.questionId === draggedCardId
    );
    if (!dragEl) return;
    const targetIdx = cards.indexOf(targetCard);
    const dragIdx = cards.indexOf(dragEl);
    if (dragIdx < targetIdx) {
      targetCard.after(dragEl);
    } else {
      targetCard.before(dragEl);
    }
    persistOrder();
  }

  async function persistOrder() {
    const container = $("questionsContainer");
    const ids = [...container.querySelectorAll(".question-card")].map(
      (c) => c.dataset.questionId
    );
    if (ids.length === 0) return;
    try {
      await apiJson(
        "/surveys/" + encodeURIComponent(surveyId) + "/questions/reorder",
        {
          method: "POST",
          body: JSON.stringify({ question_ids: ids }),
        }
      );
      await loadQuestions();
      toast("题目顺序已更新", "success");
    } catch (err) {
      toast(err.message, "error");
      await loadQuestions();
    }
  }

  async function onQuestionAction(e) {
    const btn = e.currentTarget;
    const id = btn.dataset.id;
    const act = btn.dataset.act;
    const q = questions.find((x) => x.id === id);
    if (!q && act !== "add") return;
    if (act === "edit") {
      openQuestionModal(q);
    } else if (act === "copy") {
      try {
        await apiJson(
          "/surveys/" + encodeURIComponent(surveyId) + "/questions",
          {
            method: "POST",
            body: JSON.stringify({
              title: (q.title || "") + "（副本）",
              type: q.type,
              required: !!q.required,
              options: q.options || [],
              validation: q.validation || {},
            }),
          }
        );
        toast("已复制题目", "success");
        await loadQuestions();
      } catch (err) {
        toast(err.message, "error");
      }
    } else if (act === "del") {
      if (!confirm("确定删除该题目？相关跳转规则也会被清理。")) return;
      try {
        await apiJson(
          "/surveys/" +
            encodeURIComponent(surveyId) +
            "/questions/" +
            encodeURIComponent(id),
          { method: "DELETE" }
        );
        toast("已删除", "success");
        await loadQuestions();
      } catch (err) {
        toast(err.message, "error");
      }
    }
  }

  async function loadJumpRulesData() {
    const res = await apiJson(
      "/surveys/" + encodeURIComponent(surveyId) + "/jump-rules"
    );
    jumpRules = Array.isArray(res.data) ? res.data : [];
  }

  function questionOptionsHtml(selectedId) {
    let h = '<option value="">选择题目</option>';
    questions.forEach((q, i) => {
      const t = (q.title || "").slice(0, 36);
      const sel = q.id === selectedId ? " selected" : "";
      h += `<option value="${escapeHtml(q.id)}"${sel}>${i + 1}. ${escapeHtml(
        t
      )}</option>`;
    });
    return h;
  }

  function getQuestionById(id) {
    return questions.find((q) => q.id === id);
  }

  function renderJumpRules() {
    const container = $("jumpRulesContainer");
    const empty = $("jumpRulesEmpty");
    container.innerHTML = "";
    if (!jumpRules.length) {
      empty.classList.remove("hidden");
    } else {
      empty.classList.add("hidden");
    }
    jumpRules.forEach((rule) => {
      container.appendChild(createJumpRuleCard(rule));
    });
  }

  const COND_TYPES = [
    { v: "always", label: "无条件" },
    { v: "option_match", label: "选项等于" },
    { v: "option_contains", label: "选项包含（多选，逗号分隔值）" },
    { v: "value_equal", label: "数值等于" },
    { v: "value_greater", label: "数值大于" },
    { v: "value_less", label: "数值小于" },
    { v: "value_between", label: "数值区间" },
  ];

  function createJumpRuleCard(rule) {
    const wrap = document.createElement("div");
    wrap.className = "jump-rule-card";
    wrap.dataset.ruleId = rule.id || "";
    const c = rule.condition || {};
    const ctype = c.type || "option_match";
    const p = c.params || {};

    const condOptions = COND_TYPES.map(
      (t) =>
        `<option value="${t.v}"${t.v === ctype ? " selected" : ""}>${t.label}</option>`
    ).join("");

    wrap.innerHTML = `
      <div class="rule-grid">
        <div>
          <label>源题目</label>
          <select class="jr-source">${questionOptionsHtml(
            rule.source_question_id
          )}</select>
        </div>
        <div>
          <label>条件</label>
          <select class="jr-ctype">${condOptions}</select>
        </div>
        <div class="jr-val-wrap">
          <label>条件值</label>
          <div class="jr-val-single">
            <input type="text" class="jr-val1" placeholder="如选项值 A" value="${escapeHtml(
              String(p.option_value ?? p.value ?? "")
            )}" />
          </div>
          <div class="jr-val-between hidden">
            <input type="number" class="jr-min" placeholder="最小" value="${p.min != null ? escapeHtml(String(p.min)) : ""}" />
            <input type="number" class="jr-max" placeholder="最大" value="${p.max != null ? escapeHtml(String(p.max)) : ""}" />
          </div>
          <div class="jr-val-contains hidden">
            <input type="text" class="jr-vals" placeholder="多个值用英文逗号分隔" value="${escapeHtml(
              Array.isArray(p.option_values)
                ? p.option_values.join(",")
                : ""
            )}" />
          </div>
        </div>
        <div>
          <label>跳转到</label>
          <select class="jr-target">${questionOptionsHtml(
            rule.target_question_id
          )}</select>
        </div>
        <div>
          <label>优先级（越大越先）</label>
          <input type="number" class="jr-pri" value="${Number(
            rule.priority ?? 0
          )}" />
        </div>
      </div>
      <div class="rule-actions">
        <button type="button" class="btn-toolbar primary jr-save">保存规则</button>
        <button type="button" class="btn-toolbar danger-outline jr-del">删除</button>
      </div>`;

    toggleJumpValUI(wrap, ctype);
    wrap.querySelector(".jr-ctype").addEventListener("change", () => {
      toggleJumpValUI(wrap, wrap.querySelector(".jr-ctype").value);
    });

    wrap.querySelector(".jr-save").addEventListener("click", () =>
      saveJumpRule(wrap, rule.id)
    );
    wrap.querySelector(".jr-del").addEventListener("click", () =>
      deleteJumpRule(wrap, rule.id)
    );
    return wrap;
  }

  function toggleJumpValUI(wrap, ctype) {
    const valWrap = wrap.querySelector(".jr-val-wrap");
    const s = wrap.querySelector(".jr-val-single");
    const b = wrap.querySelector(".jr-val-between");
    const oc = wrap.querySelector(".jr-val-contains");
    if (ctype === "always") {
      valWrap.classList.add("hidden");
      return;
    }
    valWrap.classList.remove("hidden");
    s.classList.add("hidden");
    b.classList.add("hidden");
    oc.classList.add("hidden");
    if (ctype === "value_between") {
      b.classList.remove("hidden");
    } else if (ctype === "option_contains") {
      oc.classList.remove("hidden");
    } else {
      s.classList.remove("hidden");
    }
  }

  function buildConditionFromCard(wrap) {
    const ctype = wrap.querySelector(".jr-ctype").value;
    if (ctype === "always") {
      return { type: "always", params: {} };
    }
    const params = {};
    if (ctype === "option_match") {
      params.option_value = wrap.querySelector(".jr-val1").value.trim();
    } else if (ctype === "option_contains") {
      const raw = wrap.querySelector(".jr-vals").value.trim();
      params.option_values = raw
        ? raw.split(",").map((x) => x.trim()).filter(Boolean)
        : [];
    } else if (ctype === "value_between") {
      params.min = Number(wrap.querySelector(".jr-min").value);
      params.max = Number(wrap.querySelector(".jr-max").value);
    } else {
      params.value = Number(wrap.querySelector(".jr-val1").value);
    }
    return { type: ctype, params };
  }

  async function saveJumpRule(wrap, ruleId) {
    const source = wrap.querySelector(".jr-source").value;
    const target = wrap.querySelector(".jr-target").value;
    const priority = Number(wrap.querySelector(".jr-pri").value || 0);
    const condition = buildConditionFromCard(wrap);
    if (!source || !target) {
      toast("请选择源题目与目标题目", "error");
      return;
    }
    try {
      if (ruleId) {
        await apiJson(
          "/surveys/" +
            encodeURIComponent(surveyId) +
            "/jump-rules/" +
            encodeURIComponent(ruleId),
          {
            method: "PUT",
            body: JSON.stringify({
              source_question_id: source,
              target_question_id: target,
              condition,
              priority,
            }),
          }
        );
        toast("规则已更新", "success");
      } else {
        await apiJson(
          "/surveys/" + encodeURIComponent(surveyId) + "/jump-rules",
          {
            method: "POST",
            body: JSON.stringify({
              source_question_id: source,
              target_question_id: target,
              condition,
              priority,
            }),
          }
        );
        toast("规则已创建", "success");
      }
      await loadJumpRulesData();
      renderJumpRules();
    } catch (err) {
      toast(err.message, "error");
    }
  }

  async function deleteJumpRule(wrap, ruleId) {
    if (!ruleId) {
      wrap.remove();
      return;
    }
    if (!confirm("确定删除该规则？")) return;
    try {
      await apiJson(
        "/surveys/" +
          encodeURIComponent(surveyId) +
          "/jump-rules/" +
          encodeURIComponent(ruleId),
        { method: "DELETE" }
      );
      toast("已删除规则", "success");
      await loadJumpRulesData();
      renderJumpRules();
    } catch (err) {
      toast(err.message, "error");
    }
  }

  function addNewJumpRuleRow() {
    const container = $("jumpRulesContainer");
    $("jumpRulesEmpty").classList.add("hidden");
    const card = createJumpRuleCard({
      id: "",
      source_question_id: "",
      target_question_id: "",
      condition: { type: "option_match", params: { option_value: "" } },
      priority: 10,
    });
    container.appendChild(card);
  }

  async function saveSurvey() {
    const deadlineIso = datetimeLocalToIso($("deadline").value);
    const body = {
      title: $("title").value.trim(),
      description: $("description").value,
      settings: {
        allow_multiple: $("allowMultiple").checked,
        allow_anonymous: $("allowAnonymous").checked,
        deadline: deadlineIso,
        thank_you_message:
          $("thankYouMessage").value.trim() || "感谢您的参与！",
      },
    };
    if (!body.title) {
      toast("请填写问卷标题", "error");
      return;
    }
    try {
      const res = await apiJson(
        "/surveys/" + encodeURIComponent(surveyId),
        {
          method: "PUT",
          body: JSON.stringify(body),
        }
      );
      survey = res.data;
      renderToolbar();
      toast("保存成功", "success");
    } catch (err) {
      toast(err.message, "error");
    }
  }

  async function publishSurvey() {
    try {
      const res = await apiJson(
        "/surveys/" + encodeURIComponent(surveyId) + "/publish",
        { method: "POST" }
      );
      survey = res.data;
      renderToolbar();
      toast("发布成功", "success");
    } catch (err) {
      toast(err.message, "error");
    }
  }

  async function closeSurveyFromToolbar() {
    try {
      const res = await apiJson(
        "/surveys/" + encodeURIComponent(surveyId) + "/close",
        { method: "POST" }
      );
      survey = res.data;
      renderToolbar();
      toast("问卷已关闭", "success");
    } catch (err) {
      toast(err.message, "error");
    }
  }

  async function deleteSurveyFromToolbar() {
    if (
      !confirm(
        "确定删除该问卷？题目、跳转规则与所有答卷将永久删除，不可恢复。"
      )
    )
      return;
    try {
      await apiJson("/surveys/" + encodeURIComponent(surveyId), {
        method: "DELETE",
      });
      toast("已删除", "success");
      location.href = "/index.html";
    } catch (err) {
      toast(err.message, "error");
    }
  }

  /* —— 题目弹窗 —— */
  function openQuestionModal(q) {
    editingQuestionId = q ? q.id : null;
    $("questionModalTitle").textContent = q ? "编辑题目" : "添加题目";
    $("qmTitle").value = q ? q.title || "" : "";
    $("qmType").value = q ? q.type : "single_choice";
    $("qmRequired").checked = q ? !!q.required : false;
    if (q && q.options && q.options.length) {
      $("qmOptionsList").innerHTML = "";
      q.options.forEach((o) => addOptionRow(o.value, o.label));
    } else {
      $("qmOptionsList").innerHTML = "";
      addOptionRow("A", "");
      addOptionRow("B", "");
    }
    const v = (q && q.validation) || {};
    $("qmMinSelect").value = v.min_select ?? "";
    $("qmMaxSelect").value = v.max_select ?? "";
    $("qmExactSelect").value = v.exact_select ?? "";
    $("qmMinLength").value = v.min_length ?? "";
    $("qmMaxLength").value = v.max_length ?? "";
    $("qmMinValue").value = v.min_value ?? "";
    $("qmMaxValue").value = v.max_value ?? "";
    $("qmIntegerOnly").checked = !!v.integer_only;
    onQmTypeChange();
    openModal("questionModal");
  }

  function addOptionRow(val, label) {
    const row = document.createElement("div");
    row.className = "option-row";
    row.innerHTML = `
      <input type="text" class="opt-val" placeholder="值" value="${escapeHtml(
        val || ""
      )}" />
      <input type="text" class="opt-label" placeholder="显示文字" value="${escapeHtml(
        label || ""
      )}" />
      <button type="button" class="icon-btn danger opt-rm">✕</button>`;
    row.querySelector(".opt-rm").addEventListener("click", () => row.remove());
    $("qmOptionsList").appendChild(row);
  }

  function onQmTypeChange() {
    const t = $("qmType").value;
    $("qmOptionsBlock").classList.toggle(
      "hidden",
      t !== "single_choice" && t !== "multiple_choice"
    );
    $("qmValMulti").classList.toggle("hidden", t !== "multiple_choice");
    $("qmValText").classList.toggle("hidden", t !== "text");
    $("qmValNumber").classList.toggle("hidden", t !== "number");
  }

  function collectOptionsFromModal() {
    const rows = [...$("qmOptionsList").querySelectorAll(".option-row")];
    const out = [];
    let i = 0;
    for (const row of rows) {
      const value = row.querySelector(".opt-val").value.trim();
      const label = row.querySelector(".opt-label").value.trim() || value;
      if (!value) continue;
      out.push({ value, label, order: i++ });
    }
    return out;
  }

  function collectValidationFromModal() {
    const t = $("qmType").value;
    const o = {};
    if (t === "multiple_choice") {
      const mn = $("qmMinSelect").value;
      const mx = $("qmMaxSelect").value;
      const ex = $("qmExactSelect").value;
      if (mn !== "") o.min_select = Number(mn);
      if (mx !== "") o.max_select = Number(mx);
      if (ex !== "") o.exact_select = Number(ex);
    } else if (t === "text") {
      const mn = $("qmMinLength").value;
      const mx = $("qmMaxLength").value;
      if (mn !== "") o.min_length = Number(mn);
      if (mx !== "") o.max_length = Number(mx);
    } else if (t === "number") {
      const mn = $("qmMinValue").value;
      const mx = $("qmMaxValue").value;
      if (mn !== "") o.min_value = Number(mn);
      if (mx !== "") o.max_value = Number(mx);
      o.integer_only = $("qmIntegerOnly").checked;
    }
    return Object.keys(o).length ? o : {};
  }

  async function saveQuestionModal() {
    const title = $("qmTitle").value.trim();
    const type = $("qmType").value;
    if (!title) {
      toast("请填写题目标题", "error");
      return;
    }
    const opts = collectOptionsFromModal();
    if (
      (type === "single_choice" || type === "multiple_choice") &&
      opts.length === 0
    ) {
      toast("请至少添加一个选项", "error");
      return;
    }
    const payload = {
      title,
      type,
      required: $("qmRequired").checked,
      options: type === "single_choice" || type === "multiple_choice" ? opts : [],
      validation: collectValidationFromModal(),
    };
    try {
      if (editingQuestionId) {
        await apiJson(
          "/surveys/" +
            encodeURIComponent(surveyId) +
            "/questions/" +
            encodeURIComponent(editingQuestionId),
          { method: "PUT", body: JSON.stringify(payload) }
        );
        toast("题目已更新", "success");
      } else {
        await apiJson(
          "/surveys/" + encodeURIComponent(surveyId) + "/questions",
          { method: "POST", body: JSON.stringify(payload) }
        );
        toast("题目已添加", "success");
      }
      closeModal("questionModal");
      await loadQuestions();
    } catch (err) {
      toast(err.message, "error");
    }
  }

  function openModal(id) {
    const el = $(id);
    el.classList.add("open");
    el.setAttribute("aria-hidden", "false");
  }

  function closeModal(id) {
    const el = $(id);
    el.classList.remove("open");
    el.setAttribute("aria-hidden", "true");
  }

  document.querySelectorAll("[data-close-modal]").forEach((btn) => {
    btn.addEventListener("click", () => closeModal(btn.dataset.closeModal));
  });

  function renderPreview() {
    const sorted = [...questions].sort(
      (a, b) => (a.order || 0) - (b.order || 0)
    );
    const title = $("title").value.trim() || survey?.title || "未命名问卷";
    const desc = $("description").value || survey?.description || "";
    let html = `<div class="pv-title">${escapeHtml(title)}</div>`;
    html += `<div class="pv-desc">${escapeHtml(desc)}</div>`;
    if (
      survey &&
      (survey.status === "published" || survey.status === "closed") &&
      survey.short_code
    ) {
      const u = `${location.origin}/fill.html?code=${encodeURIComponent(
        survey.short_code
      )}`;
      html += `<p style="font-size:0.85rem;margin-bottom:1rem"><a href="${u}" target="_blank" rel="noopener">打开真实填写页</a></p>`;
    }
    sorted.forEach((q, i) => {
      html += `<div class="preview-item"><div class="pv-q">${i + 1}. ${escapeHtml(
        q.title
      )} <span style="color:#64748b;font-weight:400">(${TYPE_LABELS[q.type]})</span></div>`;
      if (q.options && q.options.length) {
        html += `<div class="pv-opts">${q.options
          .map((o) => escapeHtml(o.label || o.value))
          .join(" · ")}</div>`;
      }
      html += `</div>`;
    });
    if (!sorted.length) html += "<p class=\"empty-hint\">暂无题目</p>";
    $("previewBody").innerHTML = html;
    openModal("previewModal");
  }

  $("title").addEventListener("input", updateCharCount);
  $("btnSave").addEventListener("click", saveSurvey);
  $("btnPublish").addEventListener("click", publishSurvey);
  $("btnCloseSurvey").addEventListener("click", closeSurveyFromToolbar);
  $("btnDeleteSurvey").addEventListener("click", deleteSurveyFromToolbar);
  $("btnPreview").addEventListener("click", renderPreview);
  $("btnStats").addEventListener("click", () => {
    location.href =
      "/statistics.html?id=" + encodeURIComponent(surveyId);
  });
  $("copyLinkBtn").addEventListener("click", () => {
    if (!survey || !survey.short_code) return;
    const u = `${location.origin}/fill.html?code=${survey.short_code}`;
    navigator.clipboard.writeText(u).then(
      () => toast("已复制", "success"),
      () => toast("复制失败，请手动复制", "error")
    );
  });

  $("btnAddQuestion").addEventListener("click", () => openQuestionModal(null));
  $("qmType").addEventListener("change", onQmTypeChange);
  $("qmAddOption").addEventListener("click", () => addOptionRow("", ""));
  $("qmSave").addEventListener("click", saveQuestionModal);

  $("btnToggleSort").addEventListener("click", () => {
    sortMode = !sortMode;
    $("btnToggleSort").textContent = sortMode ? "退出排序" : "排序模式";
    $("btnToggleSort").classList.toggle("primary", sortMode);
    renderQuestionCards();
    toast(sortMode ? "拖动题目卡片即可排序，松手后自动保存" : "已退出排序模式", "success");
  });

  $("btnAddJumpRule").addEventListener("click", addNewJumpRuleRow);

  (async function init() {
    try {
      await loadSurvey();
      await loadQuestions();
    } catch (e) {
      toast(e.message || String(e), "error");
    }
  })();
})();

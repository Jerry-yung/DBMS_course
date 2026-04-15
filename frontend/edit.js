(function () {
  requireLogin();
  const params = new URLSearchParams(location.search);
  const surveyId = params.get("id");
  const previewParam = params.get("preview") === "1";
  let previewOnly = false;
  if (!surveyId) {
    alert("缺少问卷 id");
    location.href = "/index.html";
    return;
  }

  let survey = null;
  let questions = [];
  let jumpRules = [];
  let editingQuestionId = null;
  let draggedCardId = null;
  let surveyLibSaveQuestionId = null;
  let libraryPickerBankId = null;
  let currentUserId = null;

  const $ = (id) => document.getElementById(id);

  async function fetchMe() {
    try {
      const r = await apiJson("/auth/me");
      currentUserId = r.data && r.data.user_id;
    } catch {
      currentUserId = null;
    }
  }

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

  /** 题库展示名：避免空白标题导致界面上像「只有勾选框」 */
  function displayBankTitle(b) {
    if (!b) return "（未命名题库）";
    const t = b.title != null ? String(b.title).trim() : "";
    if (t) return t;
    const id = (b.id || "").trim();
    if (id.length >= 8) return `未命名题库（${id.slice(0, 8)}…）`;
    return "（未命名题库）";
  }

  function isSharedInboxBank(b) {
    return !!(b && (b.is_shared_inbox || b.preset_kind === "shared_inbox"));
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

  /** 与问卷预览一致的纯内容块（无时间、id） */
  function libraryQuestionPreviewBlockHtml(q, idx) {
    const opts =
      q.options && q.options.length
        ? `<div class="pv-opts">${q.options
            .map((o) => escapeHtml(o.label || o.value))
            .join(" · ")}</div>`
        : "";
    const val = q.validation || {};
    let valLine = "";
    if (q.type === "multiple_choice") {
      const parts = [];
      if (val.exact_select != null) parts.push(`精确选 ${val.exact_select} 项`);
      if (val.min_select != null) parts.push(`最少选 ${val.min_select}`);
      if (val.max_select != null) parts.push(`最多选 ${val.max_select}`);
      if (parts.length)
        valLine = `<div class="pv-valhint">${escapeHtml(parts.join("；"))}</div>`;
    } else if (q.type === "text") {
      if (val.min_length != null || val.max_length != null)
        valLine = `<div class="pv-valhint">${escapeHtml(
          `字数 ${val.min_length ?? "—"}–${val.max_length ?? "—"}`
        )}</div>`;
    } else if (q.type === "number") {
      const p = [];
      if (val.min_value != null || val.max_value != null)
        p.push(`范围 ${val.min_value ?? "—"}–${val.max_value ?? "—"}`);
      if (val.integer_only) p.push("须为整数");
      if (p.length)
        valLine = `<div class="pv-valhint">${escapeHtml(p.join("；"))}</div>`;
    }
    const req = q.required
      ? ' <span class="pv-req">必答</span>'
      : "";
    return `<div class="preview-item ver-preview-item">
      <div class="pv-q">${idx}. ${escapeHtml(q.title || "（无标题）")} <span style="color:#64748b;font-weight:400">(${TYPE_LABELS[q.type] || q.type})</span>${req}</div>
      ${opts}
      ${valLine}
    </div>`;
  }

  async function openQuestionVersionsModal(questionId, lineageId) {
    openModal("qVersionsModal");
    $("qVersionsBody").innerHTML = "<p class=\"empty-hint\">加载中…</p>";
    if (!currentUserId) await fetchMe();
    const draft = isSurveyDraft();
    try {
      const r = await apiJson(
        "/question-library/lineages/" +
          encodeURIComponent(lineageId) +
          "/versions"
      );
      const rows = Array.isArray(r.data) ? r.data : [];
      const box = $("qVersionsBody");
      box.innerHTML = "";
      if (!rows.length) {
        box.innerHTML = "<p class=\"empty-hint\">无版本记录</p>";
        return;
      }
      rows.forEach((v, i) => {
        const wrap = document.createElement("div");
        wrap.className = "ver-version-row";
        const prev = document.createElement("div");
        prev.innerHTML = libraryQuestionPreviewBlockHtml(v, i + 1);
        while (prev.firstChild) wrap.appendChild(prev.firstChild);
        const actions = document.createElement("div");
        actions.className = "ver-version-actions";
        if (draft) {
          const b1 = document.createElement("button");
          b1.type = "button";
          b1.className = "icon-btn primary";
          b1.textContent = "用此版本覆盖当前题目";
          b1.addEventListener("click", async () => {
            if (!confirm("确定用该版本覆盖当前问卷中的题目？")) return;
            try {
              await apiJson(
                "/surveys/" +
                  encodeURIComponent(surveyId) +
                  "/questions/" +
                  encodeURIComponent(questionId) +
                  "/apply-library-version",
                {
                  method: "POST",
                  body: JSON.stringify({
                    library_question_id: v.id,
                  }),
                }
              );
              toast("已覆盖", "success");
              closeModal("qVersionsModal");
              await loadQuestions();
            } catch (err) {
              toast(err.message, "error");
            }
          });
          actions.appendChild(b1);
        }
        const mine = String(v.owner_id || "") === String(currentUserId || "");
        if (mine) {
          const b2 = document.createElement("button");
          b2.type = "button";
          b2.className = "icon-btn danger";
          b2.textContent = "删除此版本";
          b2.addEventListener("click", async () => {
            if (
              !confirm(
                "确定删除题库中的该版本？若有后续版本将接到上一版；本题库若钉选了该版展示将恢复为最新版。"
              )
            )
              return;
            try {
              await apiJson(
                "/question-library/items/" +
                  encodeURIComponent(v.id) +
                  "/version",
                { method: "DELETE" }
              );
              toast("已删除", "success");
              await openQuestionVersionsModal(questionId, lineageId);
              await loadQuestions();
            } catch (err) {
              toast(err.message, "error");
            }
          });
          actions.appendChild(b2);
        }
        wrap.appendChild(actions);
        box.appendChild(wrap);
      });
    } catch (err) {
      $("qVersionsBody").innerHTML = `<p class="err">${escapeHtml(
        err.message
      )}</p>`;
    }
  }

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

  function isSurveyDraft() {
    return survey && survey.status === "draft";
  }

  function applyReadOnlyPreviewMode() {
    const bar = $("readonlySurveyBanner");
    if (bar) bar.classList.remove("hidden");
    ["title", "description", "deadline", "thankYouMessage"].forEach((id) => {
      const el = $(id);
      if (el) el.readOnly = true;
    });
    ["allowMultiple", "allowAnonymous"].forEach((id) => {
      const el = $(id);
      if (el) el.disabled = true;
    });
    ["btnSave", "btnDeleteSurvey", "btnCloseSurvey"].forEach((id) => {
      const el = $(id);
      if (el) el.classList.add("hidden");
    });
    const bj = $("btnAddJumpRule");
    if (bj) bj.classList.add("hidden");
    document
      .querySelectorAll(".jump-rule-card select, .jump-rule-card input")
      .forEach((el) => {
        el.disabled = true;
      });
    document
      .querySelectorAll(".jump-rule-card .jr-save, .jump-rule-card .jr-del")
      .forEach((el) => {
        el.classList.add("hidden");
      });
  }

  function updateDraftUi() {
    const draft = isSurveyDraft();
    ["btnAddQuestion", "btnFromLibrary"].forEach((id) => {
      const el = $(id);
      if (el) el.classList.toggle("hidden", !draft);
    });
    const dragHint = $("questionsDragHint");
    if (dragHint) dragHint.classList.toggle("hidden", !draft);
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
    updateDraftUi();
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
      card.className = "question-card";
      card.dataset.questionId = q.id;
      card.draggable = false;
      const optsSummary =
        q.options && q.options.length
          ? q.options.map((o) => o.label || o.value).join(" · ")
          : "—";
      const draft = isSurveyDraft();
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
      const dragTitle = draft ? "拖动排序（松手后自动保存）" : "仅草稿可调整顺序";
      const dragCls = draft ? "drag-handle" : "drag-handle drag-handle--disabled";
      card.innerHTML = `
        <div class="${dragCls}" title="${dragTitle}">⋮⋮</div>
        <div class="q-num">${idx + 1}</div>
        <span class="q-badge">${TYPE_LABELS[q.type] || q.type}</span>
        <div class="q-body">
          <div class="q-title">${escapeHtml(q.title || "")}</div>
          <div class="q-meta">${q.required ? "必答 · " : ""}选项：${escapeHtml(
        optsSummary
      )}${valSummary ? " · " + escapeHtml(valSummary) : ""}</div>
        </div>
        <div class="q-actions">
          ${
            draft
              ? `<button type="button" class="icon-btn" data-act="edit" data-id="${escapeHtml(
                  q.id
                )}">编辑</button>
          <button type="button" class="icon-btn" data-act="copy" data-id="${escapeHtml(
                  q.id
                )}">复制</button>
          <button type="button" class="icon-btn danger" data-act="del" data-id="${escapeHtml(
                  q.id
                )}">删除</button>
          <button type="button" class="icon-btn" data-act="libsave" data-id="${escapeHtml(
                  q.id
                )}">保存到题库</button>`
              : ""
          }
          ${
            q.lineage_id
              ? `<button type="button" class="icon-btn" data-act="versions" data-id="${escapeHtml(
                  q.id
                )}" data-lid="${escapeHtml(q.lineage_id)}">版本</button>
          <button type="button" class="icon-btn" data-act="usage" data-lid="${escapeHtml(
                  q.lineage_id
                )}">使用方</button>`
              : ""
          }
        </div>`;
      container.appendChild(card);
    });

    container.querySelectorAll("[data-act]").forEach((btn) => {
      btn.addEventListener("click", onQuestionAction);
    });

    if (isSurveyDraft()) {
      container.querySelectorAll(".question-card").forEach(bindDrag);
    }
  }

  function bindDrag(card) {
    const handle = card.querySelector(".drag-handle");
    if (!handle || handle.classList.contains("drag-handle--disabled")) return;
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

  async function openLibraryPicker() {
    if (!isSurveyDraft()) {
      toast("仅草稿可从题库添加题目", "error");
      return;
    }
    const banksBox = $("libraryPickerBanks");
    const listBox = $("libraryPickerList");
    banksBox.innerHTML = "<p>加载中…</p>";
    listBox.innerHTML = "";
    const headEl = $("libraryPickerItemsHead");
    if (headEl) headEl.textContent = "本题库中的题目";
    openModal("libraryPickerModal");
    try {
      const banksRes = await apiJson("/question-library/banks");
      const banks = Array.isArray(banksRes.data) ? banksRes.data : [];
      if (!banks.length) {
        banksBox.innerHTML =
          "<p class=\"empty-hint\">暂无题库。请先到「题库管理」创建题库。</p>";
        listBox.innerHTML = "";
        return;
      }
      banksBox.innerHTML = "";
      const renderItems = async (bankId) => {
        libraryPickerBankId = bankId;
        listBox.innerHTML = "<p>加载中…</p>";
        const res = await apiJson(
          "/question-library/banks/" + encodeURIComponent(bankId) + "/items"
        );
        const rows = Array.isArray(res.data) ? res.data : [];
        if (!rows.length) {
          listBox.innerHTML =
            "<p class=\"empty-hint\">该题库暂无题目。请先在题库详情中创建，或将问卷题保存到该题库。</p>";
          return;
        }
        const enriched = await Promise.all(
          rows.map(async (entry) => {
            const lid = String(entry.lineage_id || "").trim();
            let versions = [];
            if (lid) {
              try {
                const vr = await apiJson(
                  "/question-library/lineages/" +
                    encodeURIComponent(lid) +
                    "/versions"
                );
                versions = Array.isArray(vr.data) ? vr.data.slice() : [];
                versions.reverse();
              } catch (_) {
                versions = [];
              }
            }
            const item = entry.library_question || {};
            if (!versions.length && item.id) {
              versions = [item];
            }
            return { entry, item, versions };
          })
        );
        listBox.innerHTML = "";
        enriched.forEach(({ item, versions }) => {
          if (!versions.length) return;
          const latest = versions[0];

          async function addFromLibrary(lqid) {
            const id = String(lqid || "").trim();
            if (!id) {
              toast("版本无效", "error");
              return;
            }
            try {
              await apiJson(
                "/surveys/" +
                  encodeURIComponent(surveyId) +
                  "/questions/from-library",
                {
                  method: "POST",
                  body: JSON.stringify({
                    library_question_id: id,
                  }),
                }
              );
              toast("已从题库添加", "success");
              closeModal("libraryPickerModal");
              await loadQuestions();
            } catch (err) {
              toast(err.message, "error");
            }
          }

          const row = document.createElement("div");
          row.className = "lp-row lp-row-item lp-row-item-stack";

          const previewWrap = document.createElement("div");
          previewWrap.className = "lp-item-preview";
          previewWrap.innerHTML = libraryQuestionPreviewBlockHtml(latest, 1);

          const actions = document.createElement("div");
          actions.className = "lp-picker-actions";

          const versPanel = document.createElement("div");
          versPanel.className = "lp-version-panel hidden";

          if (versions.length > 1) {
            const btnPickVer = document.createElement("button");
            btnPickVer.type = "button";
            btnPickVer.className = "btn-toolbar secondary";
            btnPickVer.textContent = "选择版本";
            btnPickVer.addEventListener("click", () => {
              versPanel.classList.toggle("hidden");
              btnPickVer.textContent = versPanel.classList.contains("hidden")
                ? "选择版本"
                : "收起版本";
            });
            actions.appendChild(btnPickVer);

            versions.forEach((v, vi) => {
              const opt = document.createElement("div");
              opt.className = "lp-version-option";
              const inner = document.createElement("div");
              inner.innerHTML = libraryQuestionPreviewBlockHtml(v, vi + 1);
              while (inner.firstChild) opt.appendChild(inner.firstChild);
              const addRow = document.createElement("div");
              addRow.className = "lp-version-add-row";
              const b = document.createElement("button");
              b.type = "button";
              b.className = "btn-toolbar lp-btn-add-version";
              b.textContent = "添加本版本";
              b.addEventListener("click", () => {
                void addFromLibrary(v.id);
              });
              addRow.appendChild(b);
              opt.appendChild(addRow);
              versPanel.appendChild(opt);
            });
          } else {
            const btnAddTopic = document.createElement("button");
            btnAddTopic.type = "button";
            btnAddTopic.className = "btn-toolbar lp-btn-add-version";
            btnAddTopic.textContent = "添加本题";
            btnAddTopic.addEventListener("click", () => {
              void addFromLibrary(latest.id);
            });
            actions.appendChild(btnAddTopic);
          }

          row.appendChild(previewWrap);
          row.appendChild(actions);
          if (versions.length > 1) {
            row.appendChild(versPanel);
          }
          listBox.appendChild(row);
        });
      };
      const itemsHead = $("libraryPickerItemsHead");
      banks.forEach((b, idx) => {
        const row = document.createElement("div");
        row.className = "lp-row lp-row-bank";
        const left = document.createElement("div");
        left.className = "lp-row-main";
        const btitle = escapeHtml(displayBankTitle(b));
        left.innerHTML = `<span class="lp-badge lp-badge-bank" aria-hidden="true">题库</span>
          <div class="lp-bank-block">
            <div class="lp-bank-title">${btitle}</div>
            <div class="lp-meta">ID ${escapeHtml((b.id || "").slice(0, 8))}…</div>
          </div>`;
        const bt = document.createElement("button");
        bt.type = "button";
        bt.className = "btn-toolbar secondary";
        bt.textContent = "查看题目";
        bt.addEventListener("click", async () => {
          if (itemsHead) {
            itemsHead.textContent = `「${displayBankTitle(b)}」中的题目`;
          }
          renderItems(b.id);
        });
        row.appendChild(left);
        row.appendChild(bt);
        banksBox.appendChild(row);
        if (idx === 0) {
          if (itemsHead) {
            itemsHead.textContent = `「${displayBankTitle(b)}」中的题目`;
          }
          renderItems(b.id);
        }
      });
    } catch (err) {
      banksBox.innerHTML = `<p class="err">${escapeHtml(err.message)}</p>`;
      listBox.innerHTML = "";
    }
  }

  function surveyStatusLabelZh(st) {
    const m = {
      draft: "未发布",
      published: "已发布",
      closed: "已关闭",
    };
    return m[st] || (st ? String(st) : "—");
  }

  async function openUsageModal(lineageId) {
    if (!lineageId) return;
    const body = $("usageModalBody");
    body.innerHTML = "<p>加载中…</p>";
    openModal("usageModal");
    try {
      const res = await apiJson(
        "/question-library/lineages/" +
          encodeURIComponent(lineageId) +
          "/usage"
      );
      const rows = Array.isArray(res.data) ? res.data : [];
      if (!rows.length) {
        body.innerHTML = "<p class=\"empty-hint\">当前账户下暂无问卷使用该家族题目。</p>";
        return;
      }
      let html =
        "<table style=\"width:100%;font-size:0.85rem;border-collapse:collapse\"><thead><tr><th align=\"left\">问卷</th><th>状态</th><th>题目ID</th></tr></thead><tbody>";
      rows.forEach((r) => {
        html += `<tr><td>${escapeHtml(r.survey_title || "")}</td><td>${escapeHtml(
          surveyStatusLabelZh(r.survey_status)
        )}</td><td><code>${escapeHtml(r.question_id || "")}</code></td></tr>`;
      });
      html += "</tbody></table>";
      body.innerHTML = html;
    } catch (err) {
      body.innerHTML = `<p class="err">${escapeHtml(err.message)}</p>`;
    }
  }

  function setSurveyLibNewBankPanel(open) {
    const panel = $("surveyLibNewBankPanel");
    if (!panel) return;
    panel.hidden = !open;
    if (!open) {
      $("surveyLibNewBankTitle").value = "";
    } else {
      $("surveyLibNewBankTitle").focus();
    }
  }

  async function openSurveyLibSaveModal(questionId) {
    surveyLibSaveQuestionId = questionId;
    const box = $("surveyLibSaveBankList");
    box.innerHTML = "<p>加载中…</p>";
    setSurveyLibNewBankPanel(false);
    openModal("surveyLibSaveBankModal");
    try {
      const res = await apiJson("/question-library/banks");
      let banks = Array.isArray(res.data) ? res.data : [];
      banks = banks.filter((b) => !isSharedInboxBank(b));
      if (!banks.length) {
        box.innerHTML =
          "<p class=\"empty-hint\">您还没有可用题库（共享库不能手动写入）。可点击「新建题库」创建后再勾选保存。</p>";
        return;
      }
      box.innerHTML = "";
      banks.forEach((b) => {
        const lab = document.createElement("label");
        lab.className = "sl-bank-row";
        const bid = escapeHtml(b.id || "");
        const name = escapeHtml(displayBankTitle(b));
        lab.innerHTML = `<input type="checkbox" class="sl-bank-cb" value="${bid}" /><span class="sl-bank-name">${name}</span>`;
        box.appendChild(lab);
      });
    } catch (err) {
      box.innerHTML = `<p class="err">${escapeHtml(err.message)}</p>`;
    }
  }

  async function onQuestionAction(e) {
    const btn = e.currentTarget;
    const id = btn.dataset.id;
    const act = btn.dataset.act;
    const lid = btn.dataset.lid;
    if (act === "versions") {
      if (!lid || !id) return;
      await openQuestionVersionsModal(id, lid);
      return;
    }
    if (act === "usage") {
      await openUsageModal(lid);
      return;
    }
    if (act === "libsave") {
      if (!isSurveyDraft()) {
        toast("仅草稿可保存到题库", "error");
        return;
      }
      openSurveyLibSaveModal(id);
      return;
    }
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
    if (previewOnly) {
      toast("当前为预览模式，不可保存", "error");
      return;
    }
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

  async function closeSurveyFromToolbar() {
    if (previewOnly) return;
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
    if (previewOnly) return;
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

  $("btnSurveyLibToggleNewBank").addEventListener("click", () => {
    const panel = $("surveyLibNewBankPanel");
    setSurveyLibNewBankPanel(panel.hidden);
  });

  $("btnSurveyLibCancelNewBank").addEventListener("click", () => {
    setSurveyLibNewBankPanel(false);
  });

  $("btnSurveyLibCreateBank").addEventListener("click", async () => {
    const title = $("surveyLibNewBankTitle").value.trim();
    if (!title) {
      toast("题库名称不能为空", "error");
      return;
    }
    try {
      await apiJson("/question-library/banks", {
        method: "POST",
        body: JSON.stringify({ title, description: "" }),
      });
      toast("题库已创建，请勾选后再保存", "success");
      setSurveyLibNewBankPanel(false);
      await openSurveyLibSaveModal(surveyLibSaveQuestionId);
    } catch (err) {
      toast(err.message, "error");
    }
  });

  $("btnSurveyLibSaveConfirm").addEventListener("click", async () => {
    const qid = surveyLibSaveQuestionId;
    if (!qid) {
      toast("内部错误", "error");
      return;
    }
    const bank_ids = [...document.querySelectorAll(".sl-bank-cb:checked")]
      .map((el) => el.value.trim())
      .filter(Boolean);
    if (!bank_ids.length) {
      toast("请至少选择一个题库", "error");
      return;
    }
    try {
      await apiJson("/question-library/items/from-survey-question", {
        method: "POST",
        body: JSON.stringify({
          survey_id: surveyId,
          question_id: qid,
          bank_ids,
        }),
      });
      toast("已保存到题库", "success");
      closeModal("surveyLibSaveBankModal");
      surveyLibSaveQuestionId = null;
    } catch (err) {
      toast(err.message, "error");
    }
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
  $("btnCloseSurvey").addEventListener("click", closeSurveyFromToolbar);
  $("btnDeleteSurvey").addEventListener("click", deleteSurveyFromToolbar);
  $("btnPreview").addEventListener("click", renderPreview);
  $("copyLinkBtn").addEventListener("click", () => {
    if (!survey || !survey.short_code) return;
    const u = `${location.origin}/fill.html?code=${survey.short_code}`;
    navigator.clipboard.writeText(u).then(
      () => toast("已复制", "success"),
      () => toast("复制失败，请手动复制", "error")
    );
  });

  $("btnAddQuestion").addEventListener("click", () => openQuestionModal(null));
  $("btnFromLibrary").addEventListener("click", openLibraryPicker);
  $("qmType").addEventListener("change", onQmTypeChange);
  $("qmAddOption").addEventListener("click", () => addOptionRow("", ""));
  $("qmSave").addEventListener("click", saveQuestionModal);

  $("btnAddJumpRule").addEventListener("click", addNewJumpRuleRow);

  (async function init() {
    try {
      await fetchMe();
      await loadSurvey();
      previewOnly =
        previewParam &&
        survey &&
        (survey.status === "published" || survey.status === "closed");
      await loadQuestions();
      if (previewOnly) {
        applyReadOnlyPreviewMode();
      }
    } catch (e) {
      toast(e.message || String(e), "error");
    }
  })();
})();

(function () {
  requireLogin();
  const $ = (id) => document.getElementById(id);

  let currentUserId = null;
  let banksCache = [];
  let currentBank = null;
  let editingLibraryQuestionId = null;
  /** null | "inplace" | "newversion" — 仅编辑已有库题时有效 */
  let libraryEditMode = null;
  /** 最近一次「统计」弹窗加载的 cross-statistics 载荷，用于导出 */
  let libLineageStatsPayload = null;

  const TYPE_LABELS = {
    single_choice: "单选",
    multiple_choice: "多选",
    text: "填空",
    number: "数字",
  };

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

  function toast(msg, err) {
    const el = $("toastLib");
    el.textContent = msg;
    el.className = err ? "err show" : "show";
    clearTimeout(el._t);
    el._t = setTimeout(() => (el.className = ""), 3200);
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function surveyStatusLabelZh(st) {
    const m = {
      draft: "未发布",
      published: "已发布",
      closed: "已关闭",
    };
    return m[st] || (st ? String(st) : "—");
  }

  async function openUsageModalLineage(lineageId) {
    if (!lineageId) return;
    const body = $("libUsageModalBody");
    if (!body) return;
    body.innerHTML = "<p>加载中…</p>";
    openModal("libUsageModal");
    try {
      const res = await apiJson(
        "/question-library/lineages/" +
          encodeURIComponent(lineageId) +
          "/usage"
      );
      const rows = Array.isArray(res.data) ? res.data : [];
      if (!rows.length) {
        body.innerHTML =
          "<p class=\"empty-hint\">当前账户下暂无问卷使用该家族题目。</p>";
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
    } catch (e) {
      body.innerHTML = `<p class="err">${escapeHtml(e.message)}</p>`;
    }
  }

  function csvEscapeCell(v) {
    const s = v == null ? "" : String(v);
    if (/[",\n\r]/.test(s)) return '"' + s.replace(/"/g, '""') + '"';
    return s;
  }

  function csvLine(cells) {
    return cells.map(csvEscapeCell).join(",");
  }

  function csvAnswerOptionRaw(value) {
    if (value == null) return "";
    if (Array.isArray(value)) return value.map((x) => String(x)).join(";");
    if (typeof value === "object") return JSON.stringify(value);
    return String(value);
  }

  function buildLineageStatsCsv(data) {
    const lines = [];
    const R = (cells) => lines.push(csvLine(cells));

    if (data.error) {
      R(["说明", data.message || data.error]);
      if (Array.isArray(data.types) && data.types.length)
        R(["冲突题型", data.types.join(";")]);
      return "\ufeff" + lines.join("\n") + "\n";
    }

    const qt = data.question_type;
    const typeLabel = TYPE_LABELS[qt] || qt || "";

    R(["题目", "题型", "涉及问卷数"]);
    R([data.title || "", typeLabel, String(data.survey_count ?? "")]);

    const os = data.option_summary || [];
    if (
      (qt === "single_choice" || qt === "multiple_choice") &&
      os.length
    ) {
      lines.push("");
      R(["选项值", "选项内容", "次数", "比例（百分比）"]);
      os.forEach((o) => {
        R([
          String(o.value ?? ""),
          String(o.label ?? ""),
          String(o.count ?? ""),
          ((o.proportion || 0) * 100).toFixed(2) + "%",
        ]);
      });
    }

    const ns = data.numeric_summary;
    if (qt === "number" && ns && typeof ns === "object") {
      lines.push("");
      R(["指标", "值"]);
      [
        ["作答人数", ns.count],
        ["平均值", ns.avg],
        ["最小值", ns.min],
        ["最大值", ns.max],
        ["中位数", ns.median],
        ["标准差（样本）", ns.std],
      ].forEach(([k, v]) =>
        R([k, v == null ? "" : String(v)])
      );
    }

    if (qt === "text" && data.statistics && Array.isArray(data.statistics.values)) {
      lines.push("");
      R(["文本作答条数", String(data.statistics.values.length)]);
    }

    if (data.note) {
      lines.push("");
      R(["说明", data.note]);
    }

    const ans = data.respondent_answers || [];
    if (ans.length) {
      lines.push("");
      R(["问卷ID", "问卷标题", "答案选项", "答案选项内容"]);
      ans.forEach((r) => {
        R([
          r.survey_id,
          r.survey_title,
          csvAnswerOptionRaw(r.value),
          r.value_display || "",
        ]);
      });
    }

    return "\ufeff" + lines.join("\n") + "\n";
  }

  function downloadTextFile(text, filename, mime) {
    const blob = new Blob([text], {
      type: mime || "text/plain;charset=utf-8",
    });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  function renderLibStatsModalBody(d) {
    const box = $("libStatsModalBody");
    if (!box) return;
    if (d.error) {
      box.innerHTML = `<p class="err">${escapeHtml(
        d.message || d.error
      )}</p><p class="hint">冲突题型：${escapeHtml(
        (Array.isArray(d.types) ? d.types : []).join(", ")
      )}</p>`;
      return;
    }
    const qt = d.question_type;
    const typeLabel = TYPE_LABELS[qt] || qt || "—";
    let html = `<div class="lib-stats-summary"><strong>${escapeHtml(
      d.title || "（无标题）"
    )}</strong><br/>题型：${escapeHtml(
      String(typeLabel)
    )}；涉及问卷 ${d.survey_count ?? 0} 份；问卷内题目实例 ${d.question_instances ?? 0} 道。</div>`;
    if (d.note)
      html += `<p class="hint" style="margin-top:.35rem">${escapeHtml(
        d.note
      )}</p>`;

    const os = d.option_summary || [];
    if (os.length) {
      html +=
        "<p style='margin:.55rem 0 .25rem;font-weight:600'>选项分布</p><div class='lib-stats-table-wrap'><table><thead><tr><th>选项</th><th>次数</th><th>比例</th></tr></thead><tbody>";
      os.forEach((o) => {
        html += `<tr><td>${escapeHtml(o.label)}</td><td>${o.count}</td><td>${(
          (o.proportion || 0) * 100
        ).toFixed(2)}%</td></tr>`;
      });
      html += "</tbody></table></div>";
    }

    const ns = d.numeric_summary;
    if (ns && typeof ns === "object") {
      html +=
        "<p style='margin:.55rem 0 .25rem;font-weight:600'>数值汇总</p><div class='lib-stats-table-wrap'><table><tbody>";
      [
        ["作答人数", ns.count],
        ["平均值", ns.avg],
        ["最小值", ns.min],
        ["最大值", ns.max],
        ["中位数", ns.median],
        ["标准差（样本）", ns.std],
      ].forEach(([k, v]) => {
        html += `<tr><td>${escapeHtml(k)}</td><td>${
          v == null || v === "" ? "—" : escapeHtml(String(v))
        }</td></tr>`;
      });
      html += "</tbody></table></div>";
    }

    if (qt === "text" && d.statistics && Array.isArray(d.statistics.values)) {
      html += `<p class="hint" style="margin-top:.5rem">文本作答共 ${d.statistics.values.length} 条（详见下方逐条或导出）。</p>`;
    }

    const ans = d.respondent_answers || [];
    html += `<p style='margin:.65rem 0 .25rem;font-weight:600'>逐条作答（${ans.length} 条）</p>`;
    if (!ans.length) {
      html += '<p class="empty-hint">暂无已完成答卷命中该题。</p>';
    } else {
      html +=
        "<div class='lib-stats-table-wrap'><table><thead><tr><th>问卷</th><th>答案</th></tr></thead><tbody>";
      ans.forEach((r) => {
        html += `<tr><td>${escapeHtml(
          r.survey_title || r.survey_id
        )}</td><td>${escapeHtml(r.value_display || "")}</td></tr>`;
      });
      html += "</tbody></table></div>";
    }
    box.innerHTML = html;
  }

  async function openLibStatsModal(lineageId) {
    if (!lineageId) return;
    libLineageStatsPayload = null;
    const box = $("libStatsModalBody");
    if (!box) return;
    box.innerHTML = "<p>加载中…</p>";
    openModal("libStatsModal");
    try {
      const res = await apiJson(
        "/question-library/lineages/" +
          encodeURIComponent(lineageId) +
          "/cross-statistics"
      );
      libLineageStatsPayload = res.data;
      renderLibStatsModalBody(res.data);
    } catch (e) {
      box.innerHTML = `<p class="err">${escapeHtml(e.message)}</p>`;
    }
  }

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

  function updateBankDetailChrome() {
    const inbox = currentBank && isSharedInboxBank(currentBank);
    const row = $("bankCreateRow");
    if (row) row.classList.toggle("hidden", !!inbox);
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

  function showInfo(title, body) {
    $("libInfoModalTitle").textContent = title;
    $("libInfoModalBody").textContent = body;
    openModal("libInfoModal");
  }

  async function fetchMe() {
    try {
      const r = await apiJson("/auth/me");
      currentUserId = r.data && r.data.user_id;
    } catch {
      currentUserId = null;
    }
  }

  function addOptionRow(val, label) {
    const row = document.createElement("div");
    row.className = "option-row";
    row.innerHTML = `
      <input type="text" class="opt-val" placeholder="值" value="${escapeHtml(val || "")}" />
      <input type="text" class="opt-label" placeholder="显示文字" value="${escapeHtml(label || "")}" />
      <button type="button" class="icon-btn danger opt-rm">✕</button>`;
    row.querySelector(".opt-rm").addEventListener("click", () => row.remove());
    $("libQmOptionsList").appendChild(row);
  }

  function onTypeChange() {
    const t = $("libQmType").value;
    $("libQmOptionsBlock").classList.toggle(
      "hidden",
      t !== "single_choice" && t !== "multiple_choice"
    );
    $("libQmValMulti").classList.toggle("hidden", t !== "multiple_choice");
    $("libQmValText").classList.toggle("hidden", t !== "text");
    $("libQmValNumber").classList.toggle("hidden", t !== "number");
  }

  function collectOptions() {
    const rows = [...$("libQmOptionsList").querySelectorAll(".option-row")];
    const out = [];
    let i = 0;
    rows.forEach((row) => {
      const value = row.querySelector(".opt-val").value.trim();
      const label = row.querySelector(".opt-label").value.trim() || value;
      if (!value) return;
      out.push({ value, label, order: i++ });
    });
    return out;
  }

  function collectValidation() {
    const t = $("libQmType").value;
    const o = {};
    if (t === "multiple_choice") {
      if ($("libQmMinSelect").value !== "") o.min_select = Number($("libQmMinSelect").value);
      if ($("libQmMaxSelect").value !== "") o.max_select = Number($("libQmMaxSelect").value);
      if ($("libQmExactSelect").value !== "") o.exact_select = Number($("libQmExactSelect").value);
    } else if (t === "text") {
      if ($("libQmMinLength").value !== "") o.min_length = Number($("libQmMinLength").value);
      if ($("libQmMaxLength").value !== "") o.max_length = Number($("libQmMaxLength").value);
    } else if (t === "number") {
      if ($("libQmMinValue").value !== "") o.min_value = Number($("libQmMinValue").value);
      if ($("libQmMaxValue").value !== "") o.max_value = Number($("libQmMaxValue").value);
      o.integer_only = $("libQmIntegerOnly").checked;
    }
    return Object.keys(o).length ? o : {};
  }

  function resetQuestionModal() {
    editingLibraryQuestionId = null;
    libraryEditMode = null;
    const tEl = $("libQuestionModalTitle");
    if (tEl) tEl.textContent = "在题库中新建题目";
    $("libQmTitle").value = "";
    $("libQmType").value = "single_choice";
    $("libQmRequired").checked = false;
    $("libQmOptionsList").innerHTML = "";
    addOptionRow("A", "");
    addOptionRow("B", "");
    $("libQmMinSelect").value = "";
    $("libQmMaxSelect").value = "";
    $("libQmExactSelect").value = "";
    $("libQmMinLength").value = "";
    $("libQmMaxLength").value = "";
    $("libQmMinValue").value = "";
    $("libQmMaxValue").value = "";
    $("libQmIntegerOnly").checked = false;
    onTypeChange();
  }

  function fillLibQuestionModalFromItem(item) {
    $("libQmTitle").value = (item.title || "").trim();
    $("libQmType").value = item.type || "single_choice";
    $("libQmRequired").checked = !!item.required;
    $("libQmOptionsList").innerHTML = "";
    const opts = item.options || [];
    if (opts.length)
      opts.forEach((o) => addOptionRow(o.value || "", o.label || ""));
    else {
      addOptionRow("A", "");
      addOptionRow("B", "");
    }
    const v = item.validation || {};
    $("libQmMinSelect").value =
      v.min_select != null && v.min_select !== "" ? v.min_select : "";
    $("libQmMaxSelect").value =
      v.max_select != null && v.max_select !== "" ? v.max_select : "";
    $("libQmExactSelect").value =
      v.exact_select != null && v.exact_select !== "" ? v.exact_select : "";
    $("libQmMinLength").value =
      v.min_length != null && v.min_length !== "" ? v.min_length : "";
    $("libQmMaxLength").value =
      v.max_length != null && v.max_length !== "" ? v.max_length : "";
    $("libQmMinValue").value =
      v.min_value != null && v.min_value !== "" ? v.min_value : "";
    $("libQmMaxValue").value =
      v.max_value != null && v.max_value !== "" ? v.max_value : "";
    $("libQmIntegerOnly").checked = !!v.integer_only;
    onTypeChange();
  }

  function openEditLibraryGate(libraryQuestionId) {
    if (!libraryQuestionId) return;
    $("libEditGatePendingId").value = libraryQuestionId;
    openModal("libEditGateModal");
  }

  async function openLibQuestionEditor(libraryQuestionId, mode) {
    if (!libraryQuestionId || (mode !== "inplace" && mode !== "newversion")) return;
    try {
      const r = await apiJson(
        "/question-library/items/" + encodeURIComponent(libraryQuestionId)
      );
      const item = r.data;
      if (!item) {
        toast("无法加载题目", true);
        return;
      }
      editingLibraryQuestionId = libraryQuestionId;
      libraryEditMode = mode;
      $("libQuestionModalTitle").textContent =
        mode === "inplace"
          ? "编辑题目（修改本版本）"
          : "编辑题目（保存为新版本）";
      fillLibQuestionModalFromItem(item);
      openModal("libQuestionModal");
    } catch (e) {
      toast(e.message, true);
    }
  }

  function renderBankList() {
    const box = $("bankList");
    if (!banksCache.length) {
      box.innerHTML = `<div class="empty">暂无题库，点击上方「新建题库」开始。</div>`;
      return;
    }
    box.innerHTML = "";
    banksCache.forEach((b) => {
      const card = document.createElement("div");
      const inbox = isSharedInboxBank(b);
      card.className = "bank-card" + (inbox ? " bank-card-shared-inbox" : "");
      const desc = inbox
        ? `<div class="bank-desc-inbox">${escapeHtml(
            b.description || "来自其他人的共享，本库不可删除"
          )}</div>`
        : "";
      card.innerHTML = `
        <div class="lib-row" style="justify-content:space-between;align-items:flex-start">
          <div>
            <strong>${escapeHtml(displayBankTitle(b))}</strong>
            ${inbox ? '<span class="badge badge-shared" style="margin-left:.4rem">共享库</span>' : ""}
            ${desc}
          </div>
          <div class="lib-row" style="gap:.45rem;align-items:center;flex-shrink:0">
            ${
              inbox
                ? ""
                : `<button type="button" class="secondary" data-act="rename-bank" data-bid="${escapeHtml(b.id || "")}">重命名</button>
            <button type="button" class="bank-del-btn" data-act="del-bank" data-bid="${escapeHtml(b.id || "")}">删除题库</button>`
            }
            <button type="button" class="primary" data-act="enter-bank">进入详情</button>
          </div>
        </div>`;
      card.querySelector('[data-act="enter-bank"]').addEventListener("click", () => {
        currentBank = b;
        $("bankDetailTitle").textContent = `题库详情：${displayBankTitle(b)}`;
        updateBankDetailChrome();
        $("bankListView").classList.add("hidden");
        $("bankDetailView").classList.remove("hidden");
        loadBankItems();
      });
      const renameBtn = card.querySelector('[data-act="rename-bank"]');
      if (renameBtn) {
        renameBtn.addEventListener("click", (e) => {
          e.stopPropagation();
          const bid = (renameBtn.dataset.bid || "").trim();
          if (!bid) return;
          const bb = banksCache.find((x) => x.id === bid);
          if (!bb || isSharedInboxBank(bb)) return;
          $("renameBankId").value = bid;
          $("renameBankTitle").value =
            bb.title != null ? String(bb.title).trim() : "";
          openModal("renameBankModal");
          $("renameBankTitle").focus();
        });
      }
      const delBtn = card.querySelector('[data-act="del-bank"]');
      if (delBtn) {
        delBtn.addEventListener("click", async (e) => {
          e.stopPropagation();
          const bid = (delBtn.dataset.bid || "").trim();
          if (!bid) return;
          const t = displayBankTitle(b);
          if (!confirm(`确定删除题库「${t}」？其中的题目引用会从本题库移除，题库中的题目文档不会被删除。`))
            return;
          try {
            await apiJson("/question-library/banks/" + encodeURIComponent(bid), {
              method: "DELETE",
            });
            toast("题库已删除", false);
            if (currentBank && currentBank.id === bid) {
              currentBank = null;
              $("bankDetailView").classList.add("hidden");
              $("bankListView").classList.remove("hidden");
            }
            await loadBanks();
          } catch (err) {
            toast(err.message, true);
          }
        });
      }
      box.appendChild(card);
    });
  }

  async function loadBanks() {
    const r = await apiJson("/question-library/banks");
    banksCache = Array.isArray(r.data) ? r.data : [];
    renderBankList();
  }

  function renderSaveBankChecks() {
    const box = $("saveToBankBankList");
    const targets = banksCache.filter((b) => !isSharedInboxBank(b));
    if (!targets.length) {
      box.innerHTML = `<p class="hint">暂无可用题库（共享库仅能通过他人共享自动加入，请新建其他题库）。</p>`;
      return;
    }
    box.innerHTML = "";
    targets.forEach((b) => {
      const lab = document.createElement("label");
      lab.className = "lib-sl-bank-row";
      const bid = escapeHtml(b.id || "");
      const name = escapeHtml(displayBankTitle(b));
      const curId = currentBank && currentBank.id;
      const isCur = curId && b.id === curId;
      lab.innerHTML = `<input type="checkbox" class="lib-sl-bank-cb" value="${bid}" ${isCur ? "checked disabled" : ""} /><span class="lib-sl-bank-name">${name}</span>`;
      box.appendChild(lab);
    });
  }

  async function openLibVersionsModal(row) {
    const lineageId = row.lineage_id || "";
    const bankId = currentBank && currentBank.id;
    const displayId = (row.display_library_question_id || "").trim();
    openModal("libVersionsModal");
    $("libVersionsBody").innerHTML = "<p class=\"empty-hint\">加载中…</p>";
    if (!currentUserId) await fetchMe();
    try {
      const r = await apiJson(
        "/question-library/lineages/" + encodeURIComponent(lineageId) + "/versions"
      );
      const rows = Array.isArray(r.data) ? r.data : [];
      const box = $("libVersionsBody");
      box.innerHTML = "";
      if (!rows.length) {
        box.innerHTML = "<p class=\"empty-hint\">无版本记录</p>";
        return;
      }
      if (bankId && displayId) {
        const bar = document.createElement("div");
        bar.className = "lib-row";
        bar.style.marginBottom = "0.35rem";
        const bUnpinTop = document.createElement("button");
        bUnpinTop.type = "button";
        bUnpinTop.className = "secondary";
        bUnpinTop.textContent = "恢复为始终显示最新版（取消钉选）";
        bUnpinTop.addEventListener("click", async () => {
          try {
            await apiJson(
              "/question-library/banks/" +
                encodeURIComponent(bankId) +
                "/items/display",
              {
                method: "PATCH",
                body: JSON.stringify({
                  lineage_id: lineageId,
                  library_question_id: null,
                }),
              }
            );
            toast("已恢复为最新版", false);
            closeModal("libVersionsModal");
            await loadBankItems();
          } catch (e) {
            toast(e.message, true);
          }
        });
        bar.appendChild(bUnpinTop);
        box.appendChild(bar);
      }
      rows.forEach((v, i) => {
        const wrap = document.createElement("div");
        wrap.className = "ver-version-row";
        if (displayId && v.id === displayId) {
          const tag = document.createElement("div");
          tag.className = "ver-pinned-tag";
          tag.textContent = "当前本题库详情钉选展示";
          wrap.appendChild(tag);
        }
        const prev = document.createElement("div");
        prev.innerHTML = libraryQuestionPreviewBlockHtml(v, i + 1);
        while (prev.firstChild) wrap.appendChild(prev.firstChild);
        const actions = document.createElement("div");
        actions.className = "ver-version-actions";
        if (bankId) {
          const bPin = document.createElement("button");
          bPin.type = "button";
          bPin.className = "secondary";
          bPin.textContent = "在本题库详情中展示此版本";
          bPin.addEventListener("click", async () => {
            try {
              await apiJson(
                "/question-library/banks/" +
                  encodeURIComponent(bankId) +
                  "/items/display",
                {
                  method: "PATCH",
                  body: JSON.stringify({
                    lineage_id: lineageId,
                    library_question_id: v.id,
                  }),
                }
              );
              toast("已固定展示该版本", false);
              closeModal("libVersionsModal");
              await loadBankItems();
            } catch (e) {
              toast(e.message, true);
            }
          });
          actions.appendChild(bPin);
        }
        const mine = String(v.owner_id || "") === String(currentUserId || "");
        if (mine) {
          const bDel = document.createElement("button");
          bDel.type = "button";
          bDel.className = "secondary";
          bDel.style.borderColor = "#991b1b";
          bDel.style.color = "#fecaca";
          bDel.textContent = "删除此版本";
          bDel.addEventListener("click", async () => {
            if (
              !confirm(
                "确定删除该版本？后续版本会接到上一版；钉选该版时展示将恢复为最新版。"
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
              toast("已删除", false);
              await loadBankItems();
              await openLibVersionsModal({
                lineage_id: lineageId,
                display_library_question_id:
                  displayId === v.id ? "" : displayId,
              });
            } catch (e) {
              toast(e.message, true);
            }
          });
          actions.appendChild(bDel);
        }
        wrap.appendChild(actions);
        box.appendChild(wrap);
      });
    } catch (e) {
      $("libVersionsBody").innerHTML = `<p class="err">${escapeHtml(
        e.message
      )}</p>`;
    }
  }

  async function loadBankItems() {
    if (!currentBank) return;
    const box = $("bankItems");
    box.innerHTML = "加载中…";
    try {
      const r = await apiJson(
        "/question-library/banks/" + encodeURIComponent(currentBank.id) + "/items"
      );
      const rows = Array.isArray(r.data) ? r.data : [];
      if (!rows.length) {
        const emptyMsg = isSharedInboxBank(currentBank)
          ? "暂无他人共享给您的题目。请对方在题目上点击「共享」并填写您的用户名。"
          : "该题库暂时没有题目，可点击上方「在此题库新建题目」。";
        box.innerHTML = `<div class="empty">${emptyMsg}</div>`;
        return;
      }
      box.innerHTML = "";
      rows.forEach((row) => {
        const item = row.library_question || {};
        const isMine = String(item.owner_id || "") === String(currentUserId || "");
        const pinned = !!(row.display_library_question_id || "").trim();
        const card = document.createElement("div");
        card.className = "item-card";
        card.innerHTML = `
          <div class="item-head">
            <span class="badge ${isMine ? "badge-mine" : "badge-shared"}">${isMine ? "我的" : "共享"}</span>
            <strong>${escapeHtml(item.title || "（无标题）")}</strong>
            ${pinned ? '<span class="ver-pinned-tag">已钉选展示某历史版本</span>' : ""}
          </div>
          <div class="actions">
            ${isMine ? '<button type="button" class="secondary act-edit">编辑</button>' : ""}
            <button type="button" class="secondary act-save">保存到题库</button>
            <button type="button" class="secondary act-ver">历史版本</button>
            <button type="button" class="secondary act-usage">使用方</button>
            <div class="actions-tail">
              <button type="button" class="secondary act-stats">统计</button>
              ${isMine ? '<button type="button" class="secondary act-share btn-lib-share">共享</button>' : ""}
              <button type="button" class="secondary act-remove btn-lib-del">删除</button>
            </div>
          </div>`;
        const ed = card.querySelector(".act-edit");
        if (ed) {
          ed.addEventListener("click", () =>
            openEditLibraryGate(item.id || "")
          );
        }
        card.querySelector(".act-save").addEventListener("click", () => {
          $("saveToBankLibQuestionId").value = item.id || "";
          renderSaveBankChecks();
          openModal("saveToBankModal");
        });
        card.querySelector(".act-ver").addEventListener("click", () => {
          openLibVersionsModal(row);
        });
        card.querySelector(".act-usage").addEventListener("click", () => {
          openUsageModalLineage(row.lineage_id || "");
        });
        card.querySelector(".act-stats").addEventListener("click", () => {
          openLibStatsModal(row.lineage_id || "");
        });
        card.querySelector(".act-remove").addEventListener("click", async () => {
          if (!confirm("确定从本题库删除该题（整道题目家族）？仅从本题库移除，不会删除题库题目文档。"))
            return;
          const bid = currentBank && currentBank.id;
          const lid = item.id || row.lineage_id || "";
          if (!bid || !lid) return;
          try {
            await apiJson(
              "/question-library/banks/" +
                encodeURIComponent(bid) +
                "/items/" +
                encodeURIComponent(lid),
              { method: "DELETE" }
            );
            toast("已从本题库删除", false);
            await loadBankItems();
          } catch (e) {
            toast(e.message, true);
          }
        });
        if (isMine) {
          card.querySelector(".act-share").addEventListener("click", () => {
            $("shareLineageId").value = row.lineage_id || "";
            $("shareUsername").value = "";
            openModal("shareModal");
            $("shareUsername").focus();
          });
        }
        box.appendChild(card);
      });
    } catch (e) {
      box.innerHTML = `<p class="err">${escapeHtml(e.message)}</p>`;
    }
  }

  async function saveLibQuestionModal() {
    if (!currentBank) {
      toast("请先进入题库详情", true);
      return;
    }
    if (isSharedInboxBank(currentBank)) {
      toast("共享库内不能新建或编辑题目", true);
      return;
    }
    const title = $("libQmTitle").value.trim();
    const type = $("libQmType").value;
    if (!title) {
      toast("请填写题目标题", true);
      return;
    }
    const options = collectOptions();
    if ((type === "single_choice" || type === "multiple_choice") && !options.length) {
      toast("请至少添加一个选项", true);
      return;
    }
    const payload = {
      title,
      type,
      required: $("libQmRequired").checked,
      options: type === "single_choice" || type === "multiple_choice" ? options : [],
      validation: collectValidation(),
      bank_ids: [currentBank.id],
    };
    try {
      if (editingLibraryQuestionId) {
        if (libraryEditMode === "inplace") {
          const putBody = {
            title,
            type,
            required: $("libQmRequired").checked,
            options:
              type === "single_choice" || type === "multiple_choice"
                ? options
                : [],
            validation: collectValidation(),
          };
          await apiJson(
            "/question-library/items/" +
              encodeURIComponent(editingLibraryQuestionId),
            {
              method: "PUT",
              body: JSON.stringify(putBody),
            }
          );
          toast("已更新当前版本", false);
        } else {
          await apiJson(
            "/question-library/items/" +
              encodeURIComponent(editingLibraryQuestionId) +
              "/versions",
            {
              method: "POST",
              body: JSON.stringify(payload),
            }
          );
          toast("已保存为新版本并保留在本题库", false);
        }
      } else {
        await apiJson("/question-library/items", {
          method: "POST",
          body: JSON.stringify(payload),
        });
        toast("已创建并加入当前题库", false);
      }
      closeModal("libQuestionModal");
      resetQuestionModal();
      await loadBankItems();
    } catch (e) {
      toast(e.message, true);
    }
  }

  async function saveToOtherBanks() {
    const lqid = $("saveToBankLibQuestionId").value.trim();
    if (!lqid) return;
    const ids = [...$("saveToBankBankList").querySelectorAll("input.lib-sl-bank-cb:checked")]
      .map((el) => el.value.trim())
      .filter(Boolean);
    if (!ids.length) {
      toast("请至少选择一个题库", true);
      return;
    }
    let added = 0;
    let skipped = 0;
    for (const bid of ids) {
      try {
        await apiJson("/question-library/banks/" + encodeURIComponent(bid) + "/items", {
          method: "POST",
          body: JSON.stringify({ library_question_id: lqid }),
        });
        added += 1;
      } catch (e) {
        if (String(e.message || "").includes("已在题库")) skipped += 1;
        else {
          toast(e.message, true);
          return;
        }
      }
    }
    closeModal("saveToBankModal");
    toast(
      added ? `已加入 ${added} 个题库` : skipped ? "所选题库中均已包含该题" : "完成",
      false
    );
    await loadBanks();
    await loadBankItems();
  }

  async function doShare() {
    const lineage_id = $("shareLineageId").value.trim();
    const grantee_username = $("shareUsername").value.trim();
    if (!lineage_id || !grantee_username) {
      toast("请填写对方用户名", true);
      return;
    }
    try {
      await apiJson("/question-library/shares", {
        method: "POST",
        body: JSON.stringify({ lineage_id, grantee_username }),
      });
      closeModal("shareModal");
      toast("共享成功", false);
    } catch (e) {
      toast(e.message, true);
    }
  }

  function openNewBankPanel() {
    const panel = $("bankNewBankPanel");
    panel.classList.remove("hidden");
    $("bankTitle").focus();
  }

  function closeNewBankPanel() {
    $("bankNewBankPanel").classList.add("hidden");
    $("bankTitle").value = "";
  }

  $("btnShowNewBank").addEventListener("click", () => openNewBankPanel());
  $("btnCancelNewBank").addEventListener("click", () => closeNewBankPanel());

  $("btnCreateBank").addEventListener("click", async () => {
    const title = $("bankTitle").value.trim();
    if (!title) {
      toast("题库名称不能为空", true);
      return;
    }
    try {
      await apiJson("/question-library/banks", {
        method: "POST",
        body: JSON.stringify({ title, description: "" }),
      });
      closeNewBankPanel();
      toast("题库已创建", false);
      await loadBanks();
    } catch (e) {
      toast(e.message, true);
    }
  });

  $("btnConfirmRenameBank").addEventListener("click", async () => {
    const bid = ($("renameBankId").value || "").trim();
    const title = ($("renameBankTitle").value || "").trim();
    if (!bid) return;
    if (!title) {
      toast("题库名称不能为空", true);
      return;
    }
    try {
      await apiJson("/question-library/banks/" + encodeURIComponent(bid), {
        method: "PUT",
        body: JSON.stringify({ title }),
      });
      closeModal("renameBankModal");
      toast("已重命名", false);
      await loadBanks();
      if (currentBank && currentBank.id === bid) {
        const nb = banksCache.find((x) => x.id === bid);
        if (nb) {
          currentBank = nb;
          $("bankDetailTitle").textContent = `题库详情：${displayBankTitle(nb)}`;
        }
      }
    } catch (e) {
      toast(e.message, true);
    }
  });

  $("btnRefreshBanks").addEventListener("click", loadBanks);
  $("btnBackToBanks").addEventListener("click", () => {
    currentBank = null;
    $("bankDetailView").classList.add("hidden");
    $("bankListView").classList.remove("hidden");
    loadBanks();
  });
  $("btnRefreshBankItems").addEventListener("click", loadBankItems);
  $("btnOpenCreateInBank").addEventListener("click", () => {
    if (!currentBank) {
      toast("请先进入题库详情", true);
      return;
    }
    resetQuestionModal();
    openModal("libQuestionModal");
  });
  $("libQmType").addEventListener("change", onTypeChange);
  $("libQmAddOption").addEventListener("click", () => addOptionRow("", ""));
  $("libQmSave").addEventListener("click", saveLibQuestionModal);
  $("btnConfirmSaveToBank").addEventListener("click", saveToOtherBanks);
  $("btnConfirmShare").addEventListener("click", doShare);

  $("btnLibStatsExportJson").addEventListener("click", () => {
    if (!libLineageStatsPayload) {
      toast("暂无数据可导出", true);
      return;
    }
    const lid = String(libLineageStatsPayload.lineage_id || "lineage").replace(
      /[^a-zA-Z0-9_-]/g,
      "_"
    );
    downloadTextFile(
      JSON.stringify(libLineageStatsPayload, null, 2),
      `lineage-${lid}-stats.json`,
      "application/json;charset=utf-8"
    );
  });
  $("btnLibStatsExportCsv").addEventListener("click", () => {
    if (!libLineageStatsPayload) {
      toast("暂无数据可导出", true);
      return;
    }
    const lid = String(libLineageStatsPayload.lineage_id || "lineage").replace(
      /[^a-zA-Z0-9_-]/g,
      "_"
    );
    downloadTextFile(
      buildLineageStatsCsv(libLineageStatsPayload),
      `lineage-${lid}-stats.csv`,
      "text/csv;charset=utf-8"
    );
  });

  $("libEditGateInPlace").addEventListener("click", async () => {
    const id = ($("libEditGatePendingId").value || "").trim();
    if (!id) return;
    closeModal("libEditGateModal");
    await openLibQuestionEditor(id, "inplace");
  });
  $("libEditGateNewVersion").addEventListener("click", async () => {
    const id = ($("libEditGatePendingId").value || "").trim();
    if (!id) return;
    closeModal("libEditGateModal");
    await openLibQuestionEditor(id, "newversion");
  });

  document.querySelectorAll("[data-close-modal]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const mid = btn.dataset.closeModal;
      closeModal(mid);
      if (mid === "libQuestionModal") {
        resetQuestionModal();
      }
    });
  });
  (async function init() {
    await fetchMe();
    await loadBanks();
  })();
})();

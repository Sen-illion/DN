const STORAGE_PREFIX = "dn-human-eval";
const DEFAULT_EVALUATOR = "anonymous";

const fallbackDataset = {
  studyTitle: "文本与图片一致性人类测评",
  instructions: [
    "请先完整阅读当前主题下的 5 段中文剧情，再比较两个匿名方案各自对应的连续图片。",
    "界面只显示方案 A / 方案 B，不显示系统身份；请只根据内容本身评分。",
    "所有分数为 1-10 分：1 表示严重不一致或不可用，10 表示高度一致且质量优秀。"
  ],
  dimensions: [
    { id: "image_consistency", label: "图片一致性", help: "连续图片是否与对应文本中的人物、场景、动作、道具和氛围一致。" },
    { id: "sequence_consistency", label: "连续性", help: "5 张图之间的人物形象、场景风格和时间推进是否稳定连续。" },
    { id: "visual_quality", label: "视觉质量", help: "图片是否清晰自然，是否存在明显崩坏、乱码或异常。" },
    { id: "image_text_alignment", label: "图文匹配", help: "整组图片是否准确表达这 5 段中文剧情。" },
    { id: "overall", label: "综合评分", help: "该匿名方案作为一组连续图文结果的总体质量。" }
  ],
  cases: [
    {
      id: "fallback_theme",
      title: "示例主题：请通过 token 或导入数据加载正式任务",
      prompt: [
        "当前是兜底示例，用来确认界面和评分流程能正常打开。",
        "正式使用时，请通过邀请链接中的 token 自动加载被分配的主题。"
      ],
      context: [
        "正式数据会包含 5 段中文剧情和两个匿名方案的连续 5 张图片。",
        "如果你是直接双击打开网页，建议改用本地 HTTP server 或 Flask 服务。"
      ],
      storySegments: [
        "示例第 1 段：这里会展示正式主题的第 1 段中文剧情。",
        "示例第 2 段：这里会展示正式主题的第 2 段中文剧情。",
        "示例第 3 段：这里会展示正式主题的第 3 段中文剧情。",
        "示例第 4 段：这里会展示正式主题的第 4 段中文剧情。",
        "示例第 5 段：这里会展示正式主题的第 5 段中文剧情。"
      ],
      candidates: [
        { system: "ours", images: [] },
        { system: "baseline", images: [] }
      ]
    }
  ]
};

const state = {
  dataset: fallbackDataset,
  currentIndex: 0,
  evaluatorId: DEFAULT_EVALUATOR,
  ratings: {},
  submittedCases: {},
  warning: "",
  datasetSourceLabel: "当前使用内置兜底样本。",
  datasetSourceType: "fallback",
  assignment: null,
  syncStatus: "尚未同步到服务器。"
};

const els = {};

document.addEventListener("DOMContentLoaded", async () => {
  bindElements();
  bindEvents();
  loadEvaluator();
  await loadDataset();
  loadProgress();
  renderAll();
});

function bindElements() {
  Object.assign(els, {
    title: document.querySelector("#study-title"),
    progressLabel: document.querySelector("#progress-label"),
    progressBar: document.querySelector("#progress-bar"),
    evaluatorId: document.querySelector("#evaluator-id"),
    instructionList: document.querySelector("#instruction-list"),
    shareLink: document.querySelector("#share-link"),
    datasetSource: document.querySelector("#dataset-source"),
    copyLink: document.querySelector("#copy-link"),
    datasetFile: document.querySelector("#dataset-file"),
    resetProgress: document.querySelector("#reset-progress"),
    prevCase: document.querySelector("#prev-case"),
    nextCase: document.querySelector("#next-case"),
    sampleIndex: document.querySelector("#sample-index"),
    caseTitle: document.querySelector("#case-title"),
    casePrompt: document.querySelector("#case-prompt"),
    caseContext: document.querySelector("#case-context"),
    storySegments: document.querySelector("#story-segments"),
    warning: document.querySelector("#completion-warning"),
    candidateList: document.querySelector("#candidate-list"),
    candidateTemplate: document.querySelector("#candidate-template"),
    caseStatus: document.querySelector("#case-status"),
    submitCase: document.querySelector("#submit-case"),
    syncStatus: document.querySelector("#sync-status"),
    syncResults: document.querySelector("#sync-results"),
    exportJson: document.querySelector("#export-json"),
    exportCsv: document.querySelector("#export-csv")
  });
}

function bindEvents() {
  els.evaluatorId.addEventListener("input", () => {
    state.evaluatorId = normalizeEvaluatorId(els.evaluatorId.value);
    localStorage.setItem(`${STORAGE_PREFIX}:evaluator`, els.evaluatorId.value.trim());
    loadProgress();
    renderAll();
  });

  els.copyLink.addEventListener("click", copyCurrentLink);
  els.datasetFile.addEventListener("change", handleDatasetImport);
  els.resetProgress.addEventListener("click", resetProgress);
  els.prevCase.addEventListener("click", () => navigateCase(-1));
  els.nextCase.addEventListener("click", () => navigateCase(1));
  els.submitCase.addEventListener("click", async () => {
    await submitCurrentCase();
  });
  els.syncResults.addEventListener("click", async () => {
    await syncResultsToServer({ manual: true });
  });
  els.exportJson.addEventListener("click", () => exportResults("json"));
  els.exportCsv.addEventListener("click", () => exportResults("csv"));
}

async function loadDataset() {
  const params = new URLSearchParams(window.location.search);
  const token = params.get("token");
  if (token) {
    const loaded = await loadAssignedTheme(token);
    if (loaded) {
      return;
    }
  }

  const { datasetPath, datasetLabel } = getDatasetRequest();
  try {
    const response = await fetch(datasetPath, { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const rawText = await response.text();
    state.dataset = validateDataset(parseDatasetText(rawText));
    state.datasetSourceLabel = datasetLabel;
    state.datasetSourceType = "hosted";
    state.syncStatus = "当前页面未绑定邀请 token，只会保存在本地浏览器和导出文件中。";
  } catch (error) {
    console.warn("Using fallback dataset:", error);
    state.dataset = fallbackDataset;
    state.datasetSourceLabel = "当前使用内置兜底样本。若要正式分发主题，请通过邀请链接中的 token 加载。";
    state.datasetSourceType = "fallback";
    state.warning = "未能自动加载正式数据。若当前是直接双击打开网页，请改用本地服务或手动导入 JSON。";
    state.syncStatus = "尚未连接到结果回传接口。";
  }
}

async function loadAssignedTheme(token) {
  try {
    const response = await fetch(`/api/session?token=${encodeURIComponent(token)}`, { cache: "no-store" });
    if (!response.ok) {
      const errorBody = await response.json().catch(() => ({}));
      throw new Error(errorBody.error || `HTTP ${response.status}`);
    }

    const payload = await response.json();
    state.assignment = payload.assignment || null;
    state.dataset = validateDataset(payload.dataset);
    state.datasetSourceType = "api-token";
    state.datasetSourceLabel = `当前主题来自邀请链接分配：${payload.assignment?.themeTitle || payload.assignment?.themeId || "未命名主题"}。`;
    state.syncStatus = payload.assignment?.submittedAt
      ? `该邀请链接已在服务器记录提交时间：${payload.assignment.submittedAt}`
      : "提交当前样本后，结果会自动同步到服务器，并同时保留在本地浏览器中。";
    if (payload.assignment?.evaluatorId && !localStorage.getItem(`${STORAGE_PREFIX}:evaluator`)) {
      els.evaluatorId.value = payload.assignment.evaluatorId;
      state.evaluatorId = normalizeEvaluatorId(payload.assignment.evaluatorId);
    }
    return true;
  } catch (error) {
    state.warning = `未能通过 token 加载正式主题：${error.message}`;
    state.syncStatus = "token 加载失败，当前只能使用本地兜底或手动导入数据。";
    return false;
  }
}

function validateDataset(dataset) {
  if (!dataset || !Array.isArray(dataset.cases) || dataset.cases.length === 0) {
    throw new Error("dataset.cases must be a non-empty array");
  }
  if (!Array.isArray(dataset.dimensions) || dataset.dimensions.length === 0) {
    throw new Error("dataset.dimensions must be a non-empty array");
  }
  return {
    studyTitle: dataset.studyTitle || fallbackDataset.studyTitle,
    instructions: Array.isArray(dataset.instructions) ? dataset.instructions : fallbackDataset.instructions,
    dimensions: dataset.dimensions,
    cases: dataset.cases.map((item) => ({
      ...item,
      storySegments: normalizeParagraphs(item.storySegments || item.sharedText || item.story || [])
    }))
  };
}

function loadEvaluator() {
  const params = new URLSearchParams(window.location.search);
  const urlEvaluator = params.get("evaluator");
  if (urlEvaluator) {
    els.evaluatorId.value = urlEvaluator;
    state.evaluatorId = normalizeEvaluatorId(urlEvaluator);
    return;
  }
  const stored = localStorage.getItem(`${STORAGE_PREFIX}:evaluator`) || "";
  els.evaluatorId.value = stored;
  state.evaluatorId = normalizeEvaluatorId(stored);
}

function loadProgress() {
  const saved = readProgress();
  state.ratings = saved.ratings || {};
  state.submittedCases = saved.submittedCases || {};
}

function readProgress() {
  try {
    return JSON.parse(localStorage.getItem(storageKey()) || "{}");
  } catch {
    return {};
  }
}

function saveProgress() {
  localStorage.setItem(
    storageKey(),
    JSON.stringify({
      datasetKey: datasetKey(),
      evaluatorId: state.evaluatorId,
      ratings: state.ratings,
      submittedCases: state.submittedCases,
      savedAt: new Date().toISOString()
    })
  );
}

function storageKey() {
  return `${STORAGE_PREFIX}:progress:${datasetKey()}:${state.evaluatorId}`;
}

function datasetKey() {
  const ids = state.dataset.cases.map((item) => item.id).join("|");
  return simpleHash(`${state.dataset.studyTitle}|${ids}`);
}

function normalizeEvaluatorId(value) {
  const trimmed = String(value || "").trim();
  return trimmed || DEFAULT_EVALUATOR;
}

function renderAll() {
  const cases = state.dataset.cases;
  if (state.currentIndex >= cases.length) {
    state.currentIndex = Math.max(0, cases.length - 1);
  }

  els.title.textContent = state.dataset.studyTitle;
  renderInstructions();
  renderShareInfo();
  renderProgress();
  renderCase();
}

function renderInstructions() {
  els.instructionList.innerHTML = "";
  state.dataset.instructions.forEach((instruction) => {
    const item = document.createElement("p");
    item.className = "instruction-item";
    item.textContent = instruction;
    els.instructionList.appendChild(item);
  });
}

function renderShareInfo() {
  els.shareLink.textContent = resolveShareUrl();
  els.datasetSource.textContent = state.datasetSourceLabel;
}

function renderProgress() {
  const total = state.dataset.cases.length;
  const completed = state.dataset.cases.filter((item) => state.submittedCases[item.id]).length;
  const percent = total ? Math.round((completed / total) * 100) : 0;

  els.progressLabel.textContent = `${completed} / ${total} 已完成`;
  els.progressBar.style.width = `${percent}%`;
}

function renderCase() {
  const currentCase = getCurrentCase();
  const total = state.dataset.cases.length;
  const caseComplete = isCaseComplete(currentCase);
  const caseSubmitted = Boolean(state.submittedCases[currentCase.id]);

  els.sampleIndex.textContent = `主题 ${state.currentIndex + 1} / ${total}`;
  els.caseTitle.textContent = currentCase.title || currentCase.id;
  els.casePrompt.textContent = formatDisplayText(currentCase.prompt, "未提供主题说明。");
  els.caseContext.textContent = formatDisplayText(currentCase.context, "未提供参考上下文。");
  els.prevCase.disabled = state.currentIndex === 0;
  els.nextCase.disabled = state.currentIndex >= total - 1;
  els.submitCase.disabled = !caseComplete;
  els.caseStatus.textContent = caseSubmitted ? "当前主题已提交" : caseComplete ? "当前主题可提交" : "当前主题未完成";
  els.syncStatus.textContent = state.syncStatus;

  if (state.warning) {
    els.warning.hidden = false;
    els.warning.textContent = state.warning;
  } else {
    els.warning.hidden = true;
    els.warning.textContent = "";
  }

  renderStorySegments(currentCase.storySegments || []);
  renderCandidates(currentCase);
}

function renderStorySegments(segments) {
  els.storySegments.innerHTML = "";
  if (!segments.length) {
    const empty = document.createElement("p");
    empty.className = "helper-text";
    empty.textContent = "当前主题未提供连续文本。";
    els.storySegments.appendChild(empty);
    return;
  }

  segments.forEach((segment, index) => {
    const block = document.createElement("article");
    block.className = "story-segment";

    const title = document.createElement("p");
    title.className = "story-segment-title";
    title.textContent = `第 ${index + 1} 段`;

    const body = document.createElement("p");
    body.className = "rich-copy";
    body.textContent = segment;

    block.append(title, body);
    els.storySegments.appendChild(block);
  });
}

function renderCandidates(currentCase) {
  els.candidateList.innerHTML = "";
  getAnonymousCandidates(currentCase).forEach((candidate) => {
    const fragment = els.candidateTemplate.content.cloneNode(true);
    const card = fragment.querySelector(".candidate-card");
    const label = fragment.querySelector(".candidate-label");
    const completion = fragment.querySelector(".candidate-completion");
    const imageStrip = fragment.querySelector(".image-strip");
    const ratingList = fragment.querySelector(".rating-list");
    const note = fragment.querySelector("textarea");
    const complete = isCandidateComplete(currentCase.id, candidate.label);

    card.dataset.label = candidate.label;
    card.classList.toggle("is-complete", complete);
    label.textContent = `方案 ${candidate.label}`;
    completion.textContent = complete ? "已完成" : "待评分";

    renderImages(imageStrip, candidate.images || []);
    renderRatings(ratingList, currentCase.id, candidate.label);

    note.value = getCandidateState(currentCase.id, candidate.label).note || "";
    note.addEventListener("input", () => {
      const candidateState = getCandidateState(currentCase.id, candidate.label);
      candidateState.note = note.value;
      state.submittedCases[currentCase.id] = false;
      saveProgress();
      renderProgress();
    });

    els.candidateList.appendChild(fragment);
  });
}

function renderImages(container, images) {
  container.innerHTML = "";

  if (!images.length) {
    const empty = document.createElement("p");
    empty.className = "image-caption";
    empty.textContent = "未提供图片。";
    container.appendChild(empty);
    return;
  }

  images.forEach((src, index) => {
    const frame = document.createElement("figure");
    frame.className = "image-frame";

    const img = document.createElement("img");
    img.src = src;
    img.alt = `候选方案图片 ${index + 1}`;
    img.loading = "lazy";

    const caption = document.createElement("figcaption");
    caption.className = "image-caption";
    caption.textContent = `第 ${index + 1} 张`;

    frame.append(img, caption);
    container.appendChild(frame);
  });
}

function renderRatings(container, caseId, label) {
  container.innerHTML = "";
  const candidateState = getCandidateState(caseId, label);
  const missing = getMissingDimensions(caseId, label);

  state.dataset.dimensions.forEach((dimension) => {
    const row = document.createElement("div");
    row.className = "rating-row";
    row.classList.toggle("is-missing", missing.includes(dimension.id));

    const heading = document.createElement("div");
    heading.className = "rating-label";
    heading.innerHTML = `<span>${escapeHtml(dimension.label)}</span><span>${candidateState.scores?.[dimension.id] || "-"} / 10</span>`;

    const help = document.createElement("div");
    help.className = "rating-help";
    help.textContent = dimension.help || "";

    const options = document.createElement("div");
    options.className = "rating-options";
    options.setAttribute("role", "radiogroup");
    options.setAttribute("aria-label", dimension.label);

    for (let score = 1; score <= 10; score += 1) {
      const button = document.createElement("button");
      button.className = "rating-option";
      button.type = "button";
      button.textContent = score;
      button.setAttribute("aria-pressed", String(candidateState.scores?.[dimension.id] === score));
      button.classList.toggle("is-selected", candidateState.scores?.[dimension.id] === score);
      button.addEventListener("click", () => {
        setScore(caseId, label, dimension.id, score);
      });
      options.appendChild(button);
    }

    row.append(heading, help, options);
    container.appendChild(row);
  });
}

function setScore(caseId, label, dimensionId, score) {
  const candidateState = getCandidateState(caseId, label);
  candidateState.scores = candidateState.scores || {};
  candidateState.scores[dimensionId] = score;
  state.submittedCases[caseId] = false;
  state.warning = "";
  saveProgress();
  renderProgress();
  renderCase();
}

function getCurrentCase() {
  return state.dataset.cases[state.currentIndex];
}

function getAnonymousCandidates(currentCase) {
  const candidates = Array.isArray(currentCase.candidates) ? [...currentCase.candidates] : [];
  const sorted = candidates
    .map((candidate, index) => ({ ...candidate, originalIndex: index }))
    .sort((a, b) => {
      const aHash = simpleHash(`${state.evaluatorId}|${currentCase.id}|${a.system}|${a.originalIndex}`);
      const bHash = simpleHash(`${state.evaluatorId}|${currentCase.id}|${b.system}|${b.originalIndex}`);
      return aHash.localeCompare(bHash);
    });

  return sorted.map((candidate, index) => ({
    ...candidate,
    label: String.fromCharCode(65 + index)
  }));
}

function getCandidateState(caseId, label) {
  state.ratings[caseId] = state.ratings[caseId] || {};
  state.ratings[caseId][label] = state.ratings[caseId][label] || { scores: {}, note: "" };
  return state.ratings[caseId][label];
}

function getMissingDimensions(caseId, label) {
  const candidateState = getCandidateState(caseId, label);
  return state.dataset.dimensions
    .map((dimension) => dimension.id)
    .filter((dimensionId) => !Number.isInteger(candidateState.scores?.[dimensionId]));
}

function isCandidateComplete(caseId, label) {
  return getMissingDimensions(caseId, label).length === 0;
}

function isCaseComplete(currentCase) {
  return getAnonymousCandidates(currentCase).every((candidate) => isCandidateComplete(currentCase.id, candidate.label));
}

async function submitCurrentCase() {
  const currentCase = getCurrentCase();
  const missingLabels = getAnonymousCandidates(currentCase)
    .filter((candidate) => !isCandidateComplete(currentCase.id, candidate.label))
    .map((candidate) => `方案 ${candidate.label}`);

  if (missingLabels.length) {
    state.warning = `请先完成 ${missingLabels.join("、")} 的所有必填评分。`;
    renderCase();
    return;
  }

  state.submittedCases[currentCase.id] = new Date().toISOString();
  state.warning = "";
  saveProgress();
  renderAll();

  if (state.assignment?.token) {
    await syncResultsToServer({ manual: false });
  } else {
    state.syncStatus = "当前没有绑定 token，结果仅保存在本地浏览器中；如需汇总，请导出 JSON 或 CSV。";
    renderCase();
  }
}

function navigateCase(delta) {
  const nextIndex = state.currentIndex + delta;
  if (nextIndex < 0 || nextIndex >= state.dataset.cases.length) {
    return;
  }
  state.currentIndex = nextIndex;
  state.warning = "";
  renderCase();
}

async function handleDatasetImport(event) {
  const [file] = event.target.files;
  if (!file) {
    return;
  }

  try {
    const text = await file.text();
    state.dataset = validateDataset(parseDatasetText(text));
    state.currentIndex = 0;
    state.assignment = null;
    state.datasetSourceType = "local-import";
    state.datasetSourceLabel = `当前数据来自手动导入的本地文件：${file.name}。该数据文件本身不会随网页链接自动共享。`;
    state.syncStatus = "手动导入模式下不会自动回传到服务器，除非你改用带 token 的邀请链接。";
    state.warning = `已导入 ${file.name}。`;
    loadProgress();
    renderAll();
  } catch (error) {
    state.warning = `导入失败：${error.message}`;
    renderCase();
  } finally {
    event.target.value = "";
  }
}

function resetProgress() {
  if (!window.confirm("确定要清空当前评测者在当前数据集下的本地评分进度吗？")) {
    return;
  }
  localStorage.removeItem(storageKey());
  state.ratings = {};
  state.submittedCases = {};
  state.warning = "本地进度已清空。";
  renderAll();
}

async function syncResultsToServer({ manual }) {
  if (!state.assignment?.token) {
    state.warning = "当前链接未绑定 token，无法自动回传到服务器。";
    renderCase();
    return;
  }

  try {
    const response = await fetch("/api/submit", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        token: state.assignment.token,
        evaluatorId: state.evaluatorId,
        assignment: state.assignment,
        payload: buildExportPayload()
      })
    });

    const result = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(result.error || `HTTP ${response.status}`);
    }

    state.syncStatus = manual
      ? `已重新同步到服务器：${result.savedAt}`
      : `提交成功，服务器已记录：${result.savedAt}`;
    state.warning = manual ? "结果已重新同步到服务器。" : "";
    renderCase();
  } catch (error) {
    state.syncStatus = `服务器同步失败：${error.message}`;
    state.warning = "结果仍保存在当前浏览器和导出文件中，但未成功回传到服务器。";
    renderCase();
  }
}

function exportResults(format) {
  const payload = buildExportPayload();
  const timestamp = new Date().toISOString().replace(/[:.]/g, "-");

  if (format === "json") {
    downloadFile(
      `human_eval_results_${timestamp}.json`,
      JSON.stringify(payload, null, 2),
      "application/json"
    );
    return;
  }

  downloadFile(
    `human_eval_results_${timestamp}.csv`,
    toCsv(payload),
    "text/csv;charset=utf-8"
  );
}

function buildExportPayload() {
  const exportedAt = new Date().toISOString();
  const cases = state.dataset.cases.map((currentCase) => {
    const anonymousCandidates = getAnonymousCandidates(currentCase);
    return {
      caseId: currentCase.id,
      title: currentCase.title || "",
      submittedAt: state.submittedCases[currentCase.id] || null,
      storySegments: currentCase.storySegments || [],
      mapping: Object.fromEntries(anonymousCandidates.map((candidate) => [candidate.label, candidate.system || "unknown"])),
      ratings: anonymousCandidates.map((candidate) => {
        const candidateState = getCandidateState(currentCase.id, candidate.label);
        return {
          anonymousLabel: candidate.label,
          system: candidate.system || "unknown",
          imageCount: Array.isArray(candidate.images) ? candidate.images.length : 0,
          scores: candidateState.scores || {},
          note: candidateState.note || "",
          complete: isCandidateComplete(currentCase.id, candidate.label)
        };
      })
    };
  });

  return {
    studyTitle: state.dataset.studyTitle,
    evaluatorId: state.evaluatorId,
    exportedAt,
    assignment: state.assignment,
    dimensions: state.dataset.dimensions,
    cases
  };
}

function toCsv(payload) {
  const columns = [
    "studyTitle",
    "evaluatorId",
    "themeId",
    "exportedAt",
    "caseId",
    "caseTitle",
    "submittedAt",
    "anonymousLabel",
    "system",
    "imageCount",
    "dimensionId",
    "dimensionLabel",
    "score",
    "note",
    "complete"
  ];
  const rows = [columns];

  payload.cases.forEach((caseResult) => {
    caseResult.ratings.forEach((rating) => {
      payload.dimensions.forEach((dimension) => {
        rows.push([
          payload.studyTitle,
          payload.evaluatorId,
          payload.assignment?.themeId || "",
          payload.exportedAt,
          caseResult.caseId,
          caseResult.title,
          caseResult.submittedAt || "",
          rating.anonymousLabel,
          rating.system,
          rating.imageCount,
          dimension.id,
          dimension.label,
          rating.scores?.[dimension.id] || "",
          rating.note,
          rating.complete
        ]);
      });
    });
  });

  return rows.map((row) => row.map(csvEscape).join(",")).join("\n");
}

function csvEscape(value) {
  const stringValue = String(value ?? "");
  if (/[",\n\r]/.test(stringValue)) {
    return `"${stringValue.replace(/"/g, '""')}"`;
  }
  return stringValue;
}

function downloadFile(filename, content, type) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function getDatasetRequest() {
  const params = new URLSearchParams(window.location.search);
  const requestedDataset = params.get("dataset");
  if (requestedDataset) {
    return {
      datasetPath: requestedDataset,
      datasetLabel: `当前数据来自链接参数中的 dataset：${requestedDataset}`
    };
  }
  return {
    datasetPath: "data/dataset.json",
    datasetLabel: "当前数据来自站点内置的 data/dataset.json。部署后把站点链接发给别人即可访问同一份数据。"
  };
}

function parseDatasetText(text) {
  return JSON.parse(String(text || "").replace(/^\uFEFF/, ""));
}

function formatDisplayText(value, fallback) {
  const parts = normalizeParagraphs(value);
  return parts.length ? parts.join("\n\n") : fallback;
}

function normalizeParagraphs(value) {
  if (Array.isArray(value)) {
    return value.map((item) => String(item || "").trim()).filter(Boolean);
  }
  const text = String(value || "").trim();
  if (!text) {
    return [];
  }
  if (text.includes("\n\n")) {
    return text.split(/\n{2,}/).map((item) => item.trim()).filter(Boolean);
  }
  return [text];
}

function resolveShareUrl() {
  return new URL(window.location.href).toString();
}

async function copyCurrentLink() {
  const url = resolveShareUrl();
  try {
    await navigator.clipboard.writeText(url);
    state.warning = "当前链接已复制。这个链接如果带有 token，接收者会看到被分配到的固定主题。";
  } catch {
    state.warning = `复制失败，请手动复制：${url}`;
  }
  renderCase();
}

function simpleHash(input) {
  let hash = 2166136261;
  const text = String(input);
  for (let index = 0; index < text.length; index += 1) {
    hash ^= text.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0).toString(16).padStart(8, "0");
}

function escapeHtml(value) {
  const span = document.createElement("span");
  span.textContent = value;
  return span.innerHTML;
}

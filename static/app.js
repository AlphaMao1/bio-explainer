const tabs = ["morphology", "evolution", "ecology"];
const providerDefaults = {
  deepseek: { baseUrl: "https://api.deepseek.com/v1", model: "deepseek-chat" },
  openai: { baseUrl: "https://api.openai.com/v1", model: "gpt-4.1-mini" },
  claude: { baseUrl: "", model: "claude-3-5-sonnet-latest" },
};
const imageDefaults = {
  baseUrl: "",
  model: "gpt-image-1",
  resolution: "2k",
  quality: "medium",
};

const state = {
  query: "",
  lang: "zh",
  activeTab: "morphology",
  loading: false,
  captionToken: 0,
  config: null,
  prompts: {},
  defaults: {},
  selectedPrompt: "style_description",
  pagesByTab: Object.fromEntries(tabs.map((tab) => [tab, { pages: [], currentIndex: -1 }])),
};

const $ = (id) => document.getElementById(id);

async function requestJson(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const text = await response.text();
  let data = {};
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    data = { detail: text || response.statusText || "请求失败" };
  }
  if (!response.ok) {
    throw new Error(data.detail || `HTTP ${response.status}`);
  }
  return data;
}

function currentTabState() {
  return state.pagesByTab[state.activeTab];
}

function currentPage() {
  const tabState = currentTabState();
  return tabState.pages[tabState.currentIndex] || null;
}

function configured() {
  return Boolean(state.config?.hasLlmApiKey && state.config?.hasOpenaiApiKey);
}

function setLoading(value) {
  state.loading = value;
  $("posterFrame").classList.toggle("is-loading", value);
  $("loadingOverlay").classList.toggle("hidden", !value);
  document.querySelectorAll("button, input, select, textarea").forEach((element) => {
    if (element.closest("#settingsModal")) return;
    if (element.id === "settingsButton" || element.id === "languageSelect") return;
    element.disabled = value;
  });
}

function showHomeError(message) {
  $("homeError").textContent = message || "";
}

function showExploreError(message) {
  $("exploreError").textContent = message || "";
}

function renderShell() {
  const inExplore = Boolean(state.query);
  $("homeView").classList.toggle("hidden", inExplore);
  $("exploreView").classList.toggle("hidden", !inExplore);
  $("backButton").classList.toggle("hidden", !inExplore);
  $("forwardButton").classList.toggle("hidden", !inExplore);
  $("resetButton").classList.toggle("hidden", !inExplore);
  $("languageSelect").value = state.lang;
  renderTabs();
  renderPage();
}

function renderTabs() {
  document.querySelectorAll("#tabs button").forEach((button) => {
    button.classList.toggle("active", button.dataset.tab === state.activeTab);
  });
}

function renderPage() {
  const page = currentPage();
  const tabState = currentTabState();
  const frame = $("posterFrame");
  const image = $("posterImage");
  frame.classList.toggle("has-image", Boolean(page));
  image.src = page ? `${page.imageUrl}?v=${page.id}` : "";
  $("backButton").disabled = state.loading || tabState.currentIndex <= 0;
  $("forwardButton").disabled = state.loading || tabState.currentIndex >= tabState.pages.length - 1;
  $("factualWarning").textContent = page?.factualWarning || "";
  renderCaption(page?.caption || "");
  renderThumbnails();
}

function renderCaption(text) {
  state.captionToken += 1;
  const token = state.captionToken;
  const caption = $("caption");
  caption.textContent = "";
  if (!text) return;
  let index = 0;
  const tick = () => {
    if (token !== state.captionToken) return;
    caption.textContent = text.slice(0, index);
    index += 1;
    if (index <= text.length) window.setTimeout(tick, 14);
  };
  tick();
}

function renderThumbnails() {
  const strip = $("thumbnailStrip");
  const tabState = currentTabState();
  strip.innerHTML = "";
  tabState.pages.forEach((page, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `thumbnail${index === tabState.currentIndex ? " active" : ""}`;
    button.innerHTML = `<img alt="第 ${index + 1} 页" src="${page.imageUrl}?v=${page.id}" />`;
    button.addEventListener("click", () => {
      if (state.loading) return;
      tabState.currentIndex = index;
      showExploreError("");
      renderPage();
    });
    strip.appendChild(button);
  });
}

async function ensureRoot(tab) {
  const tabState = state.pagesByTab[tab];
  if (tabState.pages.length) {
    renderPage();
    return;
  }
  await generatePage({ query: state.query, tab, lang: state.lang }, (page) => {
    tabState.pages = [page];
    tabState.currentIndex = 0;
  });
}

async function generatePage(payload, onPage) {
  if (!configured()) {
    openSettings("api");
    showHomeError("请先配置 LLM API Key 和 OpenAI API Key。");
    return;
  }
  setLoading(true);
  showHomeError("");
  showExploreError("");
  try {
    const { page } = await requestJson("/api/page", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    onPage(page);
    showExploreError("");
    renderShell();
  } catch (error) {
    const message = error.message || "生成失败";
    showExploreError(message);
    if (message.includes("configured")) openSettings("api");
  } finally {
    setLoading(false);
    renderPage();
  }
}

function addPageToTab(tabState, page) {
  const existingIndex = tabState.pages.findIndex((item) => item.id === page.id);
  if (existingIndex >= 0) {
    tabState.currentIndex = existingIndex;
    return;
  }
  tabState.pages.push(page);
  tabState.currentIndex = tabState.pages.length - 1;
}

async function restoreCachedPages(query, lang) {
  const params = new URLSearchParams({ query, lang });
  const { pagesByTab } = await requestJson(`/api/pages?${params.toString()}`);
  let restored = false;
  tabs.forEach((tab) => {
    const pages = pagesByTab?.[tab] || [];
    if (!pages.length) return;
    state.pagesByTab[tab] = {
      pages,
      currentIndex: 0,
    };
    restored = true;
  });
  return restored;
}

async function startExplore(query) {
  const trimmed = query.trim();
  if (!trimmed) {
    showHomeError("请输入一个物种名。");
    return;
  }
  if (!configured()) {
    showHomeError("请先配置 API Key。");
    openSettings("api");
    return;
  }
  state.query = trimmed;
  state.activeTab = "morphology";
  state.pagesByTab = Object.fromEntries(tabs.map((tab) => [tab, { pages: [], currentIndex: -1 }]));
  renderShell();
  try {
    await restoreCachedPages(trimmed, state.lang);
    renderShell();
  } catch (error) {
    showExploreError(error.message || "缓存读取失败");
  }
  await ensureRoot("morphology");
}

function switchTab(tab) {
  if (state.loading || state.activeTab === tab) return;
  state.activeTab = tab;
  renderShell();
  ensureRoot(tab);
}

function openSettings(tabName = "api") {
  $("settingsModal").classList.remove("hidden");
  switchSettingsTab(tabName);
}

function closeSettings() {
  $("settingsModal").classList.add("hidden");
}

function switchSettingsTab(tabName) {
  document.querySelectorAll("[data-settings-tab]").forEach((button) => {
    button.classList.toggle("active", button.dataset.settingsTab === tabName);
  });
  $("apiSettings").classList.toggle("hidden", tabName !== "api");
  $("promptSettings").classList.toggle("hidden", tabName !== "prompts");
}

function renderPromptList() {
  const list = $("promptList");
  list.innerHTML = "";
  Object.keys(state.prompts).forEach((key) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = key;
    button.classList.toggle("active", key === state.selectedPrompt);
    button.addEventListener("click", () => {
      persistPromptDraft();
      state.selectedPrompt = key;
      $("promptText").value = state.prompts[key] || "";
      renderPromptList();
    });
    list.appendChild(button);
  });
  $("promptText").value = state.prompts[state.selectedPrompt] || "";
}

function persistPromptDraft() {
  if (!state.selectedPrompt) return;
  state.prompts[state.selectedPrompt] = $("promptText").value;
}

async function loadInitialData() {
  const [{ config }, promptResponse] = await Promise.all([
    requestJson("/api/config"),
    requestJson("/api/prompts"),
  ]);
  state.config = config;
  state.prompts = promptResponse.prompts;
  state.defaults = promptResponse.defaults;
  hydrateConfigForm(config);
  renderPromptList();
}

function hydrateConfigForm(config) {
  $("llmProvider").value = config.llmProvider || "deepseek";
  $("llmBaseUrl").value = config.llmBaseUrl || providerDefaults[$("llmProvider").value].baseUrl;
  $("llmModel").value = config.llmModel || providerDefaults[$("llmProvider").value].model;
  $("imageBaseUrl").value = config.imageBaseUrl || imageDefaults.baseUrl;
  $("imageModel").value = config.imageModel || imageDefaults.model;
  $("imageResolution").value = config.imageResolution || imageDefaults.resolution;
  $("imageQuality").value = config.imageQuality || imageDefaults.quality;
  $("configStatus").textContent = config.hasLlmApiKey || config.hasOpenaiApiKey ? "已保存到服务端内存" : "";
}

function bindEvents() {
  $("brandButton").addEventListener("click", () => {
    if (!state.loading) {
      state.query = "";
      renderShell();
    }
  });
  $("settingsButton").addEventListener("click", () => openSettings("api"));
  $("closeSettingsButton").addEventListener("click", closeSettings);
  $("settingsModal").addEventListener("click", (event) => {
    if (event.target === $("settingsModal")) closeSettings();
  });
  document.querySelectorAll("[data-settings-tab]").forEach((button) => {
    button.addEventListener("click", () => switchSettingsTab(button.dataset.settingsTab));
  });
  $("llmProvider").addEventListener("change", () => {
    const defaults = providerDefaults[$("llmProvider").value];
    $("llmBaseUrl").value = defaults.baseUrl;
    $("llmModel").value = defaults.model;
  });
  $("apiSettings").addEventListener("submit", async (event) => {
    event.preventDefault();
    $("configStatus").textContent = "保存中…";
    const payload = {
      llmProvider: $("llmProvider").value,
      llmApiKey: $("llmApiKey").value,
      llmBaseUrl: $("llmBaseUrl").value,
      llmModel: $("llmModel").value,
      openaiApiKey: $("openaiApiKey").value,
      imageBaseUrl: $("imageBaseUrl").value,
      imageModel: $("imageModel").value,
      imageResolution: $("imageResolution").value,
      imageQuality: $("imageQuality").value,
    };
    try {
      const { config } = await requestJson("/api/config", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      state.config = config;
      $("llmApiKey").value = "";
      $("openaiApiKey").value = "";
      hydrateConfigForm(config);
      $("configStatus").textContent = "已保存";
      showHomeError("");
    } catch (error) {
      $("configStatus").textContent = error.message || "保存失败";
    }
  });
  $("searchForm").addEventListener("submit", (event) => {
    event.preventDefault();
    startExplore($("queryInput").value || $("queryInput").placeholder);
  });
  $("examples").addEventListener("click", (event) => {
    if (event.target.tagName !== "BUTTON") return;
    $("queryInput").value = event.target.textContent;
    startExplore(event.target.textContent);
  });
  $("languageSelect").addEventListener("change", () => {
    state.lang = $("languageSelect").value;
  });
  $("tabs").addEventListener("click", (event) => {
    const button = event.target.closest("button[data-tab]");
    if (button) switchTab(button.dataset.tab);
  });
  $("posterImage").addEventListener("click", async (event) => {
    const page = currentPage();
    if (!page || state.loading) return;
    const rect = event.currentTarget.getBoundingClientRect();
    const x = (event.clientX - rect.left) / rect.width;
    const y = (event.clientY - rect.top) / rect.height;
    const ripple = $("ripple");
    ripple.style.left = `${event.clientX - rect.left}px`;
    ripple.style.top = `${event.clientY - rect.top}px`;
    ripple.classList.remove("hidden");
    window.setTimeout(() => ripple.classList.add("hidden"), 720);
    const tabState = currentTabState();
    await generatePage({ parentId: page.id, parentClick: { x, y } }, (newPage) => {
      addPageToTab(tabState, newPage);
    });
  });
  $("backButton").addEventListener("click", () => {
    const tabState = currentTabState();
    if (tabState.currentIndex > 0) {
      tabState.currentIndex -= 1;
      renderPage();
    }
  });
  $("forwardButton").addEventListener("click", () => {
    const tabState = currentTabState();
    if (tabState.currentIndex < tabState.pages.length - 1) {
      tabState.currentIndex += 1;
      renderPage();
    }
  });
  $("resetButton").addEventListener("click", () => {
    if (state.loading) return;
    state.query = "";
    showExploreError("");
    renderShell();
  });
  $("restorePromptButton").addEventListener("click", () => {
    state.prompts[state.selectedPrompt] = state.defaults[state.selectedPrompt] || "";
    $("promptText").value = state.prompts[state.selectedPrompt];
    $("promptStatus").textContent = "已恢复当前模板默认值，保存后生效";
  });
  $("savePromptButton").addEventListener("click", async () => {
    persistPromptDraft();
    $("promptStatus").textContent = "保存中…";
    try {
      const response = await requestJson("/api/prompts", {
        method: "PUT",
        body: JSON.stringify({ prompts: state.prompts }),
      });
      state.prompts = response.prompts;
      state.defaults = response.defaults;
      $("promptStatus").textContent = "已保存";
      renderPromptList();
    } catch (error) {
      $("promptStatus").textContent = error.message || "保存失败";
    }
  });
}

bindEvents();
loadInitialData()
  .catch((error) => {
    showHomeError(error.message || "初始化失败");
  })
  .finally(renderShell);

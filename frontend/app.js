const chatLog = document.getElementById("chat-log");
const monitorLog = document.getElementById("monitor-log");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const sendButton = document.getElementById("send-button");
const newChatButton = document.getElementById("new-chat-button");
const providerBadge = document.getElementById("provider-badge");
const providerLabel = document.getElementById("provider-label");
const modelButton = document.getElementById("model-button");
const modelLabel = document.getElementById("model-label");
const modelPopup = document.getElementById("model-popup");
const modelSelect = document.getElementById("model-select");
const modelApplyButton = document.getElementById("model-apply-button");
const modeBadge = document.getElementById("mode-badge");
const modeLabel = document.getElementById("mode-label");
const shieldOverlay = document.getElementById("shield-overlay");
const shieldMessage = document.getElementById("shield-message");
const exfilBanner = document.getElementById("exfil-banner");

let config = null;
const pendingUserMessages = [];
let pendingAssistantIndicator = null;
let activeChatController = null;

function setChatPending(isPending) {
  activeChatController = isPending ? activeChatController : null;
  sendButton.textContent = isPending ? "Stop" : "Send";
  chatInput.disabled = isPending;
}

async function cancelChatRequest() {
  const controller = activeChatController;
  if (!controller) {
    return;
  }

  controller.abort();
  setChatPending(false);
  clearPendingAssistant();
  try {
    await fetch("/api/chat/cancel", { method: "POST" });
  } catch (error) {
    console.error("Failed to cancel chat", error);
  } finally {
    chatInput.focus();
  }
}

function closeModelPopup() {
  modelPopup.hidden = true;
  modelButton.setAttribute("aria-expanded", "false");
}

function openModelPopup() {
  modelPopup.hidden = false;
  modelButton.setAttribute("aria-expanded", "true");
}

function applyModelLabel(model) {
  modelLabel.textContent = model || "Select model";
}

function populateModelOptions(models, selectedModel) {
  modelSelect.textContent = "";
  (models || []).forEach((model) => {
    const option = document.createElement("option");
    option.value = model;
    option.textContent = model;
    option.selected = model === selectedModel;
    modelSelect.appendChild(option);
  });
  if (!modelSelect.value && selectedModel) {
    const option = document.createElement("option");
    option.value = selectedModel;
    option.textContent = selectedModel;
    option.selected = true;
    modelSelect.appendChild(option);
  }
}

async function fetchModels() {
  modelButton.disabled = true;
  modelApplyButton.disabled = true;
  try {
    const response = await fetch("/api/models");
    if (!response.ok) {
      throw new Error(`Model fetch failed with status ${response.status}`);
    }
    const payload = await response.json();
    config = {
      ...(config || {}),
      provider: payload.provider,
      model: payload.model,
      models: payload.models,
    };
    applyModelLabel(payload.model);
    populateModelOptions(payload.models, payload.model);
    return payload;
  } finally {
    modelButton.disabled = false;
    modelApplyButton.disabled = false;
  }
}

function applyMode(mode) {
  const normalizedMode = mode === "secure" ? "secure" : "insecure";
  modeBadge.dataset.mode = normalizedMode;
  modeBadge.setAttribute("aria-checked", String(normalizedMode === "secure"));
  modeLabel.textContent = normalizedMode === "secure" ? "Secure" : "Insecure";
}

function applyProvider(provider) {
  const normalizedProvider = provider === "local" ? "local" : "openai";
  providerBadge.dataset.provider = normalizedProvider;
  providerLabel.textContent = normalizedProvider === "local" ? "Local LLM" : "OpenAI";
}

const promptBuilders = {
  "safe-webpage": (appConfig) =>
    `Read ${appConfig.contentServerUrl}/pages/acme-q2-report.html and summarize it`,
  "malicious-webpage": (appConfig) =>
    `Read ${appConfig.contentServerUrl}/pages/mal-ai-trends.html and summarize it`,
};

function appendChat(role, content) {
  const div = document.createElement("div");
  div.className = `message message-${role}`;
  div.textContent = content;
  chatLog.appendChild(div);
  chatLog.scrollTop = chatLog.scrollHeight;
}

function showPendingAssistant() {
  if (pendingAssistantIndicator) {
    return;
  }

  const div = document.createElement("div");
  div.className = "message message-assistant message-pending";
  div.setAttribute("aria-live", "polite");
  div.setAttribute("aria-label", "Assistant is responding");
  div.innerHTML = '<span class="spinner" aria-hidden="true"></span><span>Waiting for reply...</span>';
  chatLog.appendChild(div);
  chatLog.scrollTop = chatLog.scrollHeight;
  pendingAssistantIndicator = div;
}

function clearPendingAssistant() {
  if (!pendingAssistantIndicator) {
    return;
  }

  pendingAssistantIndicator.remove();
  pendingAssistantIndicator = null;
}

function clearConversation() {
  chatLog.textContent = "";
  shieldOverlay.hidden = true;
  exfilBanner.hidden = true;
  clearPendingAssistant();
}

function appendMonitor(title, payload, level = "normal", blocked = false) {
  const details = document.createElement("details");
  details.className = `monitor-entry ${blocked ? "blocked" : level}`;

  const summary = document.createElement("summary");
  summary.textContent = title;
  details.appendChild(summary);

  const pre = document.createElement("pre");
  pre.textContent = JSON.stringify(payload, null, 2);
  details.appendChild(pre);

  monitorLog.prepend(details);
}

function showShield(message) {
  shieldMessage.textContent = message;
  shieldOverlay.hidden = false;
  window.setTimeout(() => {
    shieldOverlay.hidden = true;
  }, 3000);
}

function showExfilBanner() {
  exfilBanner.hidden = false;
  window.setTimeout(() => {
    exfilBanner.hidden = true;
  }, 3000);
}

async function loadConfig() {
  const response = await fetch("/api/config");
  config = await response.json();
  applyMode(config.mode);
  applyProvider(config.provider);
  applyModelLabel(config.model);
  populateModelOptions(config.models, config.model);
}

function connectWebSocket() {
  const wsProtocol = window.location.protocol === "https:" ? "wss" : "ws";
  const socket = new WebSocket(`${wsProtocol}://${window.location.host}/ws`);

  socket.onopen = () => socket.send("ready");
  socket.onmessage = (event) => {
    const envelope = JSON.parse(event.data);
    const { type, data } = envelope;

    if (type === "user_message") {
      if (pendingUserMessages[0] === data.content) {
        pendingUserMessages.shift();
        return;
      }
      appendChat("user", data.content);
      return;
    }

    if (type === "assistant_message") {
      clearPendingAssistant();
      appendChat("assistant", data.content);
      return;
    }

    if (type === "tool_call") {
      appendMonitor(`> ${data.name}()`, data, data.danger_level || "normal");
      return;
    }

    if (type === "tool_result") {
      const level = data.blocked ? "blocked" : (data.result?.exfiltrated ? "critical" : "normal");
      appendMonitor(
        data.blocked ? `[BLOCKED BY POLICY] ${data.name}` : `< ${data.name} result`,
        data,
        level,
        data.blocked,
      );

      if (data.blocked) {
        showShield(data.block_reason || "Blocked by policy");
      }

      if (!data.blocked && data.result?.exfiltrated) {
        showExfilBanner();
      }
      return;
    }

    if (type === "mode_change") {
      config = { ...(config || {}), mode: data.mode };
      applyMode(data.mode);
      appendMonitor("mode_change", data, "normal");
      return;
    }

    if (type === "provider_change") {
      config = { ...(config || {}), provider: data.provider, model: data.model };
      applyProvider(data.provider);
      applyModelLabel(data.model);
      appendMonitor("provider_change", data, "normal");
      void fetchModels().catch((error) => {
        console.error("Failed to refresh models", error);
      });
    }
  };
}

async function submitChatMessage() {
  if (activeChatController) {
    await cancelChatRequest();
    return;
  }

  const message = chatInput.value.trim();
  if (!message) {
    return;
  }

  const controller = new AbortController();
  activeChatController = controller;
  pendingUserMessages.push(message);
  appendChat("user", message);
  showPendingAssistant();
  chatInput.value = "";
  setChatPending(true);
  try {
    await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      signal: controller.signal,
      body: JSON.stringify({ message }),
    });
  } catch (error) {
    if (error.name === "AbortError") {
      return;
    }
    clearPendingAssistant();
    appendChat("assistant", "Request failed. Please try again.");
    throw error;
  } finally {
    if (activeChatController === controller) {
      setChatPending(false);
    }
    chatInput.focus();
  }
}

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  await submitChatMessage();
});

chatInput.addEventListener("keydown", (event) => {
  if (event.key !== "Enter" || event.shiftKey || event.isComposing) {
    return;
  }
  event.preventDefault();
  chatForm.requestSubmit();
});

newChatButton.addEventListener("click", async () => {
  newChatButton.disabled = true;
  try {
    if (activeChatController) {
      await cancelChatRequest();
    }
    await fetch("/api/chat/reset", { method: "POST" });
    clearConversation();
    chatInput.value = "";
    chatInput.focus();
  } finally {
    newChatButton.disabled = false;
  }
});

providerBadge.addEventListener("click", async () => {
  const previousProvider = providerBadge.dataset.provider === "local" ? "local" : "openai";
  const nextProvider = previousProvider === "local" ? "openai" : "local";
  config = { ...(config || {}), provider: nextProvider };
  applyProvider(nextProvider);
  providerBadge.disabled = true;
  try {
    const response = await fetch("/api/provider", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ provider: nextProvider }),
    });
    if (!response.ok) {
      throw new Error(`Provider update failed with status ${response.status}`);
    }
    try {
      await fetchModels();
    } catch (error) {
      console.error("Failed to load models after provider switch", error);
    }
  } catch (error) {
    config = { ...(config || {}), provider: previousProvider };
    applyProvider(previousProvider);
    console.error("Failed to update provider", error);
  } finally {
    providerBadge.disabled = false;
  }
});

modelButton.addEventListener("click", async () => {
  if (modelPopup.hidden) {
    openModelPopup();
    try {
      await fetchModels();
    } catch (error) {
      console.error("Failed to load models", error);
    }
    return;
  }
  closeModelPopup();
});

modelPopup.addEventListener("click", (event) => {
  event.stopPropagation();
});

modelButton.addEventListener("mousedown", (event) => {
  event.stopPropagation();
});

modelApplyButton.addEventListener("click", async () => {
  const nextModel = modelSelect.value;
  if (!nextModel || nextModel === config?.model) {
    closeModelPopup();
    return;
  }

  const previousModel = config?.model;
  config = { ...(config || {}), model: nextModel };
  applyModelLabel(nextModel);
  modelApplyButton.disabled = true;
  modelButton.disabled = true;
  try {
    const response = await fetch("/api/model", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ model: nextModel }),
    });
    if (!response.ok) {
      throw new Error(`Model update failed with status ${response.status}`);
    }
    const payload = await response.json();
    config = { ...(config || {}), provider: payload.provider, model: payload.model, models: payload.models };
    applyProvider(payload.provider);
    applyModelLabel(payload.model);
    populateModelOptions(payload.models, payload.model);
    closeModelPopup();
  } catch (error) {
    config = { ...(config || {}), model: previousModel };
    applyModelLabel(previousModel);
    console.error("Failed to update model", error);
  } finally {
    modelApplyButton.disabled = false;
    modelButton.disabled = false;
  }
});

document.addEventListener("click", (event) => {
  if (modelPopup.hidden) {
    return;
  }
  if (modelPopup.contains(event.target) || modelButton.contains(event.target)) {
    return;
  }
  closeModelPopup();
});

modeBadge.addEventListener("click", async () => {
  const previousMode = modeBadge.dataset.mode === "secure" ? "secure" : "insecure";
  const nextMode = modeBadge.dataset.mode === "secure" ? "insecure" : "secure";
  config = { ...(config || {}), mode: nextMode };
  applyMode(nextMode);
  modeBadge.disabled = true;
  try {
    const response = await fetch("/api/mode", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode: nextMode }),
    });
    if (!response.ok) {
      throw new Error(`Mode update failed with status ${response.status}`);
    }
  } catch (error) {
    config = { ...(config || {}), mode: previousMode };
    applyMode(previousMode);
    console.error("Failed to update mode", error);
  } finally {
    modeBadge.disabled = false;
  }
});

document.querySelectorAll("[data-prompt], [data-prompt-key]").forEach((button) => {
  button.addEventListener("click", () => {
    const promptKey = button.dataset.promptKey;
    if (promptKey && !config) {
      return;
    }
    chatInput.value = promptKey ? promptBuilders[promptKey](config) : button.dataset.prompt;
    void submitChatMessage();
  });
});

loadConfig().then(connectWebSocket);

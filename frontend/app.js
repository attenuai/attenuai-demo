const chatLog = document.getElementById("chat-log");
const monitorLog = document.getElementById("monitor-log");
const appShell = document.querySelector(".app-shell");
const paneResizer = document.getElementById("pane-resizer");
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
const capabilityButton = document.getElementById("capability-button");
const capabilityLabel = document.getElementById("capability-label");
const capabilityPopup = document.getElementById("capability-popup");
const capabilityList = document.getElementById("capability-list");
const capabilityInsecureButton = document.getElementById("capability-insecure-button");
const capabilityCloseButton = document.getElementById("capability-close-button");
const shieldOverlay = document.getElementById("shield-overlay");
const shieldMessage = document.getElementById("shield-message");
const exfilBanner = document.getElementById("exfil-banner");
const BLOCKED_MESSAGE = "The system has detected unapproved behavior. If you were processing unknown data, be aware that there may be malicious content in that data. All further actions have been stopped.";
const STACKED_LAYOUT_BREAKPOINT = 760;

let config = null;
const pendingUserMessages = [];
let pendingAssistantIndicator = null;
let activeChatController = null;
let draftCapabilities = [];
let capabilitiesDirty = false;
let chatLocked = false;
let isResizingPanes = false;

function setPaneWidth(leftPercent) {
  if (!appShell) {
    return;
  }
  const clamped = Math.min(75, Math.max(25, leftPercent));
  appShell.style.setProperty("--pane-left", `${clamped}%`);
}

function updatePaneWidthFromPointer(clientX) {
  if (!appShell || window.innerWidth <= STACKED_LAYOUT_BREAKPOINT) {
    return;
  }
  const bounds = appShell.getBoundingClientRect();
  const leftPercent = ((clientX - bounds.left) / bounds.width) * 100;
  setPaneWidth(leftPercent);
}

function stopPaneResize() {
  if (!appShell || !isResizingPanes) {
    return;
  }
  isResizingPanes = false;
  appShell.classList.remove("is-resizing");
}

function applyChatLockState() {
  chatInput.disabled = Boolean(activeChatController) || chatLocked;
  if (chatLocked) {
    sendButton.disabled = false;
    sendButton.textContent = "New Chat";
    chatInput.placeholder = "Start a new chat to continue.";
    return;
  }
  sendButton.disabled = false;
  sendButton.textContent = activeChatController ? "Stop" : "Send";
  chatInput.placeholder = "";
}

function setChatPending(isPending) {
  activeChatController = isPending ? activeChatController : null;
  applyChatLockState();
}

function lockChat() {
  chatLocked = true;
  clearPendingAssistant();
  applyChatLockState();
}

function unlockChat() {
  chatLocked = false;
  applyChatLockState();
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
  if (!capabilityLabel) {
    return;
  }
  const normalizedMode = mode === "insecure" ? "insecure" : "secure";
  capabilityButton.dataset.mode = normalizedMode;
  capabilityInsecureButton.dataset.mode = normalizedMode;
  capabilityButton.setAttribute("aria-pressed", String(normalizedMode === "insecure"));
  capabilityInsecureButton.setAttribute("aria-pressed", String(normalizedMode === "insecure"));
  capabilityLabel.textContent = normalizedMode === "insecure" ? "Insecure" : "Capabilities";
}

function applyProvider(provider) {
  const normalizedProvider = provider === "local" ? "local" : "openai";
  providerBadge.dataset.provider = normalizedProvider;
  providerLabel.textContent = normalizedProvider === "local" ? "Local LLM" : "OpenAI";
}

function cloneCapabilities(capabilities = []) {
  return capabilities.map((capability) => ({
    ...capability,
    ...(Array.isArray(capability.values) ? { values: [...capability.values] } : {}),
  }));
}

function applyCapabilityButtonState(capabilities = []) {
  const enabledCount = capabilities.filter((capability) => capability.checked).length;
  capabilityButton.dataset.count = String(enabledCount);
  capabilityButton.title = (config?.mode || "secure") === "insecure"
    ? "Running without protection"
    : `${enabledCount} capabilities enabled`;
}

function renderCapabilityOptions(capabilities = []) {
  const isInsecure = (config?.mode || "secure") === "insecure";
  capabilityList.textContent = "";
  capabilityList.dataset.disabled = String(isInsecure);
  capabilities.forEach((capability) => {
    const label = document.createElement("label");
    label.className = `capability-item${isInsecure ? " is-disabled" : ""}`;

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.value = capability.id;
    checkbox.checked = Boolean(capability.checked);
    checkbox.disabled = isInsecure;
    checkbox.addEventListener("change", () => {
      capability.checked = checkbox.checked;
      capabilitiesDirty = true;
      applyCapabilityButtonState(draftCapabilities);
    });

    const copy = document.createElement("div");
    const title = document.createElement("strong");
    title.textContent = capability.label;
    const description = document.createElement("span");
    description.textContent = capability.description;
    copy.append(title, description);

    if (typeof capability.value === "string") {
      const input = document.createElement("input");
      input.type = "text";
      input.value = capability.value;
      input.className = "capability-value-input";
      input.placeholder = "Pattern";
      input.disabled = isInsecure;
      input.addEventListener("input", () => {
        capability.value = input.value;
        capabilitiesDirty = true;
      });
      copy.appendChild(input);
    }

    if (Array.isArray(capability.values)) {
      const valuesWrapper = document.createElement("div");
      valuesWrapper.className = "capability-values";

      capability.values.forEach((subpath, index) => {
        const row = document.createElement("div");
        row.className = "capability-value-row";

        const input = document.createElement("input");
        input.type = "text";
        input.value = subpath;
        input.className = "capability-value-input";
        input.placeholder = "/app/safe";
        input.disabled = isInsecure;
        input.addEventListener("input", () => {
          capability.values[index] = input.value;
          capabilitiesDirty = true;
        });

        const removeButton = document.createElement("button");
        removeButton.type = "button";
        removeButton.className = "capability-value-action button-secondary";
        removeButton.textContent = "-";
        removeButton.disabled = isInsecure || capability.values.length <= 1;
        removeButton.setAttribute("aria-label", "Remove subpath");
        removeButton.addEventListener("click", () => {
          capability.values.splice(index, 1);
          capabilitiesDirty = true;
          renderCapabilityOptions(draftCapabilities);
        });

        row.append(input, removeButton);
        valuesWrapper.appendChild(row);
      });

      const addButton = document.createElement("button");
      addButton.type = "button";
      addButton.className = "capability-add-button button-secondary";
      addButton.textContent = "+";
      addButton.disabled = isInsecure;
      addButton.setAttribute("aria-label", "Add subpath");
      addButton.addEventListener("click", () => {
        capability.values.push("");
        capabilitiesDirty = true;
        renderCapabilityOptions(draftCapabilities);
      });

      copy.append(valuesWrapper, addButton);
    }

    label.append(checkbox, copy);
    capabilityList.appendChild(label);
  });
}

function closeCapabilityPopup() {
  capabilityPopup.hidden = true;
  capabilityButton.setAttribute("aria-expanded", "false");
}

function openCapabilityPopup() {
  draftCapabilities = cloneCapabilities(config?.capabilities || []);
  capabilitiesDirty = false;
  renderCapabilityOptions(draftCapabilities);
  capabilityPopup.hidden = false;
  capabilityButton.setAttribute("aria-expanded", "true");
}

async function commitCapabilities() {
  if ((config?.mode || "secure") === "insecure") {
    closeCapabilityPopup();
    return;
  }

  if (!capabilitiesDirty) {
    closeCapabilityPopup();
    return;
  }

  const previousCapabilities = cloneCapabilities(config?.capabilities || []);
  const nextCapabilities = cloneCapabilities(draftCapabilities);
  config = { ...(config || {}), capabilities: nextCapabilities, mode: "secure" };
  applyCapabilityButtonState(nextCapabilities);
  capabilityButton.disabled = true;
  capabilityInsecureButton.disabled = true;
  capabilityCloseButton.disabled = true;
  try {
    const response = await fetch("/api/capabilities", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        capabilities: nextCapabilities.map((capability) => ({
          id: capability.id,
          checked: Boolean(capability.checked),
          ...(typeof capability.value === "string" ? { value: capability.value } : {}),
          ...(Array.isArray(capability.values) ? { values: capability.values } : {}),
        })),
      }),
    });
    if (!response.ok) {
      throw new Error(`Capability update failed with status ${response.status}`);
    }
    const payload = await response.json();
    config = { ...(config || {}), capabilities: cloneCapabilities(payload.capabilities), mode: "secure" };
    applyMode("secure");
    applyCapabilityButtonState(config.capabilities);
    closeCapabilityPopup();
  } catch (error) {
    config = { ...(config || {}), capabilities: previousCapabilities };
    draftCapabilities = cloneCapabilities(previousCapabilities);
    applyCapabilityButtonState(previousCapabilities);
    renderCapabilityOptions(draftCapabilities);
    console.error("Failed to update capabilities", error);
  } finally {
    capabilityButton.disabled = false;
    capabilityInsecureButton.disabled = false;
    capabilityCloseButton.disabled = false;
  }
}

async function toggleInsecureMode() {
  const previousMode = config?.mode === "insecure" ? "insecure" : "secure";
  const nextMode = previousMode === "insecure" ? "secure" : "insecure";
  const renderedCapabilities = draftCapabilities.length
    ? draftCapabilities
    : cloneCapabilities(config?.capabilities || []);

  config = { ...(config || {}), mode: nextMode };
  applyMode(nextMode);
  applyCapabilityButtonState(config?.capabilities || []);
  renderCapabilityOptions(renderedCapabilities);
  capabilityButton.disabled = true;
  capabilityInsecureButton.disabled = true;
  capabilityCloseButton.disabled = true;
  try {
    const response = await fetch("/api/mode", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode: nextMode }),
    });
    if (!response.ok) {
      throw new Error(`Mode update failed with status ${response.status}`);
    }
    const payload = await response.json();
    config = { ...(config || {}), mode: payload.mode };
    applyMode(payload.mode);
    applyCapabilityButtonState(config?.capabilities || []);
    renderCapabilityOptions(renderedCapabilities);
  } catch (error) {
    config = { ...(config || {}), mode: previousMode };
    applyMode(previousMode);
    applyCapabilityButtonState(config?.capabilities || []);
    renderCapabilityOptions(renderedCapabilities);
    console.error("Failed to update mode", error);
  } finally {
    capabilityButton.disabled = false;
    capabilityInsecureButton.disabled = false;
    capabilityCloseButton.disabled = false;
  }
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
  unlockChat();
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
  config.capabilities = cloneCapabilities(config.capabilities || []);
  applyCapabilityButtonState(config.capabilities);
  draftCapabilities = cloneCapabilities(config.capabilities);
}

function connectWebSocket() {
  const wsProtocol = window.location.protocol === "https:" ? "wss" : "ws";
  const socket = new WebSocket(`${wsProtocol}://${window.location.host}/ws`);

  socket.onopen = () => socket.send("ready");
  socket.onmessage = (event) => {
    const envelope = JSON.parse(event.data);
    const { type, data } = envelope;

    if (type === "user_message") {
      appendMonitor("user_message", data, "normal");
      if (pendingUserMessages[0] === data.content) {
        pendingUserMessages.shift();
        return;
      }
      appendChat("user", data.content);
      return;
    }

    if (type === "assistant_message") {
      clearPendingAssistant();
      appendMonitor("assistant_message", data, "normal");
      appendChat("assistant", data.content);
      if (data.content === BLOCKED_MESSAGE) {
        lockChat();
      }
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
      applyCapabilityButtonState(config.capabilities || []);
      if (!capabilityPopup.hidden) {
        renderCapabilityOptions(draftCapabilities);
      }
      appendMonitor("mode_change", data, "normal");
      return;
    }

    if (type === "capability_change") {
      config = { ...(config || {}), capabilities: cloneCapabilities(data.capabilities || []) };
      applyMode(config.mode);
      applyCapabilityButtonState(config.capabilities);
      draftCapabilities = cloneCapabilities(config.capabilities);
      if (!capabilityPopup.hidden) {
        renderCapabilityOptions(draftCapabilities);
      }
      appendMonitor("capability_change", data, "normal");
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

  if (chatLocked) {
    await resetChat();
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
    if (!chatLocked) {
      chatInput.focus();
    }
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

async function resetChat() {
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
}

newChatButton.addEventListener("click", async () => {
  await resetChat();
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

capabilityButton.addEventListener("click", () => {
  if (capabilityPopup.hidden) {
    openCapabilityPopup();
    return;
  }
  void commitCapabilities();
});

capabilityCloseButton.addEventListener("click", async () => {
  await commitCapabilities();
});

capabilityInsecureButton.addEventListener("click", async () => {
  await toggleInsecureMode();
});

capabilityPopup.addEventListener("click", (event) => {
  event.stopPropagation();
});

capabilityButton.addEventListener("mousedown", (event) => {
  event.stopPropagation();
});

document.addEventListener("click", (event) => {
  if (!modelPopup.hidden) {
    if (modelPopup.contains(event.target) || modelButton.contains(event.target)) {
      return;
    }
    closeModelPopup();
    return;
  }

  if (!capabilityPopup.hidden) {
    if (capabilityPopup.contains(event.target) || capabilityButton.contains(event.target)) {
      return;
    }
    void commitCapabilities();
  }
});

document.addEventListener("keydown", (event) => {
  if (event.key !== "Escape") {
    return;
  }
  if (!modelPopup.hidden) {
    closeModelPopup();
    return;
  }
  if (!capabilityPopup.hidden) {
    void commitCapabilities();
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

window.addEventListener("pointermove", (event) => {
  if (!isResizingPanes) {
    return;
  }
  updatePaneWidthFromPointer(event.clientX);
});

window.addEventListener("pointerup", () => {
  stopPaneResize();
});

window.addEventListener("pointercancel", () => {
  stopPaneResize();
});

window.addEventListener("resize", () => {
  if (window.innerWidth <= STACKED_LAYOUT_BREAKPOINT) {
    stopPaneResize();
  }
});

if (paneResizer) {
  paneResizer.addEventListener("pointerdown", (event) => {
    if (!appShell || window.innerWidth <= STACKED_LAYOUT_BREAKPOINT) {
      return;
    }
    isResizingPanes = true;
    appShell.classList.add("is-resizing");
    paneResizer.setPointerCapture(event.pointerId);
    updatePaneWidthFromPointer(event.clientX);
  });
}

loadConfig().then(connectWebSocket);

const chatLog = document.getElementById("chat-log");
const monitorLog = document.getElementById("monitor-log");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const sendButton = document.getElementById("send-button");
const modeBadge = document.getElementById("mode-badge");
const engineBadge = document.getElementById("engine-badge");
const shieldOverlay = document.getElementById("shield-overlay");
const shieldMessage = document.getElementById("shield-message");
const exfilBanner = document.getElementById("exfil-banner");
const exfilLink = document.getElementById("exfil-link");

let config = null;

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
  modeBadge.textContent = config.mode === "secure" ? "Secure Mode" : "Insecure Mode";
  modeBadge.classList.toggle("badge-muted", config.mode !== "secure");
  engineBadge.textContent = `${config.engine} · act ${config.currentAct}`;
  exfilLink.href = config.exfilServerUrl;
}

function connectWebSocket() {
  const wsProtocol = window.location.protocol === "https:" ? "wss" : "ws";
  const socket = new WebSocket(`${wsProtocol}://${window.location.host}/ws`);

  socket.onopen = () => socket.send("ready");
  socket.onmessage = (event) => {
    const envelope = JSON.parse(event.data);
    const { type, data } = envelope;

    if (type === "user_message") {
      appendChat("user", data.content);
      return;
    }

    if (type === "assistant_message") {
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
      appendMonitor("mode_change", data, "normal");
    }
  };
}

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = chatInput.value.trim();
  if (!message) {
    return;
  }

  sendButton.disabled = true;
  try {
    await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
    chatInput.value = "";
  } finally {
    sendButton.disabled = false;
    chatInput.focus();
  }
});

document.querySelectorAll("[data-prompt], [data-prompt-key]").forEach((button) => {
  button.addEventListener("click", () => {
    const promptKey = button.dataset.promptKey;
    if (promptKey && !config) {
      return;
    }
    chatInput.value = promptKey ? promptBuilders[promptKey](config) : button.dataset.prompt;
    chatForm.requestSubmit();
  });
});

loadConfig().then(connectWebSocket);

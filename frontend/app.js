const els = {
  providerBadge: document.getElementById("provider-badge"),
  testCases: document.getElementById("test-cases"),
  log: document.getElementById("log"),
  form: document.getElementById("query-form"),
  query: document.getElementById("query"),
  sendBtn: document.getElementById("send-btn"),
  sendLabel: document.querySelector(".send-label"),
  spinner: document.querySelector(".spinner"),
  clearBtn: document.getElementById("clear-btn"),
};

let running = false;
let currentEventSource = null;

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function setRunning(state) {
  running = state;
  els.query.disabled = state;
  els.sendBtn.disabled = state;
  els.spinner.hidden = !state;
  els.sendLabel.textContent = state ? "Running" : "Send";
}

function appendEvent(cls, text) {
  const div = document.createElement("div");
  div.className = `evt ${cls}`;
  div.textContent = text;
  els.log.appendChild(div);
  els.log.scrollTop = els.log.scrollHeight;
}

function renderEvent(ev) {
  switch (ev.type) {
    case "query":
      appendEvent("evt-query", `💬 ${ev.text}`);
      break;
    case "step":
      appendEvent("evt-step", `--- 🔄 Vòng lặp ReAct (Step ${ev.step}/${ev.max}) ---`);
      break;
    case "llm_response":
      appendEvent("evt-llm", ev.text);
      break;
    case "action":
      appendEvent("evt-action", `🛠️ Action -> ${ev.tool}(${ev.args})`);
      break;
    case "observation":
      appendEvent("evt-observation", `👁️ Observation: ${ev.text}`);
      break;
    case "final_answer":
      appendEvent("evt-final", `🏁 Final Answer: ${ev.text}`);
      break;
    case "guardrail":
      appendEvent("evt-guardrail", `🛡️ GUARDRAIL TRIGGERED: ${ev.message}`);
      break;
    case "error":
      appendEvent("evt-error", `❌ Error: ${ev.message}`);
      break;
    default:
      appendEvent("", JSON.stringify(ev));
  }
}

function runAgent(query) {
  if (running || !query.trim()) return;
  els.log.innerHTML = "";
  setRunning(true);

  const url = "/api/agent/stream?query=" + encodeURIComponent(query);
  const es = new EventSource(url);
  currentEventSource = es;

  const finish = () => {
    es.close();
    currentEventSource = null;
    setRunning(false);
  };

  es.onmessage = (msg) => {
    let ev;
    try {
      ev = JSON.parse(msg.data);
    } catch {
      appendEvent("evt-error", "❌ Error: phản hồi không hợp lệ.");
      return;
    }
    renderEvent(ev);
    if (ev.type === "final_answer" || ev.type === "guardrail" || ev.type === "error") {
      finish();
    }
  };

  es.onerror = () => {
    if (running) {
      appendEvent("evt-error", "❌ Mất kết nối với server.");
    }
    finish();
  };
}

function truncate(text, n) {
  const t = String(text).trim();
  return t.length > n ? t.slice(0, n).trimEnd() + "…" : t;
}

function renderTestCases(cases) {
  els.testCases.innerHTML = "";
  if (!cases.length) {
    els.testCases.innerHTML = '<div class="muted">Không có test case.</div>';
    return;
  }
  for (const c of cases) {
    const card = document.createElement("div");
    card.className = "test-card";
    card.dataset.id = c.id;
    card.innerHTML = `
      <div class="tc-top">
        <span class="tc-id">#${c.id}</span>
        <span class="tc-cat">${escapeHtml(c.category)}</span>
      </div>
      <div class="tc-q">${escapeHtml(truncate(c.question, 120))}</div>
    `;
    card.addEventListener("click", () => {
      if (running) return;
      els.testCases.querySelectorAll(".test-card").forEach((el) => el.classList.remove("selected"));
      card.classList.add("selected");
      els.query.value = c.question;
      els.query.focus();
    });
    els.testCases.appendChild(card);
  }
}

async function loadTestCases() {
  try {
    const res = await fetch("/api/test_cases");
    renderTestCases(await res.json());
  } catch {
    els.testCases.innerHTML = '<div class="muted">Lỗi tải test cases.</div>';
  }
}

async function loadProvider() {
  try {
    const res = await fetch("/api/provider");
    const info = await res.json();
    els.providerBadge.textContent = `${info.provider} · ${info.model}`;
  } catch {
    els.providerBadge.textContent = "—";
  }
}

els.form.addEventListener("submit", (e) => {
  e.preventDefault();
  runAgent(els.query.value);
});

els.clearBtn.addEventListener("click", () => {
  if (running) return;
  els.log.innerHTML = "";
});

loadProvider();
loadTestCases();

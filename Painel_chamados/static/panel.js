async function fetchHistory() {
  const response = await fetch("/api/history");
  return response.json();
}

let lastHistorySignature = "";
let lastCurrentId = null;
let soundEnabled = false;
let audioContext = null;

function playChime() {
  if (!soundEnabled) {
    return;
  }

  if (!audioContext) {
    audioContext = new (window.AudioContext || window.webkitAudioContext)();
  }

  const oscillator = audioContext.createOscillator();
  const gainNode = audioContext.createGain();

  oscillator.type = "sine";
  oscillator.frequency.value = 880;
  gainNode.gain.value = 0.0001;

  oscillator.connect(gainNode);
  gainNode.connect(audioContext.destination);

  const now = audioContext.currentTime;
  gainNode.gain.exponentialRampToValueAtTime(0.3, now + 0.03);
  gainNode.gain.exponentialRampToValueAtTime(0.0001, now + 1.2);

  oscillator.start(now);
  oscillator.stop(now + 1.25);
}

function renderPanel(history) {
  const current = history[0] || null;
  const currentName = document.getElementById("current-name");
  const currentReg = document.getElementById("current-reg");
  const currentDest = document.getElementById("current-dest");
  const historyList = document.getElementById("history-list");

  const setValueWithPriority = (element, value, priority) => {
    element.textContent = value;
    if (priority) {
      const badge = document.createElement("span");
      badge.className = "priority-badge";
      badge.textContent = "Prioridade";
      element.appendChild(badge);
    }
  };

  if (current) {
    setValueWithPriority(currentName, current.name, current.priority);
    currentReg.textContent = current.registration;
    currentDest.textContent = current.destination || "Aguardando";
  }
   else {
    currentName.textContent = "-";
    currentReg.textContent = "-";
    currentDest.textContent = "Aguardando";
  }

  historyList.innerHTML = "";
  history.slice(1).forEach((item) => {
    const row = document.createElement("div");
    row.className = "history-item";
    row.innerHTML = `
      <div>
        <strong>${item.name}</strong>
        <div class="meta">Registro ${item.registration}</div>
      </div>
      <div>${item.destination || ""}</div>
    `;

    if (item.priority) {
      const meta = row.querySelector(".meta");
      const badge = document.createElement("span");
      badge.className = "priority-badge";
      badge.textContent = "Prioridade";
      meta.appendChild(badge);
    }
    historyList.appendChild(row);
  });
}

async function refreshPanel() {
  const history = await fetchHistory();
  const signature = JSON.stringify(history);
  if (signature === lastHistorySignature) {
    return;
  }
  lastHistorySignature = signature;
  const currentId = history[0] ? history[0].id : null;
  if (currentId && lastCurrentId && currentId !== lastCurrentId) {
    playChime();
  }
  lastCurrentId = currentId;
  renderPanel(history);
}

document.addEventListener("DOMContentLoaded", () => {
  const soundToggle = document.getElementById("sound-toggle");
  if (soundToggle) {
    soundToggle.addEventListener("click", async () => {
      soundEnabled = !soundEnabled;
      soundToggle.textContent = soundEnabled ? "Som: Ligado" : "Som: Desligado";
      if (soundEnabled && audioContext && audioContext.state === "suspended") {
        await audioContext.resume();
      }
    });
  }
  refreshPanel();
  connectSocket(refreshPanel);
  setInterval(refreshPanel, 5000);
});

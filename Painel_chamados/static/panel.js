async function fetchHistory() {
  const response = await fetch("/api/history");
  return response.json();
}

let lastHistorySignature = "";

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
  renderPanel(history);
}

document.addEventListener("DOMContentLoaded", () => {
  refreshPanel();
  connectSocket(refreshPanel);
  setInterval(refreshPanel, 5000);
});

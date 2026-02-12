async function fetchHistory() {
  const response = await fetch("/api/history");
  return response.json();
}

function renderPanel(history) {
  const current = history[0] || null;
  const currentName = document.getElementById("current-name");
  const currentReg = document.getElementById("current-reg");
  const currentDest = document.getElementById("current-dest");
  const historyList = document.getElementById("history-list");

  if (current) {
    currentName.textContent = current.name;
    currentReg.textContent = current.registration;
    currentDest.textContent = current.destination || "Aguardando";
  } else {
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
    historyList.appendChild(row);
  });
}

async function refreshPanel() {
  const history = await fetchHistory();
  renderPanel(history);
}

document.addEventListener("DOMContentLoaded", () => {
  refreshPanel();
  connectSocket(refreshPanel);
});

const fallbackDestinations = [
  "Recursos Humanos",
  "Auditório",
  "Retornar para recepção",
  "Sala de negociação",
];

let destinations = [...fallbackDestinations];

async function fetchQueue() {
  const response = await fetch("/api/queue");
  return response.json();
}

let lastQueueSignature = "";

async function fetchDestinations() {
  try {
    const response = await fetch("/api/destinations");
    if (!response.ok) {
      return;
    }
    const data = await response.json();
    if (Array.isArray(data) && data.length > 0) {
      destinations = data;
    }
  } catch (_) {
    destinations = [...fallbackDestinations];
  }
}

function createSelect() {
  const select = document.createElement("select");
  destinations.forEach((dest) => {
    const option = document.createElement("option");
    option.value = dest;
    option.textContent = dest;
    select.appendChild(option);
  });
  return select;
}

function renderQueue(queue) {
  const list = document.getElementById("queue-list");
  list.innerHTML = "";

  queue.forEach((item) => {
    const row = document.createElement("div");
    row.className = "row";

    const select = createSelect();
    const action = document.createElement("button");
    action.textContent = "Chamar";

    action.addEventListener("click", async () => {
      await fetch(`/api/dispatch/${item.id}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ destination: select.value }),
      });
      refreshQueue();
    });

    row.innerHTML = `
      <div>
        <strong>${item.name}</strong>
        <div class="meta">Registro ${item.registration}</div>
      </div>
      <div class="meta">Aguardando</div>
    `;

    if (item.priority) {
      const meta = row.querySelector(".meta");
      const badge = document.createElement("span");
      badge.className = "priority-badge";
      badge.textContent = "Prioridade";
      meta.appendChild(badge);
    }

    const actionWrap = document.createElement("div");
    actionWrap.appendChild(select);
    actionWrap.appendChild(action);
    actionWrap.style.display = "grid";
    actionWrap.style.gap = "8px";

    row.appendChild(actionWrap);
    list.appendChild(row);
  });
}

async function refreshQueue() {
  const queue = await fetchQueue();
  const signature = JSON.stringify(queue);
  if (signature === lastQueueSignature) {
    return;
  }
  lastQueueSignature = signature;
  renderQueue(queue);
}

document.addEventListener("DOMContentLoaded", () => {
  fetchDestinations().then(refreshQueue);
  connectSocket(refreshQueue);
  setInterval(refreshQueue, 5000);
});

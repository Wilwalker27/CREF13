const destinations = [
  "Sala 1",
  "Sala 2",
  "Voltar para recepcao",
  "Sala de negociacao",
];

async function fetchQueue() {
  const response = await fetch("/api/queue");
  return response.json();
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
    });

    row.innerHTML = `
      <div>
        <strong>${item.name}</strong>
        <div class="meta">Registro ${item.registration}</div>
      </div>
      <div class="meta">Aguardando</div>
    `;

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
  renderQueue(queue);
}

document.addEventListener("DOMContentLoaded", () => {
  refreshQueue();
  connectSocket(refreshQueue);
});

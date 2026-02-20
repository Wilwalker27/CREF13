let editingId = null;

async function fetchQueue() {
  const response = await fetch("/api/queue");
  return response.json();
}

let lastQueueSignature = "";

function resetForm() {
  editingId = null;
  document.getElementById("name").value = "";
  document.getElementById("registration").value = "";
  document.getElementById("priority").checked = false;
  document.getElementById("submit-btn").textContent = "Cadastrar";
}

function renderQueue(queue) {
  const list = document.getElementById("queue-list");
  list.innerHTML = "";

  queue.forEach((item) => {
    const row = document.createElement("div");
    row.className = "row";
    row.innerHTML = `
      <div>
        <strong>${item.name}</strong>
        <div class="meta">Registro ${item.registration}</div>
      </div>
      <div class="meta">Aguardando</div>
      <div class="queue-actions">
        <button data-action="edit" data-id="${item.id}">Editar</button>
        <button data-action="delete" data-id="${item.id}" class="button-danger">Apagar</button>
      </div>
    `;

    if (item.priority) {
      const meta = row.querySelector(".meta");
      const badge = document.createElement("span");
      badge.className = "priority-badge";
      badge.textContent = "Prioridade";
      meta.appendChild(badge);
    }

    row.querySelector('[data-action="edit"]').addEventListener("click", () => {
      editingId = item.id;
      document.getElementById("name").value = item.name;
      document.getElementById("registration").value = item.registration;
      document.getElementById("priority").checked = Boolean(item.priority);
      document.getElementById("submit-btn").textContent = "Salvar";
    });

    row.querySelector('[data-action="delete"]').addEventListener("click", async () => {
      await fetch(`/api/queue/${item.id}`, {
        method: "DELETE",
      });
      if (editingId === item.id) {
        resetForm();
      }
      refreshQueue();
    });

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

async function submitForm(event) {
  event.preventDefault();
  const name = document.getElementById("name").value.trim();
  const registration = document.getElementById("registration").value.trim();
  const priority = document.getElementById("priority").checked;

  if (!name || !registration) {
    return;
  }

  if (editingId) {
    await fetch(`/api/edit/${editingId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, registration, priority }),
    });
  } else {
    await fetch("/api/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, registration, priority }),
    });
  }

  resetForm();
  refreshQueue();
}

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("reception-form").addEventListener("submit", submitForm);
  document.getElementById("cancel-btn").addEventListener("click", resetForm);
  refreshQueue();
  connectSocket(refreshQueue);
  setInterval(refreshQueue, 5000);
});

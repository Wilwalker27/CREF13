let editingId = null;

async function fetchQueue() {
  const response = await fetch("/api/queue");
  return response.json();
}

function resetForm() {
  editingId = null;
  document.getElementById("name").value = "";
  document.getElementById("registration").value = "";
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
      <div>
        <button data-id="${item.id}">Editar</button>
      </div>
    `;

    row.querySelector("button").addEventListener("click", () => {
      editingId = item.id;
      document.getElementById("name").value = item.name;
      document.getElementById("registration").value = item.registration;
      document.getElementById("submit-btn").textContent = "Salvar";
    });

    list.appendChild(row);
  });
}

async function refreshQueue() {
  const queue = await fetchQueue();
  renderQueue(queue);
}

async function submitForm(event) {
  event.preventDefault();
  const name = document.getElementById("name").value.trim();
  const registration = document.getElementById("registration").value.trim();

  if (!name || !registration) {
    return;
  }

  if (editingId) {
    await fetch(`/api/edit/${editingId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, registration }),
    });
  } else {
    await fetch("/api/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, registration }),
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
});

const ticketsEl = document.querySelector("#tickets");
const filterEl = document.querySelector("#status-filter");
const openCountEl = document.querySelector("#open-count");
const totalCountEl = document.querySelector("#total-count");

function formatStatus(status) {
  return status.replace("_", " ");
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[character]);
}

function ticketCard(rawTicket) {
  const ticket = Object.fromEntries(
    Object.entries(rawTicket).map(([key, value]) => [key, escapeHtml(value)])
  );
  const article = document.createElement("article");
  article.className = "ticket-card";
  article.innerHTML = `
    <header>
      <div>
        <p class="eyebrow">${ticket.assigned_team}</p>
        <h3>Ticket #${ticket.id}</h3>
      </div>
      <span class="badge ${ticket.priority}">${ticket.priority}</span>
    </header>
    <p>${ticket.customer_message}</p>
    <dl class="meta-list">
      <div><dt>Status</dt><dd><span class="badge ${ticket.status}">${formatStatus(ticket.status)}</span></dd></div>
      <div><dt>Reason</dt><dd>${ticket.reason}</dd></div>
    </dl>
    <form class="ticket-actions" data-ticket-id="${ticket.id}">
      <select name="status">
        <option value="open" ${ticket.status === "open" ? "selected" : ""}>Open</option>
        <option value="in_progress" ${ticket.status === "in_progress" ? "selected" : ""}>In progress</option>
        <option value="resolved" ${ticket.status === "resolved" ? "selected" : ""}>Resolved</option>
        <option value="closed" ${ticket.status === "closed" ? "selected" : ""}>Closed</option>
      </select>
      <input name="assigned_team" value="${ticket.assigned_team}" />
      <button type="submit">Save</button>
    </form>
  `;
  return article;
}

async function loadTickets() {
  const params = new URLSearchParams();
  if (filterEl.value) params.set("status", filterEl.value);

  const response = await fetch(`/admin/tickets?${params}`);
  const payload = await response.json();
  const tickets = payload.tickets;

  ticketsEl.innerHTML = "";
  openCountEl.textContent = tickets.filter((ticket) => ticket.status === "open").length;
  totalCountEl.textContent = tickets.length;

  if (tickets.length === 0) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = "No tickets match this filter.";
    ticketsEl.append(empty);
    return;
  }

  tickets.forEach((ticket) => ticketsEl.append(ticketCard(ticket)));
}

ticketsEl.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.target;
  const ticketId = form.dataset.ticketId;
  const data = new FormData(form);

  await fetch(`/admin/tickets/${ticketId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      status: data.get("status"),
      assigned_team: data.get("assigned_team"),
    }),
  });

  await loadTickets();
});

filterEl.addEventListener("change", loadTickets);
loadTickets();

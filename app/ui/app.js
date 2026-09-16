const form = document.querySelector("#chat-form");
const input = document.querySelector("#message");
const conversation = document.querySelector("#conversation");
const statusEl = document.querySelector("#status");
const confidenceEl = document.querySelector("#confidence");
const escalationEl = document.querySelector("#escalation");
const ticketEl = document.querySelector("#ticket");
const citationsEl = document.querySelector("#citations");
const feedbackEl = document.querySelector("#feedback");

let conversationId = null;
let conversationToken = null;
let lastMessageId = null;

function addMessage(role, text) {
  const article = document.createElement("article");
  article.className = `message ${role}`;

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = role === "user" ? "YOU" : "AI";

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  const paragraph = document.createElement("p");
  paragraph.textContent = text;
  bubble.append(paragraph);

  article.append(avatar, bubble);
  conversation.append(article);
  conversation.scrollTop = conversation.scrollHeight;
}

function setStatus(text) {
  statusEl.textContent = text;
  statusEl.className = "status-pill";
  if (text === "Thinking") statusEl.classList.add("thinking");
  if (text === "Error") statusEl.classList.add("error");
  if (text === "Feedback saved") statusEl.classList.add("saved");
}

function renderMetadata(payload) {
  confidenceEl.textContent = payload.confidence;
  escalationEl.textContent = payload.needs_escalation ? payload.escalation_reason : "No";
  ticketEl.textContent = payload.ticket_id ? `#${payload.ticket_id}` : "-";
  citationsEl.innerHTML = "";

  if (payload.citations.length === 0) {
    const item = document.createElement("li");
    item.textContent = "No citations returned";
    citationsEl.append(item);
  } else {
    payload.citations.forEach((citation) => {
      const item = document.createElement("li");
      item.textContent = citation;
      citationsEl.append(item);
    });
  }

  feedbackEl.hidden = false;
}

async function sendFeedback(rating) {
  if (!conversationId || !lastMessageId) return;

  const response = await fetch("/feedback", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      conversation_id: conversationId,
      conversation_token: conversationToken,
      message_id: lastMessageId,
      rating,
      comment: rating === 5 ? "Helpful from portfolio UI." : "Needs review from portfolio UI.",
    }),
  });
  if (!response.ok) throw new Error("Feedback could not be saved.");
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = input.value.trim();
  if (!message) return;

  addMessage("user", message);
  input.value = "";
  setStatus("Thinking");

  try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message,
        conversation_id: conversationId,
      conversation_token: conversationToken,
      }),
    });

    if (!response.ok) {
      throw new Error(`Chat request failed with ${response.status}`);
    }

    const payload = await response.json();
    conversationId = payload.conversation_id;
    conversationToken = payload.conversation_token || conversationToken;
    lastMessageId = payload.message_id;
    addMessage("assistant", payload.answer);
    renderMetadata(payload);
    setStatus("Ready");
  } catch (error) {
    addMessage("assistant", "The support API did not respond. Please check the backend server.");
    setStatus("Error");
  }
});

feedbackEl.addEventListener("click", async (event) => {
  const rating = event.target.dataset.rating;
  if (!rating) return;
  try {
    await sendFeedback(Number(rating));
    setStatus("Feedback saved");
  } catch {
    setStatus("Error");
  }
});

const API_BASE = "/api";

let currentConversationId = null;

// ---- DOM references ----

const chatMessages = document.getElementById("chat-messages");
const chatForm = document.getElementById("chat-form");
const questionInput = document.getElementById("question-input");
const sendBtn = document.getElementById("send-btn");
const uploadForm = document.getElementById("upload-form");
const fileInput = document.getElementById("file-input");
const uploadArea = document.getElementById("upload-area");
const uploadStatus = document.getElementById("upload-status");
const documentList = document.getElementById("document-list");
const newChatBtn = document.getElementById("new-chat-btn");
const conversationList = document.getElementById("conversation-list");

// ---- New Chat ----

function resetChat() {
    currentConversationId = null;
    chatMessages.innerHTML = `
        <div class="welcome-message">
            <h2>Ask questions about your documents</h2>
            <p>Upload a PDF or TXT file, then ask anything about its content.</p>
        </div>`;
    // Keep history visible after starting a new chat and only clear active selection.
    loadConversations();
}

// ---- Conversation history ----

async function loadConversations() {
    try {
        const res = await fetch(`${API_BASE}/conversations`);
        const data = await res.json();
        renderConversationList(data.conversations);
    } catch (err) {
        console.error("Failed to load conversations:", err);
    }
}

function renderConversationList(conversations) {
    if (!conversations || conversations.length === 0) {
        conversationList.innerHTML = '<p class="empty-state">No conversations yet.</p>';
        return;
    }
    conversationList.innerHTML = conversations.map((c) => `
        <div class="conversation-item ${c.id === currentConversationId ? "active" : ""}"
             data-id="${c.id}" onclick="openConversation('${c.id}', this)">
            <span class="conv-title" title="${escapeHtml(c.title)}">${escapeHtml(c.title)}</span>
            <button class="conv-delete" onclick="event.stopPropagation(); deleteConversation('${c.id}')" title="Delete">×</button>
        </div>
    `).join("");
}

async function openConversation(id, el) {
    try {
        const res = await fetch(`${API_BASE}/conversations/${id}`);
        if (!res.ok) return;
        const data = await res.json();

        currentConversationId = id;

        // Mark active
        document.querySelectorAll(".conversation-item").forEach(i => i.classList.remove("active"));
        if (el) el.classList.add("active");

        // Render messages
        chatMessages.innerHTML = "";
        data.messages.forEach((msg) => {
            let sources = null;
            if (msg.role === "assistant" && msg.sources) {
                try { sources = JSON.parse(msg.sources); } catch (_) {}
                // sources from DB are {document_name, chunk_preview} — adapt to display format
                if (sources) sources = sources.map(s => ({
                    document_name: s.document_name,
                    chunk_text: s.chunk_preview || "",
                }));
            }
            addMessage(msg.role, msg.content, sources);
        });
    } catch (err) {
        console.error("Failed to load conversation:", err);
    }
}

async function deleteConversation(id) {
    try {
        await fetch(`${API_BASE}/conversations/${id}`, { method: "DELETE" });
        if (currentConversationId === id) resetChat();
        loadConversations();
    } catch (err) {
        console.error("Failed to delete conversation:", err);
    }
}

window.openConversation = openConversation;
window.deleteConversation = deleteConversation;

// ---- Documents ----

async function loadDocuments() {
    try {
        const response = await fetch(`${API_BASE}/documents`);
        const data = await response.json();
        renderDocumentList(data.documents);
    } catch (err) {
        console.error("Failed to load documents:", err);
    }
}

function renderDocumentList(documents) {
    if (documents.length === 0) {
        documentList.innerHTML = '<p class="empty-state">No documents uploaded yet.</p>';
        return;
    }

    documentList.innerHTML = documents
        .map((doc) => {
            const statusClass = doc.status === "ready" ? "" : doc.status;
            const statusText = doc.status === "ready" ? `${doc.chunk_count} chunks` : doc.status;
            return `
                <div class="document-item" data-id="${doc.id}">
                    <span class="doc-name" title="${doc.filename}">${doc.filename}</span>
                    <span class="doc-status ${statusClass}">${statusText}</span>
                    <button class="delete-btn" onclick="deleteDocument('${doc.id}')" title="Delete">&times;</button>
                </div>
            `;
        })
        .join("");
}

async function uploadFile(file) {
    const formData = new FormData();
    formData.append("file", file);

    uploadStatus.hidden = false;
    uploadStatus.className = "upload-status";
    uploadStatus.textContent = `Uploading ${file.name}...`;

    try {
        const response = await fetch(`${API_BASE}/documents/upload`, {
            method: "POST",
            body: formData,
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || "Upload failed");
        }

        const doc = await response.json();
        uploadStatus.className = "upload-status success";
        uploadStatus.textContent = `${doc.filename} processed (${doc.chunk_count} chunks)`;
        loadDocuments();
    } catch (err) {
        uploadStatus.className = "upload-status error";
        uploadStatus.textContent = `Error: ${err.message}`;
    }
}

async function deleteDocument(documentId) {
    try {
        await fetch(`${API_BASE}/documents/${documentId}`, { method: "DELETE" });
        loadDocuments();
    } catch (err) {
        console.error("Failed to delete document:", err);
    }
}

// Make deleteDocument available globally for onclick handlers
window.deleteDocument = deleteDocument;

// ---- Chat ----

function addMessage(role, content, sources) {
    const welcome = chatMessages.querySelector(".welcome-message");
    if (welcome) welcome.remove();

    const messageDiv = document.createElement("div");
    messageDiv.className = `message ${role}`;

    const inner = document.createElement("div");
    inner.className = "message-inner";

    const roleLabel = document.createElement("div");
    roleLabel.className = "role-label";
    roleLabel.textContent = role === "user" ? "You" : "AI Assistant";

    const text = document.createElement("div");
    text.className = "message-text";
    text.textContent = content;

    inner.appendChild(roleLabel);
    inner.appendChild(text);

    if (sources && sources.length > 0) {
        const details = document.createElement("details");
        details.className = "sources-list";

        const summary = document.createElement("summary");
        summary.textContent = `${sources.length} source${sources.length > 1 ? "s" : ""}`;

        const items = document.createElement("div");
        items.className = "sources-items";

        sources.forEach((s) => {
            const item = document.createElement("div");
            item.className = "source-item";
            item.innerHTML = `
                <span class="source-name">${escapeHtml(s.document_name)}</span>
                <span class="source-preview">${escapeHtml(s.chunk_text.substring(0, 180))}${s.chunk_text.length > 180 ? "…" : ""}</span>
            `;
            items.appendChild(item);
        });

        details.appendChild(summary);
        details.appendChild(items);
        inner.appendChild(details);
    }

    messageDiv.appendChild(inner);
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function showLoading() {
    const wrapper = document.createElement("div");
    wrapper.className = "message assistant";
    wrapper.id = "loading";
    wrapper.innerHTML = `
        <div class="loading-indicator">
            <div class="loading-dots">
                <span></span><span></span><span></span>
            </div>
        </div>`;
    chatMessages.appendChild(wrapper);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function hideLoading() {
    const loader = document.getElementById("loading");
    if (loader) loader.remove();
}

async function askQuestion(question) {
    addMessage("user", question);
    showLoading();
    sendBtn.disabled = true;

    try {
        const body = { question };
        if (currentConversationId) {
            body.conversation_id = currentConversationId;
        }

        const response = await fetch(`${API_BASE}/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        });

        hideLoading();

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || "Request failed");
        }

        const data = await response.json();
        currentConversationId = data.conversation_id;
        addMessage("assistant", data.answer, data.sources);
        loadConversations();
    } catch (err) {
        hideLoading();
        addMessage("assistant", `Error: ${err.message}`);
    } finally {
        sendBtn.disabled = false;
        questionInput.focus();
    }
}

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

// ---- Event listeners ----

newChatBtn.addEventListener("click", () => {
    resetChat();
    questionInput.focus();
});

chatForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const question = questionInput.value.trim();
    if (!question) return;
    questionInput.value = "";
    askQuestion(question);
});

fileInput.addEventListener("change", () => {
    if (fileInput.files.length > 0) {
        uploadFile(fileInput.files[0]);
        fileInput.value = "";
    }
});

uploadArea.addEventListener("dragover", (e) => {
    e.preventDefault();
    uploadArea.classList.add("drag-over");
});

uploadArea.addEventListener("dragleave", () => {
    uploadArea.classList.remove("drag-over");
});

uploadArea.addEventListener("drop", (e) => {
    e.preventDefault();
    uploadArea.classList.remove("drag-over");
    if (e.dataTransfer.files.length > 0) {
        uploadFile(e.dataTransfer.files[0]);
    }
});

// ---- Init ----

loadDocuments();
loadConversations();

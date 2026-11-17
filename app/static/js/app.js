/**
 * DOCUINTEL AI — CLIENT CONTROLLER & RAG INTERFACE
 */

document.addEventListener("DOMContentLoaded", () => {
  // ============================================================================
  // DOM REFERENCES
  // ============================================================================
  const chatViewport = document.getElementById("chatViewport");
  const messagesStream = document.getElementById("messagesStream");
  const welcomeHero = document.getElementById("welcomeHero");
  const chatForm = document.getElementById("chatForm");
  const chatInput = document.getElementById("chatInput");
  const btnSendMessage = document.getElementById("btnSendMessage");
  const typingIndicator = document.getElementById("typingIndicator");

  // Dropzone & Upload
  const dropzone = document.getElementById("dropzoneCompact");
  const fileInput = document.getElementById("fileInput");
  const btnQuickUpload = document.getElementById("btnQuickUpload");
  const uploadBanner = document.getElementById("uploadBanner");
  const uploadProgressContainer = document.getElementById("uploadProgressContainer");
  const uploadProgressBar = document.getElementById("uploadProgressBar");
  const uploadStatusText = document.getElementById("uploadStatusText");
  const uploadProgressPercent = document.getElementById("uploadProgressPercent");

  // Right Panel & Knowledge Base
  const tabDocuments = document.getElementById("tabDocuments");
  const tabSources = document.getElementById("tabSources");
  const contentDocuments = document.getElementById("contentDocuments");
  const contentSources = document.getElementById("contentSources");
  const documentsList = document.getElementById("documentsList");
  const emptyDocsState = document.getElementById("emptyDocsState");
  const sourcesInspectorList = document.getElementById("sourcesInspectorList");
  const emptySourcesState = document.getElementById("emptySourcesState");
  const statDocCount = document.getElementById("statDocCount");
  const statChunkCount = document.getElementById("statChunkCount");
  const headerChunkCount = document.getElementById("headerChunkCount");
  const panelDocCount = document.getElementById("panelDocCount");
  const sidebarDocBadge = document.getElementById("sidebarDocBadge");
  const btnRefreshDocs = document.getElementById("btnRefreshDocs");

  // Nav & History Controls
  const btnNewChat = document.getElementById("btnNewChat");
  const btnClearAllHistory = document.getElementById("btnClearAllHistory");
  const chatSessionsList = document.getElementById("chatSessionsList");
  const suggestedPromptsGrid = document.getElementById("suggestedPromptsGrid");
  const activeProviderPill = document.getElementById("activeProviderPill");
  const sidebarProviderLabel = document.getElementById("sidebarProviderLabel");

  // Mobile Toggles
  const btnToggleSidebar = document.getElementById("btnToggleSidebar");
  const btnToggleRightPanel = document.getElementById("btnToggleRightPanel");
  const sidebarLeft = document.getElementById("sidebarLeft");
  const sidebarRight = document.getElementById("sidebarRight");

  // Modals
  const btnOpenSettings = document.getElementById("btnOpenSettings");
  const btnCloseSettings = document.getElementById("btnCloseSettings");
  const btnCancelSettings = document.getElementById("btnCancelSettings");
  const btnSaveSettings = document.getElementById("btnSaveSettings");
  const modalSettings = document.getElementById("modalSettings");
  const selectProvider = document.getElementById("selectProvider");
  const inputApiKey = document.getElementById("inputApiKey");
  const inputModelName = document.getElementById("inputModelName");
  const btnToggleKeyVis = document.getElementById("btnToggleKeyVis");
  const diagProvider = document.getElementById("diagProvider");
  const diagKeyStatus = document.getElementById("diagKeyStatus");
  const diagStorage = document.getElementById("diagStorage");

  const btnOpenAbout = document.getElementById("btnOpenAbout");
  const btnCloseAbout = document.getElementById("btnCloseAbout");
  const btnDismissAbout = document.getElementById("btnDismissAbout");
  const modalAbout = document.getElementById("modalAbout");

  const toastContainer = document.getElementById("toastContainer");

  // ============================================================================
  // APPLICATION STATE
  // ============================================================================
  let currentSessionId = "default";
  let isGenerating = false;
  let latestRetrievedSources = [];

  // Configure marked.js for safe markdown rendering
  if (typeof marked !== "undefined") {
    marked.setOptions({
      gfm: true,
      breaks: true
    });
  }

  // ============================================================================
  // INITIALIZATION
  // ============================================================================
  loadDocuments();
  checkSystemHealth();
  setupEventListeners();

  // ============================================================================
  // EVENT LISTENERS SETUP
  // ============================================================================
  function setupEventListeners() {
    // Chat Form Submit
    chatForm.addEventListener("submit", (e) => {
      e.preventDefault();
      handleSendMessage();
    });

    // Chat Textarea auto-resize and Enter key send
    chatInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSendMessage();
      }
    });

    chatInput.addEventListener("input", () => {
      chatInput.style.height = "auto";
      chatInput.style.height = Math.min(chatInput.scrollHeight, 120) + "px";
    });

    // Suggested Questions Chips
    suggestedPromptsGrid.addEventListener("click", (e) => {
      const chip = e.target.closest(".prompt-chip");
      if (chip) {
        const promptText = chip.getAttribute("data-prompt");
        chatInput.value = promptText;
        chatInput.focus();
        handleSendMessage();
      }
    });

    // Quick upload click
    btnQuickUpload.addEventListener("click", () => fileInput.click());

    // Dropzone Events
    dropzone.addEventListener("click", () => fileInput.click());
    
    ["dragenter", "dragover"].forEach(evtName => {
      dropzone.addEventListener(evtName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.add("dragover");
      });
    });

    ["dragleave", "drop"].forEach(evtName => {
      dropzone.addEventListener(evtName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.remove("dragover");
      });
    });

    dropzone.addEventListener("drop", (e) => {
      const files = e.dataTransfer.files;
      if (files && files.length > 0) {
        handleFileUpload(files[0]);
      }
    });

    fileInput.addEventListener("change", (e) => {
      if (fileInput.files && fileInput.files.length > 0) {
        handleFileUpload(fileInput.files[0]);
      }
    });

    // Panel Tabs
    tabDocuments.addEventListener("click", () => switchTab("documents"));
    tabSources.addEventListener("click", () => switchTab("sources"));

    // Nav Items
    btnNewChat.addEventListener("click", () => resetChat());
    btnClearAllHistory.addEventListener("click", () => clearConversationHistory());
    btnRefreshDocs.addEventListener("click", () => loadDocuments());

    // Modals
    btnOpenSettings.addEventListener("click", () => openSettingsModal());
    btnCloseSettings.addEventListener("click", () => modalSettings.classList.add("hidden"));
    btnCancelSettings.addEventListener("click", () => modalSettings.classList.add("hidden"));
    btnSaveSettings.addEventListener("click", () => saveSettings());

    btnOpenAbout.addEventListener("click", () => modalAbout.classList.remove("hidden"));
    btnCloseAbout.addEventListener("click", () => modalAbout.classList.add("hidden"));
    btnDismissAbout.addEventListener("click", () => modalAbout.classList.add("hidden"));

    btnToggleKeyVis.addEventListener("click", () => {
      const type = inputApiKey.getAttribute("type") === "password" ? "text" : "password";
      inputApiKey.setAttribute("type", type);
      btnToggleKeyVis.innerHTML = type === "password" ? '<i class="fa-solid fa-eye"></i>' : '<i class="fa-solid fa-eye-slash"></i>';
    });

    // Mobile Sidebar Toggles
    if (btnToggleSidebar) {
      btnToggleSidebar.addEventListener("click", () => {
        sidebarLeft.classList.toggle("open");
      });
    }
    if (btnToggleRightPanel) {
      btnToggleRightPanel.addEventListener("click", () => {
        sidebarRight.classList.toggle("open");
      });
    }
  }

  // ============================================================================
  // CHAT & RAG ENGINE
  // ============================================================================
  async function handleSendMessage() {
    const message = chatInput.value.trim();
    if (!message || isGenerating) return;

    // Reset input
    chatInput.value = "";
    chatInput.style.height = "auto";

    // Hide welcome hero if first message
    if (welcomeHero) welcomeHero.classList.add("hidden");

    // Append User Message to UI
    const timeStr = getCurrentTime();
    appendMessage({
      role: "user",
      content: message,
      timestamp: timeStr
    });

    // Scroll to bottom
    scrollToBottom();

    // Show Typing Indicator
    isGenerating = true;
    btnSendMessage.disabled = true;
    typingIndicator.classList.remove("hidden");
    scrollToBottom();

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: message,
          session_id: currentSessionId
        })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Failed to generate answer from RAG pipeline.");
      }

      // Hide typing indicator
      typingIndicator.classList.add("hidden");

      // Store latest sources
      latestRetrievedSources = data.sources || [];
      renderSourcesInspector(latestRetrievedSources);

      // Append Assistant Message to UI
      appendMessage({
        role: "assistant",
        content: data.answer,
        timestamp: getCurrentTime(),
        sources: data.sources,
        model: data.model_used,
        latency_ms: data.latency_ms
      });

    } catch (err) {
      typingIndicator.classList.add("hidden");
      showToast(err.message, "error");
      
      appendMessage({
        role: "assistant",
        content: `**Error**: ${err.message}\n\n*Tip: If you haven't uploaded any documents or your API key is invalid, please check the Settings or upload a document.*`,
        timestamp: getCurrentTime(),
        isError: true
      });
    } finally {
      isGenerating = false;
      btnSendMessage.disabled = false;
      scrollToBottom();
    }
  }

  function appendMessage({ role, content, timestamp, sources = [], model, latency_ms, isError = false }) {
    const row = document.createElement("div");
    row.className = `message-row ${role === "user" ? "user-row" : "assistant-row"}`;

    const avatar = document.createElement("div");
    avatar.className = "message-avatar";
    avatar.innerHTML = role === "user" ? '<i class="fa-regular fa-user"></i>' : '<i class="fa-solid fa-brain-circuit"></i>';

    const bubble = document.createElement("div");
    bubble.className = "message-bubble";

    // Format markdown or plain text
    let parsedHTML = "";
    if (typeof marked !== "undefined") {
      parsedHTML = marked.parse(content);
    } else {
      parsedHTML = `<p>${escapeHTML(content).replace(/\n/g, "<br>")}</p>`;
    }

    bubble.innerHTML = parsedHTML;

    // If sources exist, append expandable source badges and inline previews
    if (sources && sources.length > 0) {
      const inlineSourcesBox = document.createElement("div");
      inlineSourcesBox.className = "inline-sources-box";
      
      let sourcesHTML = `
        <div class="inline-sources-title">
          <i class="fa-solid fa-book-bookmark"></i> Verified Sources (${sources.length} Chunks Used):
        </div>
      `;

      sources.forEach((s, idx) => {
        sourcesHTML += `
          <div class="inline-source-item">
            <div class="inline-source-header">
              <span><strong>[${idx + 1}]</strong> ${escapeHTML(s.filename)} (Page ${s.page || 1})</span>
              <span class="source-score-pill">Match: ${(s.score * 100).toFixed(0)}%</span>
            </div>
            <div class="inline-source-snippet">"${escapeHTML(s.snippet)}"</div>
          </div>
        `;
      });

      inlineSourcesBox.innerHTML = sourcesHTML;
      bubble.appendChild(inlineSourcesBox);
    }

    // Message Metadata Footer
    const meta = document.createElement("div");
    meta.className = "message-meta";

    const leftMeta = document.createElement("div");
    leftMeta.className = "d-flex align-center gap-2";

    if (sources && sources.length > 0) {
      const sourceBadge = document.createElement("span");
      sourceBadge.className = "sources-badge";
      sourceBadge.innerHTML = `<i class="fa-solid fa-list-check"></i> ${sources.length} source references`;
      sourceBadge.addEventListener("click", () => {
        switchTab("sources");
        if (window.innerWidth <= 1024) sidebarRight.classList.add("open");
      });
      leftMeta.appendChild(sourceBadge);
    }

    if (latency_ms) {
      const latencyBadge = document.createElement("span");
      latencyBadge.style.color = "var(--text-dim)";
      latencyBadge.style.marginLeft = "8px";
      latencyBadge.textContent = `${latency_ms}ms`;
      leftMeta.appendChild(latencyBadge);
    }

    const rightMeta = document.createElement("div");
    rightMeta.className = "message-actions";

    // Copy Button
    const copyBtn = document.createElement("button");
    copyBtn.className = "btn-bubble-action";
    copyBtn.title = "Copy answer to clipboard";
    copyBtn.innerHTML = '<i class="fa-regular fa-copy"></i>';
    copyBtn.addEventListener("click", () => {
      navigator.clipboard.writeText(content);
      copyBtn.innerHTML = '<i class="fa-solid fa-check"></i>';
      setTimeout(() => { copyBtn.innerHTML = '<i class="fa-regular fa-copy"></i>'; }, 1800);
      showToast("Copied answer to clipboard!", "success");
    });
    rightMeta.appendChild(copyBtn);

    const timeSpan = document.createElement("span");
    timeSpan.style.color = "var(--text-dim)";
    timeSpan.style.fontSize = "11px";
    timeSpan.textContent = timestamp;
    rightMeta.appendChild(timeSpan);

    meta.appendChild(leftMeta);
    meta.appendChild(rightMeta);
    bubble.appendChild(meta);

    row.appendChild(avatar);
    row.appendChild(bubble);
    messagesStream.appendChild(row);
  }

  function resetChat() {
    messagesStream.innerHTML = "";
    if (welcomeHero) welcomeHero.classList.remove("hidden");
    latestRetrievedSources = [];
    renderSourcesInspector([]);
    showToast("Started a new chat session.", "info");
  }

  async function clearConversationHistory() {
    try {
      await fetch(`/api/history?session_id=${currentSessionId}`, { method: "DELETE" });
      resetChat();
      showToast("Conversation history cleared.", "success");
    } catch (e) {
      showToast("Failed to clear history.", "error");
    }
  }

  // ============================================================================
  // DOCUMENT MANAGEMENT & UPLOAD
  // ============================================================================
  async function handleFileUpload(file) {
    if (!file) return;

    const validExtensions = [".pdf", ".docx", ".txt"];
    const ext = "." + file.name.split(".").pop().toLowerCase();
    if (!validExtensions.includes(ext)) {
      showToast(`Invalid file format '${ext}'. Please upload PDF, DOCX, or TXT.`, "error");
      return;
    }

    if (file.size > 25 * 1024 * 1024) {
      showToast("File exceeds 25MB maximum limit.", "error");
      return;
    }

    // Show Progress Bar
    uploadProgressContainer.classList.remove("hidden");
    uploadProgressBar.style.width = "20%";
    uploadStatusText.textContent = `Uploading ${file.name}...`;
    uploadProgressPercent.textContent = "20%";

    const formData = new FormData();
    formData.append("file", file);

    try {
      // Advance progress
      setTimeout(() => {
        uploadProgressBar.style.width = "60%";
        uploadStatusText.textContent = `Extracting text and generating vector chunks...`;
        uploadProgressPercent.textContent = "60%";
      }, 400);

      const response = await fetch("/api/upload", {
        method: "POST",
        body: formData
      });

      const data = await response.json();

      if (response.status === 409) {
        // Duplicate file error
        uploadProgressBar.style.width = "100%";
        uploadProgressContainer.classList.add("hidden");
        showToast(data.message || "Document is already indexed.", "warning");
        fileInput.value = "";
        return;
      }

      if (!response.ok) {
        throw new Error(data.detail || data.message || "Upload failed.");
      }

      uploadProgressBar.style.width = "100%";
      uploadStatusText.textContent = "Indexing complete!";
      uploadProgressPercent.textContent = "100%";

      setTimeout(() => {
        uploadProgressContainer.classList.add("hidden");
        uploadProgressBar.style.width = "0%";
      }, 1000);

      showToast(`Successfully indexed ${data.document.filename} (${data.document.chunk_count} chunks)`, "success");
      fileInput.value = "";

      // Refresh documents list & stats
      await loadDocuments();

    } catch (err) {
      uploadProgressContainer.classList.add("hidden");
      fileInput.value = "";
      showToast(`Upload error: ${err.message}`, "error");
    }
  }

  async function loadDocuments() {
    try {
      const response = await fetch("/api/documents");
      const data = await response.json();

      renderDocumentsList(data.documents || []);
      updateStats(data.total_documents, data.total_chunks);
    } catch (e) {
      console.error("Failed to load documents:", e);
    }
  }

  function renderDocumentsList(documents) {
    documentsList.innerHTML = "";

    if (!documents || documents.length === 0) {
      emptyDocsState.classList.remove("hidden");
      documentsList.appendChild(emptyDocsState);
      return;
    }

    emptyDocsState.classList.add("hidden");

    documents.forEach((doc) => {
      const card = document.createElement("div");
      card.className = "doc-card";

      const ext = doc.file_type.replace(".", "").toLowerCase();
      const iconClass = ext === "pdf" ? "pdf" : (ext === "docx" ? "docx" : "txt");
      const iconFa = ext === "pdf" ? "fa-file-pdf" : (ext === "docx" ? "fa-file-word" : "fa-file-lines");

      card.innerHTML = `
        <div class="doc-card-header">
          <div class="doc-card-icon ${iconClass}">
            <i class="fa-solid ${iconFa}"></i>
          </div>
          <div class="doc-card-info">
            <div class="doc-card-name" title="${escapeHTML(doc.filename)}">${escapeHTML(doc.filename)}</div>
            <div class="doc-card-date">${escapeHTML(doc.uploaded_at)}</div>
          </div>
          <button class="btn-icon-subtle btn-delete-doc" data-id="${doc.doc_id}" title="Remove Document">
            <i class="fa-solid fa-trash"></i>
          </button>
        </div>
        <div class="doc-card-footer">
          <div class="doc-card-tags">
            <span class="doc-tag">${doc.file_size_formatted}</span>
            <span class="doc-tag">${doc.chunk_count} chunks</span>
            <span class="doc-tag">${doc.page_count} page(s)</span>
          </div>
        </div>
      `;

      // Delete listener
      const deleteBtn = card.querySelector(".btn-delete-doc");
      deleteBtn.addEventListener("click", async (e) => {
        e.stopPropagation();
        if (confirm(`Remove "${doc.filename}" from the knowledge base?`)) {
          await deleteDocument(doc.doc_id);
        }
      });

      documentsList.appendChild(card);
    });
  }

  async function deleteDocument(docId) {
    try {
      const response = await fetch(`/api/documents/${docId}`, { method: "DELETE" });
      const data = await response.json();
      if (response.ok) {
        showToast("Document removed from knowledge base.", "success");
        await loadDocuments();
      } else {
        showToast(data.detail || "Failed to delete document.", "error");
      }
    } catch (err) {
      showToast(`Error deleting document: ${err.message}`, "error");
    }
  }

  function updateStats(totalDocs, totalChunks) {
    statDocCount.textContent = totalDocs;
    statChunkCount.textContent = totalChunks;
    headerChunkCount.textContent = totalChunks;
    panelDocCount.textContent = totalDocs;
    sidebarDocBadge.textContent = totalDocs;
  }

  // ============================================================================
  // SOURCES INSPECTOR
  // ============================================================================
  function renderSourcesInspector(sources) {
    sourcesInspectorList.innerHTML = "";

    if (!sources || sources.length === 0) {
      emptySourcesState.classList.remove("hidden");
      sourcesInspectorList.appendChild(emptySourcesState);
      return;
    }

    emptySourcesState.classList.add("hidden");

    sources.forEach((s, idx) => {
      const card = document.createElement("div");
      card.className = "source-inspector-card";

      card.innerHTML = `
        <div class="source-inspector-header">
          <span class="source-file-title">#${idx + 1} — ${escapeHTML(s.filename)} (Page ${s.page || 1})</span>
          <span class="source-score-pill">Score: ${(s.score * 100).toFixed(0)}%</span>
        </div>
        <div class="source-inspector-text">
          "${escapeHTML(s.snippet)}"
        </div>
      `;

      sourcesInspectorList.appendChild(card);
    });
  }

  function switchTab(tabName) {
    if (tabName === "documents") {
      tabDocuments.classList.add("active");
      tabSources.classList.remove("active");
      contentDocuments.classList.add("active");
      contentSources.classList.remove("active");
    } else {
      tabSources.classList.add("active");
      tabDocuments.classList.remove("active");
      contentSources.classList.add("active");
      contentDocuments.classList.remove("active");
    }
  }

  // ============================================================================
  // SYSTEM HEALTH & SETTINGS
  // ============================================================================
  async function checkSystemHealth() {
    try {
      const response = await fetch("/api/health");
      const data = await response.json();

      // Update provider pill
      sidebarProviderLabel.textContent = `${capitalize(data.provider)} (${data.model})`;
      diagProvider.textContent = data.provider;
      diagKeyStatus.textContent = data.api_key_configured ? "Configured Active" : "Missing / Needs Setup";
      diagStorage.textContent = data.storage_path;

      if (!data.api_key_configured) {
        activeProviderPill.querySelector(".status-dot").className = "status-dot offline";
      } else {
        activeProviderPill.querySelector(".status-dot").className = "status-dot online";
      }
    } catch (e) {
      console.error("Health check error:", e);
    }
  }

  function openSettingsModal() {
    modalSettings.classList.remove("hidden");
    checkSystemHealth();
  }

  async function saveSettings() {
    const provider = selectProvider.value;
    const apiKey = inputApiKey.value.trim();
    const model = inputModelName.value.trim();

    try {
      const response = await fetch("/api/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          provider: provider,
          api_key: apiKey || undefined,
          model: model || undefined
        })
      });

      const data = await response.json();
      if (response.ok) {
        showToast("Settings updated successfully!", "success");
        modalSettings.classList.add("hidden");
        inputApiKey.value = "";
        await checkSystemHealth();
      } else {
        showToast(data.detail || "Failed to update settings.", "error");
      }
    } catch (e) {
      showToast(`Error saving settings: ${e.message}`, "error");
    }
  }

  // ============================================================================
  // UTILITIES
  // ============================================================================
  function showToast(message, type = "info") {
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    
    let icon = "fa-circle-info";
    if (type === "success") icon = "fa-circle-check";
    if (type === "error") icon = "fa-triangle-exclamation";
    if (type === "warning") icon = "fa-circle-exclamation";

    toast.innerHTML = `<i class="fa-solid ${icon}"></i> <span>${escapeHTML(message)}</span>`;
    toastContainer.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transform = "translateY(10px)";
      toast.style.transition = "all 0.3s ease";
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  }

  function scrollToBottom() {
    chatViewport.scrollTop = chatViewport.scrollHeight;
  }

  function getCurrentTime() {
    return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  function escapeHTML(str) {
    if (!str) return "";
    return str.replace(/[&<>'"]/g, 
      tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag)
    );
  }

  function capitalize(str) {
    if (!str) return "";
    return str.charAt(0).toUpperCase() + str.slice(1);
  }
});

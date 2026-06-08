document.addEventListener("DOMContentLoaded", () => {
    const chatForm = document.getElementById("chatForm");
    const queryInput = document.getElementById("queryInput");
    const chatArea = document.getElementById("chatArea");
    const typingIndicator = document.getElementById("typingIndicator");
    const suggestionChips = document.getElementById("suggestionChips");

    // Focus input on load
    queryInput.focus();

    // Form submit listener
    chatForm.addEventListener("submit", (e) => {
        e.preventDefault();
        const text = queryInput.value.trim();
        if (!text) return;

        queryInput.value = "";
        sendMessage(text);
    });

    // Handle suggestion chip click
    window.sendSuggestion = (text) => {
        sendMessage(text);
    };

    // Main send message handler
    async function sendMessage(text) {
        // Hide suggestion chips after first interaction
        if (suggestionChips) {
            suggestionChips.style.display = "none";
        }

        // Append User Message
        appendMessage("user", text);

        // Show Typing Indicator
        showLoading(true);
        scrollToBottom();

        try {
            const response = await fetch("/api/chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ question: text })
            });

            const data = await response.json();
            showLoading(false);

            if (response.ok) {
                // Successful answer
                appendMessage("ai", data.answer, {
                    source: data.source
                });
            } else {
                // Error / PII block
                const errMsg = data.detail || "Something went wrong. Please try again.";
                const isPII = response.status === 400 && errMsg.includes("security");
                appendMessage("error", errMsg, { isPII });
            }
        } catch (error) {
            showLoading(false);
            appendMessage("error", "Failed to connect to the backend server. Make sure the API is running.");
        }

        scrollToBottom();
    }

    // Helper to format text markdown to HTML
    function formatMessageText(text) {
        let html = text;
        
        // Escape HTML to prevent XSS (basic)
        html = html
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");

        // Convert Markdown links: [title](url)
        // Match [label](url) where label doesn't contain [ or ] and url doesn't contain )
        html = html.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, (match, label, url) => {
            return `<a href="${url}" target="_blank" rel="noopener" class="source-link">${label} <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="display:inline-block;vertical-align:middle;margin-left:1px;"><line x1="7" y1="17" x2="17" y2="7"></line><polyline points="7 7 17 7 17 17"></polyline></svg></a>`;
        });

        // Convert Bold text: **text**
        html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");

        // Convert newlines to HTML breaks
        html = html.replace(/\n/g, "<br>");

        return html;
    }

    // Append Message bubble to DOM
    function appendMessage(sender, text, meta = {}) {
        const messageDiv = document.createElement("div");
        messageDiv.classList.add("message");

        if (sender === "user") {
            messageDiv.classList.add("user-msg");
            messageDiv.innerHTML = `
                <div class="bubble">
                    <p>${formatMessageText(text)}</p>
                </div>
            `;
        } else if (sender === "ai") {
            messageDiv.classList.add("ai-msg");
            
            // Format time stamp or badge info
            let metaHtml = "";
            if (meta.source) {
                metaHtml = `<div class="message-meta">`;
                metaHtml += `
                    <a href="${meta.source}" target="_blank" rel="noopener" class="source-link">
                        Official Document 
                        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                            <line x1="7" y1="17" x2="17" y2="7"></line>
                            <polyline points="7 7 17 7 17 17"></polyline>
                        </svg>
                    </a>
                `;
                metaHtml += `</div>`;
            }

            messageDiv.innerHTML = `
                <div class="bubble">
                    <p>${formatMessageText(text)}</p>
                </div>
                ${metaHtml}
            `;
        } else if (sender === "error") {
            messageDiv.classList.add("ai-msg");
            if (meta.isPII) {
                messageDiv.classList.add("compliance-block");
            }
            messageDiv.innerHTML = `
                <div class="bubble">
                    <p>${formatMessageText(text)}</p>
                </div>
            `;
        }

        chatArea.appendChild(messageDiv);
        scrollToBottom();
    }

    // Toggle typing indicator loading display
    function showLoading(show) {
        if (show) {
            typingIndicator.style.display = "block";
        } else {
            typingIndicator.style.display = "none";
        }
    }

    // Scroll chat area to bottom
    function scrollToBottom() {
        chatArea.scrollTop = chatArea.scrollHeight;
    }
});

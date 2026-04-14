// Complete Chat Manager
class ChatManager {
    constructor(otherUsername) {
        this.otherUsername = otherUsername;
        this.currentUsername = document.querySelector('meta[name="current-username"]')?.content || '';
        this.pollingInterval = null;
        this.lastMessageId = 0;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.startPolling();
        this.scrollToBottom();
    }

    setupEventListeners() {
        const messageInput = document.getElementById('message-input');
        const sendBtn = document.getElementById('send-btn');
        const attachBtn = document.getElementById('attach-btn');
        const fileInput = document.getElementById('file-input');

        if (messageInput) {
            messageInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });
        }

        if (sendBtn) {
            sendBtn.addEventListener('click', () => this.sendMessage());
        }

        if (attachBtn && fileInput) {
            attachBtn.addEventListener('click', () => fileInput.click());
            fileInput.addEventListener('change', (e) => {
                if (e.target.files[0]) this.uploadFile(e.target.files[0]);
                fileInput.value = '';
            });
        }
    }

    scrollToBottom() {
        const div = document.getElementById('chat-messages');
        if (div) div.scrollTop = div.scrollHeight;
    }

    formatTime(isoString) {
        if (!isoString) return '';
        const date = new Date(isoString);
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }

    addTextMessage(content, isSent, msgId, createdAt) {
        const container = document.getElementById('chat-messages');
        if (!container) return;

        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${isSent ? 'message-sent' : 'message-received'}`;
        if (msgId) msgDiv.setAttribute('data-msg-id', msgId);

        const bubble = document.createElement('div');
        bubble.className = 'message-bubble';
        bubble.textContent = content;

        const time = document.createElement('div');
        time.className = 'message-time';
        time.textContent = this.formatTime(createdAt);

        msgDiv.appendChild(bubble);
        msgDiv.appendChild(time);
        container.appendChild(msgDiv);
        this.scrollToBottom();
    }

    addImageMessage(imageUrl, isSent, msgId, createdAt) {
        const container = document.getElementById('chat-messages');
        if (!container) return;

        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${isSent ? 'message-sent' : 'message-received'}`;
        if (msgId) msgDiv.setAttribute('data-msg-id', msgId);

        const bubble = document.createElement('div');
        bubble.className = 'message-bubble';

        const img = document.createElement('img');
        img.src = imageUrl;
        img.style.maxWidth = '200px';
        img.style.maxHeight = '200px';
        img.style.borderRadius = '8px';
        img.style.cursor = 'pointer';
        img.onclick = () => window.open(imageUrl, '_blank');
        bubble.appendChild(img);

        const time = document.createElement('div');
        time.className = 'message-time';
        time.textContent = this.formatTime(createdAt);

        msgDiv.appendChild(bubble);
        msgDiv.appendChild(time);
        container.appendChild(msgDiv);
        this.scrollToBottom();
    }

    addFileMessage(fileUrl, fileName, isSent, msgId, createdAt) {
        const container = document.getElementById('chat-messages');
        if (!container) return;

        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${isSent ? 'message-sent' : 'message-received'}`;
        if (msgId) msgDiv.setAttribute('data-msg-id', msgId);

        const bubble = document.createElement('div');
        bubble.className = 'message-bubble';
        bubble.innerHTML = `<a href="${fileUrl}" target="_blank" class="text-indigo-600 hover:underline">📎 ${fileName}</a>`;

        const time = document.createElement('div');
        time.className = 'message-time';
        time.textContent = this.formatTime(createdAt);

        msgDiv.appendChild(bubble);
        msgDiv.appendChild(time);
        container.appendChild(msgDiv);
        this.scrollToBottom();
    }

    uploadFile(file) {
        const formData = new FormData();
        formData.append('file', file);
        const isImage = file.type.startsWith('image/');

        fetch('/api/upload-chat-file/', {
            method: 'POST',
            headers: { 'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value },
            body: formData
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                // Create message with file
                fetch(`/chat/send/${this.otherUsername}/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ message: `[${isImage ? 'image' : 'file'}] ${data.file_name}` })
                })
                .then(res => res.json())
                .then(msgData => {
                    if (msgData.success) {
                        if (isImage) {
                            this.addImageMessage(data.url, true, msgData.message_id, msgData.created_at);
                        } else {
                            this.addFileMessage(data.url, data.file_name, true, msgData.message_id, msgData.created_at);
                        }
                    }
                });
            }
        });
    }

    sendMessage() {
        const input = document.getElementById('message-input');
        const content = input?.value.trim();
        if (!content) return;

        input.value = '';
        input.disabled = true;

        fetch(`/chat/send/${this.otherUsername}/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ message: content })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                this.addTextMessage(content, true, data.message_id, data.created_at);
                if (data.message_id > this.lastMessageId) this.lastMessageId = data.message_id;
            }
        })
        .finally(() => {
            input.disabled = false;
            input.focus();
        });
    }

    pollMessages() {
        fetch(`/chat/messages/${this.otherUsername}/?since=${this.lastMessageId}`)
            .then(res => res.json())
            .then(data => {
                if (data.messages && data.messages.length > 0) {
                    data.messages.forEach(msg => {
                        if (msg.sender !== this.currentUsername) {
                            if (msg.type === 'image') {
                                this.addImageMessage(msg.file_url, false, msg.id, msg.created_at);
                            } else if (msg.type === 'file') {
                                this.addFileMessage(msg.file_url, msg.file_name, false, msg.id, msg.created_at);
                            } else {
                                this.addTextMessage(msg.content, false, msg.id, msg.created_at);
                            }
                        }
                        if (msg.id > this.lastMessageId) this.lastMessageId = msg.id;
                    });
                }
            })
            .catch(console.error);
    }

    startPolling() {
        this.pollingInterval = setInterval(() => this.pollMessages(), 2000);
        this.pollMessages();
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    const meta = document.querySelector('meta[name="other-username"]');
    if (meta && meta.content) {
        window.chatManager = new ChatManager(meta.content);
    }
});
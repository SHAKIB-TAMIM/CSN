// Chat WebSocket Handler
class ChatManager {
    constructor() {
        this.socket = null;
        this.conversationId = null;
        this.typingTimeout = null;
        this.init();
    }
    
    init() {
        this.connect();
        this.setupEventListeners();
    }
    
    connect() {
        const username = document.querySelector('meta[name="other-username"]')?.content;
        if (!username) return;
        
        this.socket = new WebSocket(
            `ws://${window.location.host}/ws/chat/${username}/`
        );
        
        this.socket.onopen = () => {
            console.log('Chat WebSocket connected');
            this.markMessagesAsRead();
        };
        
        this.socket.onmessage = (e) => {
            const data = JSON.parse(e.data);
            this.handleNewMessage(data.message);
        };
        
        this.socket.onclose = () => {
            console.log('Chat WebSocket disconnected');
            setTimeout(() => this.connect(), 3000);
        };
    }
    
    setupEventListeners() {
        // Message input
        const messageInput = document.getElementById('message-input');
        if (messageInput) {
            messageInput.addEventListener('keypress', () => this.handleTyping());
            messageInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });
        }
        
        // Send button
        const sendBtn = document.getElementById('send-message');
        if (sendBtn) {
            sendBtn.addEventListener('click', () => this.sendMessage());
        }
        
        // File upload
        const fileInput = document.getElementById('file-upload');
        if (fileInput) {
            fileInput.addEventListener('change', (e) => this.handleFileUpload(e));
        }
    }
    
    sendMessage() {
        const input = document.getElementById('message-input');
        const content = input.value.trim();
        
        if (!content) return;
        
        this.socket.send(JSON.stringify({
            type: 'message',
            content: content
        }));
        
        input.value = '';
        this.stopTyping();
    }
    
    handleNewMessage(message) {
        // Add message to chat
        this.appendMessage(message);
        
        // Scroll to bottom
        const chatContainer = document.getElementById('chat-messages');
        chatContainer.scrollTop = chatContainer.scrollHeight;
        
        // Play notification sound
        if (message.sender_id !== currentUserId) {
            this.playNotificationSound();
        }
    }
    
    appendMessage(message) {
        const template = document.getElementById('message-template');
        const clone = template.content.cloneNode(true);
        
        const messageDiv = clone.querySelector('.message');
        messageDiv.classList.add(message.sender_id === currentUserId ? 'sent' : 'received');
        
        clone.querySelector('.message-content').textContent = message.content;
        clone.querySelector('.message-time').textContent = new Date(message.created_at).toLocaleTimeString();
        
        document.getElementById('chat-messages').appendChild(clone);
    }
    
    handleTyping() {
        if (this.typingTimeout) {
            clearTimeout(this.typingTimeout);
        } else {
            this.socket.send(JSON.stringify({ type: 'typing', typing: true }));
        }
        
        this.typingTimeout = setTimeout(() => {
            this.stopTyping();
        }, 1000);
    }
    
    stopTyping() {
        this.socket.send(JSON.stringify({ type: 'typing', typing: false }));
        this.typingTimeout = null;
    }
    
    handleFileUpload(event) {
        const file = event.target.files[0];
        if (!file) return;
        
        const formData = new FormData();
        formData.append('file', file);
        formData.append('conversation_id', this.conversationId);
        
        fetch('/api/upload-chat-file/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            },
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.socket.send(JSON.stringify({
                    type: 'file',
                    file_url: data.url,
                    file_type: data.type
                }));
            }
        });
    }
    
    markMessagesAsRead() {
        fetch('/api/mark-messages-read/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                conversation_id: this.conversationId
            })
        });
    }
    
    playNotificationSound() {
        const audio = new Audio('/static/core/sounds/notification.mp3');
        audio.play().catch(() => {});
    }
}

// Initialize chat
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('chat-container')) {
        window.chatManager = new ChatManager();
    }
});
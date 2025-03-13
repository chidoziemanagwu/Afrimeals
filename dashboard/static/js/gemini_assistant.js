// dashboard/static/js/gemini_assistant.js
class GeminiAssistant {
    constructor() {
        this.baseUrl = '/api/gemini';
        // Remove duplicate chat interface setup since it's already in base.html
        this.setupEventListeners();
        // No need to add welcome message as it's in the HTML
    }

    async chat(message) {
        try {
            const response = await fetch(`${this.baseUrl}/chat/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCsrfToken()
                },
                body: JSON.stringify({ message })
            });

            if (!response.ok) throw new Error('Failed to get response');
            return await response.json();
        } catch (error) {
            console.error('Error:', error);
            throw error;
        }
    }

    setupEventListeners() {
        const chatToggle = document.getElementById('chat-toggle');
        const closeChat = document.getElementById('close-chat');
        const chatWindow = document.getElementById('chat-window');
        const chatForm = document.getElementById('chat-form');
        const chatInput = document.getElementById('chat-input');

        // Toggle chat window
        chatToggle?.addEventListener('click', () => {
            chatWindow.classList.toggle('hidden');
            chatToggle.classList.toggle('hidden');
            chatInput.focus();
        });

        // Close chat window
        closeChat?.addEventListener('click', () => {
            chatWindow.classList.add('hidden');
            chatToggle.classList.remove('hidden');
        });

        // Handle chat form submission
        chatForm?.addEventListener('submit', async (e) => {
            e.preventDefault();
            const message = chatInput.value.trim();
            if (!message) return;

            // Add user message to chat
            this.addMessage('user', message);
            chatInput.value = '';
            chatInput.focus();

            try {
                // Show typing indicator
                this.showTypingIndicator();

                // Get response from Gemini
                const response = await this.chat(message);
                
                // Remove typing indicator and add response
                this.removeTypingIndicator();
                this.addMessage('assistant', response.message);
            } catch (error) {
                console.error('Chat error:', error);
                this.removeTypingIndicator();
                this.addMessage('assistant', 'Sorry, I encountered an error. Please try again.');
            }
        });

        // Handle Enter key
        chatInput?.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                chatForm.dispatchEvent(new Event('submit'));
            }
        });
    }

    showTypingIndicator() {
        const typingDiv = document.createElement('div');
        typingDiv.id = 'typing-indicator';
        typingDiv.className = 'flex items-start';
        typingDiv.innerHTML = `
            <div class="flex-shrink-0">
                <div class="h-8 w-8 rounded-full bg-green-100 flex items-center justify-center">
                    <i class="fas fa-robot text-green-600"></i>
                </div>
            </div>
            <div class="ml-3 bg-gray-100 rounded-lg p-3">
                <div class="typing-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
        `;
        document.getElementById('chat-messages').appendChild(typingDiv);
        this.scrollToBottom();
    }

    removeTypingIndicator() {
        const typingIndicator = document.getElementById('typing-indicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }

    addMessage(type, content) {
        const chatMessages = document.getElementById('chat-messages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `flex items-start ${type === 'user' ? 'justify-end' : ''}`;

        const messageContent = `
            ${type === 'assistant' ? `
                <div class="flex-shrink-0">
                    <div class="h-8 w-8 rounded-full bg-green-100 flex items-center justify-center">
                        <i class="fas fa-robot text-green-600"></i>
                    </div>
                </div>
            ` : ''}
            <div class="ml-3 ${type === 'user' ? 'bg-green-600 text-white' : 'bg-gray-100 text-gray-800'} rounded-lg p-3">
                <p class="text-sm whitespace-pre-wrap">${content}</p>
            </div>
        `;

        messageDiv.innerHTML = messageContent;
        chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
    }

    scrollToBottom() {
        const chatMessages = document.getElementById('chat-messages');
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    getCsrfToken() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
        if (!token) {
            console.warn('CSRF token not found');
            return '';
        }
        return token;
    }
}

// Add necessary CSS
const style = document.createElement('style');
style.textContent = `
    .typing-dots {
        display: flex;
        gap: 4px;
    }
    .typing-dots span {
        width: 8px;
        height: 8px;
        background: #10B981;
        border-radius: 50%;
        animation: typing 1s infinite ease-in-out;
    }
    .typing-dots span:nth-child(2) { animation-delay: 0.2s; }
    .typing-dots span:nth-child(3) { animation-delay: 0.4s; }
    @keyframes typing {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.5); }
    }
`;
document.head.appendChild(style);

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.geminiAssistant = new GeminiAssistant();
});
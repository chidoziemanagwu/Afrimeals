// dashboard/static/js/gemini_assistant.js

class GeminiAssistant {
    constructor() {
        this.baseUrl = '/api/gemini';
        this.setupChatInterface();
        this.addWelcomeMessage();
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

    setupChatInterface() {
        const chatHTML = `
            <div id="gemini-chat-widget" class="fixed bottom-4 right-4 z-50">
                <!-- Chat Toggle Button -->
                <button id="chat-toggle" class="bg-green-600 text-white p-4 rounded-full shadow-lg hover:bg-green-700 transition-all duration-300">
                    <i class="fas fa-comments text-xl"></i>
                </button>

                <!-- Chat Window -->
                <div id="chat-window" class="hidden absolute bottom-16 right-0 w-96 bg-white rounded-lg shadow-xl">
                    <!-- Chat Header -->
                    <div class="bg-green-600 text-white p-4 rounded-t-lg flex justify-between items-center">
                        <h3 class="text-lg font-semibold">Gemini Assistant</h3>
                        <button id="close-chat" class="text-white hover:text-gray-200">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                    
                    <!-- Chat Messages -->
                    <div id="chat-messages" class="h-96 overflow-y-auto p-4 space-y-4">
                    </div>
                    
                    <!-- Chat Input -->
                    <div class="border-t p-4">
                        <form id="chat-form" class="flex items-center space-x-2">
                            <input type="text" 
                                   id="chat-input" 
                                   class="flex-1 border rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-green-500"
                                   placeholder="Type your message...">
                            <button type="submit" 
                                    class="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition-colors">
                                <i class="fas fa-paper-plane"></i>
                            </button>
                        </form>
                    </div>
                </div>
            </div>
        `;

        // Add chat interface to the page
        document.body.insertAdjacentHTML('beforeend', chatHTML);
        this.setupEventListeners();
    }

    addWelcomeMessage() {
        setTimeout(() => {
            this.addMessage('assistant', `Hello! I'm your Nigerian cuisine assistant. I can help you with:
- Finding ingredients and substitutes
- Recipe suggestions and modifications
- Cooking tips and techniques
- Cultural context and history

What would you like to know?`);
        }, 500);
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

        // Close chat window when clicking outside
        document.addEventListener('click', (e) => {
            const chatWidget = document.getElementById('gemini-chat-widget');
            if (chatWidget && !chatWidget.contains(e.target)) {
                chatWindow.classList.add('hidden');
                chatToggle.classList.remove('hidden');
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

    async getRecipeRecommendations(preferences) {
        try {
            const response = await fetch(`${this.baseUrl}/recommendations/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCsrfToken()
                },
                body: JSON.stringify(preferences)
            });

            if (!response.ok) throw new Error('Failed to get recommendations');
            return await response.json();
        } catch (error) {
            console.error('Error:', error);
            throw error;
        }
    }

    async findIngredientSubstitutes(ingredient, location = 'UK') {
        try {
            const response = await fetch(`${this.baseUrl}/substitutes/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCsrfToken()
                },
                body: JSON.stringify({ ingredient, location })
            });

            if (!response.ok) throw new Error('Failed to find substitutes');
            return await response.json();
        } catch (error) {
            console.error('Error:', error);
            throw error;
        }
    }

    async getCookingTips(recipeName) {
        try {
            const response = await fetch(`${this.baseUrl}/cooking-tips/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCsrfToken()
                },
                body: JSON.stringify({ recipe_name: recipeName })
            });

            if (!response.ok) throw new Error('Failed to get cooking tips');
            return await response.json();
        } catch (error) {
            console.error('Error:', error);
            throw error;
        }
    }

    getCsrfToken() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
        if (!token) {
            throw new Error('CSRF token not found');
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

// Initialize and export
window.geminiAssistant = new GeminiAssistant();
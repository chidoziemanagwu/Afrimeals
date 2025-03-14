// dashboard/static/js/gemini_assistant.js
class GeminiAssistant {
    constructor() {
        this.baseUrl = '/api/gemini';
        this.setupEventListeners();
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
        const chatMessages = document.getElementById('chat-messages');

        // Ensure elements exist before adding listeners
        if (chatToggle) {
            chatToggle.addEventListener('click', () => {
                chatWindow.classList.toggle('hidden');
                chatToggle.classList.toggle('hidden');
                chatInput.focus();
            });
        }

        if (closeChat) {
            closeChat.addEventListener('click', () => {
                chatWindow.classList.add('hidden');
                chatToggle.classList.remove('hidden');
            });
        }

        if (chatForm) {
            chatForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                const message = chatInput.value.trim();
                if (!message) return;

                this.addMessage('user', message);
                chatInput.value = '';
                chatInput.focus();

                try {
                    this.showTypingIndicator();
                    const response = await this.chat(message);
                    this.removeTypingIndicator();
                    this.addMessage('assistant', response.message);
                } catch (error) {
                    console.error('Chat error:', error);
                    this.removeTypingIndicator();
                    this.addMessage('assistant', 'Sorry, I encountered an error. Please try again.');
                }
            });
        }

        if (chatInput) {
            chatInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    chatForm.dispatchEvent(new Event('submit'));
                }
            });
        }
    }

    showTypingIndicator() {
        const chatMessages = document.getElementById('chat-messages');
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
        chatMessages.appendChild(typingDiv);
        this.scrollToBottom();
    }

    removeTypingIndicator() {
        const typingIndicator = document.getElementById('typing-indicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }

    // Add this function to your GeminiAssistant class
    formatMessage(content) {
        // Convert markdown-style lists to HTML
        content = content.replace(/^\s*•\s+(.+)$/gm, '<li>$1</li>');
        content = content.replace(/^\s*\d+\.\s+(.+)$/gm, '<li>$1</li>');
        
        // Wrap lists in appropriate tags
        content = content.replace(/<li>.*?<\/li>/gs, function(match) {
            if (match.includes('1.')) {
                return '<ol>' + match + '</ol>';
            }
            return '<ul>' + match + '</ul>';
        });
    
        // Handle sections and headers
        content = content.replace(/^Section \d+:/gm, '<h3 class="text-lg font-semibold mt-4 mb-2">$&</h3>');
        
        // Handle bold text
        content = content.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        
        // Handle italics
        content = content.replace(/\*(.*?)\*/g, '<em>$1</em>');
        
        return content;
    }
    
    // Update the addMessage method in your GeminiAssistant class
    addMessage(type, content) {
        const chatMessages = document.getElementById('chat-messages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `flex items-start ${type === 'user' ? 'justify-end' : ''} mb-4`;

        if (type === 'user') {
            // User message
            messageDiv.innerHTML = `
                <div class="bg-green-600 text-white rounded-2xl rounded-br-none px-4 py-2 max-w-[80%] shadow-sm">
                    <p class="text-sm">${content}</p>
                </div>
            `;
        } else {
            // Assistant message with structured content
            const formattedContent = this.formatAssistantMessage(content);
            messageDiv.innerHTML = `
                <div class="flex items-start space-x-2 max-w-[80%]">
                    <div class="flex-shrink-0">
                        <div class="h-8 w-8 rounded-full bg-green-100 flex items-center justify-center">
                            <i class="fas fa-robot text-green-600"></i>
                        </div>
                    </div>
                    <div class="bg-white border border-gray-200 rounded-2xl rounded-tl-none px-4 py-2 shadow-sm">
                        ${formattedContent}
                    </div>
                </div>
            `;
        }

        chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
    }

    // Add this new method to handle assistant message formatting
    formatAssistantMessage(content) {
        // Split content into sections if it contains headers
        const sections = content.split(/(?=Why it's great:|Smoking Techniques:|Tips:|Instructions:|Note:)/g);
        
        return sections.map(section => {
            // Check if section starts with a known header
            const isHeader = /^(Why it's great:|Smoking Techniques:|Tips:|Instructions:|Note:)/.test(section);
            
            if (isHeader) {
                // Extract header and content
                const [header, ...contentParts] = section.split(':');
                const sectionContent = contentParts.join(':').trim();
                
                return `
                    <div class="mb-3">
                        <h4 class="text-green-600 font-semibold text-sm mb-1">${header}:</h4>
                        <p class="text-gray-700 text-sm">${this.formatTextContent(sectionContent)}</p>
                    </div>
                `;
            } else {
                // Regular content
                return `<p class="text-gray-700 text-sm mb-2">${this.formatTextContent(section.trim())}</p>`;
            }
        }).join('');
    }

    // Add this helper method to format text content
    formatTextContent(text) {
        return text
            // Convert bullet points
            .replace(/•\s+([^\n]+)/g, '<li class="ml-4">$1</li>')
            // Convert numbered lists
            .replace(/(\d+\.\s+[^\n]+)/g, '<li class="ml-4">$1</li>')
            // Convert links
            .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" class="text-green-600 hover:underline">$1</a>')
            // Convert bold text
            .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
            // Convert italic text
            .replace(/\*([^*]+)\*/g, '<em>$1</em>');
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
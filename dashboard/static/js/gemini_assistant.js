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

        const chatToggleContainer = document.getElementById('chat-toggle-container');

        // Ensure elements exist before adding listeners

        if (chatToggle && chatWindow && chatToggleContainer) {
            chatToggle.addEventListener('click', () => {
              chatWindow.classList.remove('hidden');
              chatToggleContainer.classList.add('hidden');
              this.scrollToBottom();
            });
          }
        
        if (closeChat && chatWindow && chatToggleContainer) {
            closeChat.addEventListener('click', () => {
              chatWindow.classList.add('hidden');
              chatToggleContainer.classList.remove('hidden');
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

    formatAssistantMessage(content) {
        // First, clean up any malformed HTML
        content = content.replace(/(<\/?div[^>]*>|<\/?em>|<\/?a[^>]*>)/g, '');
        
        // Split content into sections
        const sections = content.split(/(?=📍|•|\d+\.|NaijaPlate's Recipe Recommendations|I\.|II\.|III\.)/g);
        
        return sections.map(section => {
            section = section.trim();
            
            // Handle recipe tutorial sections
            if (section.match(/^(I\.|II\.|III\.)/)) {
                return this.formatRecipeSection(section);
            }
            
            // Handle main sections
            if (section.startsWith('📍')) {
                return `
                    <div class="bg-white rounded-lg shadow-sm p-4 mb-4">
                        <p class="text-gray-700 text-sm">${section.substring(2).trim()}</p>
                    </div>
                `;
            }
            
            // Handle ingredients or steps
            if (section.includes('•')) {
                return this.formatIngredientsList(section);
            }
            
            // Regular content
            return `<p class="text-gray-700 text-sm mb-3">${this.formatTextContent(section)}</p>`;
        }).join('');
    }
    
    formatRecipeSection(section) {
        const lines = section.split('\n');
        const title = lines[0].trim();
        
        return `
            <div class="recipe-section bg-white rounded-lg shadow-sm p-4 mb-4">
                <h3 class="text-green-800 font-semibold text-lg mb-3">
                    <i class="fas fa-utensils mr-2"></i>${title}
                </h3>
                <div class="space-y-3">
                    ${this.formatRecipeContent(lines.slice(1).join('\n'))}
                </div>
            </div>
        `;
    }
    
    formatIngredientsList(section) {
        const items = section.split('•').filter(item => item.trim());
        
        return `
            <div class="ingredients-list bg-white rounded-lg shadow-sm p-4 mb-4">
                <div class="space-y-2">
                    ${items.map(item => `
                        <div class="flex items-start space-x-2">
                            <i class="fas fa-check-circle text-green-600 mt-1"></i>
                            <span class="text-gray-700 text-sm">${this.formatTextContent(item.trim())}</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }
    
    // Add this method to your GeminiAssistant class
    formatRecipeContent(content) {
        // Split content into parts (video, ingredients, instructions, etc.)
        const parts = content.split(/(?=• Cooking Video:|• Key Ingredients:|• Finding Ingredients)/g);
        
        return parts.map(part => {
            part = part.trim();
            
            // Handle video links
            if (part.startsWith('• Cooking Video:')) {
                return this.formatVideoSection(part);
            }
            
            // Handle ingredients section
            if (part.startsWith('• Key Ingredients:')) {
                return this.formatKeyIngredients(part);
            }
            
            // Handle finding ingredients section
            if (part.startsWith('• Finding Ingredients')) {
                return this.formatSourceInfo(part);
            }
            
            // Regular content
            return `<p class="text-gray-700 text-sm">${this.formatTextContent(part)}</p>`;
        }).join('');
    }

    // Add these helper methods as well
    formatVideoSection(content) {
        const videoMatch = content.match(/\[([^\]]+)\]\(([^)]+)\)/);
        if (videoMatch) {
            return `
                <div class="video-link mb-3">
                    <h4 class="text-green-700 font-medium mb-2">
                        <i class="fab fa-youtube text-red-600 mr-2"></i>Tutorial Video
                    </h4>
                    <a href="${videoMatch[2]}" target="_blank" 
                    class="text-green-600 hover:text-green-800 flex items-center">
                        <i class="fas fa-play-circle mr-2"></i>
                        ${videoMatch[1]}
                    </a>
                </div>
            `;
        }
        return '';
    }

    formatKeyIngredients(content) {
        const items = content.split('\n')
            .filter(line => line.trim().startsWith('•'))
            .map(line => line.replace('•', '').trim());
        
        return `
            <div class="ingredients mb-3">
                <h4 class="text-green-700 font-medium mb-2">
                    <i class="fas fa-mortar-pestle mr-2"></i>Key Ingredients
                </h4>
                <div class="grid gap-2">
                    ${items.map(item => `
                        <div class="flex items-start space-x-2">
                            <i class="fas fa-check-circle text-green-600 mt-1"></i>
                            <span class="text-gray-700 text-sm">${this.formatTextContent(item)}</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    formatSourceInfo(content) {
        const items = content.split('\n')
            .filter(line => line.trim().startsWith('•'))
            .map(line => line.replace('•', '').trim());
        
        return `
            <div class="sourcing-info mb-3">
                <h4 class="text-green-700 font-medium mb-2">
                    <i class="fas fa-shopping-basket mr-2"></i>Where to Find Ingredients
                </h4>
                <div class="space-y-2">
                    ${items.map(item => `
                        <div class="flex items-start space-x-2">
                            <i class="fas fa-store text-green-600 mt-1"></i>
                            <span class="text-gray-700 text-sm">${this.formatTextContent(item)}</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    formatTextContent(text) {
        return text
            // Clean up URLs and make them clickable
            .replace(/\[([^\]]+)\]\(([^)]+)\)/g, (match, text, url) => {
                if (url.includes('youtube.com')) {
                    return `<a href="${url}" target="_blank" class="text-green-600 hover:text-green-800">
                        <i class="fab fa-youtube mr-1"></i>${text}
                    </a>`;
                }
                return `<a href="${url}" target="_blank" class="text-green-600 hover:text-green-800">
                    <i class="fas fa-external-link-alt mr-1"></i>${text}
                </a>`;
            })
            // Format bold text
            .replace(/\*\*([^*]+)\*\*/g, '<strong class="font-semibold">$1</strong>')
            // Format italic text
            .replace(/\*([^*]+)\*/g, '<em class="italic">$1</em>')
            // Format location references
            .replace(/Location Example:/g, '<i class="fas fa-map-marker-alt text-green-600 mr-1"></i>Location:')
            // Format ingredient names
            .replace(/(\w+)\s*\(([^)]+)\)/g, '<span class="font-medium">$1</span> <span class="text-gray-600">($2)</span>');
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
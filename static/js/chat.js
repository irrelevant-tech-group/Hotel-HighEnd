// Global variables
let guestData = {};
let isFirstMessage = true;

// Initialize chat
function initChat(guest) {
    guestData = guest;
    
    // Set up event listeners
    setupEventListeners();
    
    // Add welcome message (system will send the first message)
    sendAutomaticMessage();
}

// Set up event listeners
function setupEventListeners() {
    // Message form submission
    const messageForm = document.getElementById('message-form');
    messageForm.addEventListener('submit', handleMessageSubmit);
    
    // Suggestion buttons
    const suggestionBtns = document.querySelectorAll('.suggestion-btn');
    suggestionBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const message = btn.textContent;
            document.getElementById('message-input').value = message;
            messageForm.dispatchEvent(new Event('submit'));
        });
    });
    
    // Scroll to bottom when new messages arrive
    const messagesContainer = document.getElementById('messages');
    const observer = new MutationObserver(() => {
        scrollToBottom();
    });
    observer.observe(messagesContainer, { childList: true });
}

// Handle message form submission
async function handleMessageSubmit(e) {
    e.preventDefault();
    
    const messageInput = document.getElementById('message-input');
    const message = messageInput.value.trim();
    
    if (!message) return;
    
    // Add user message to chat
    addMessageToChat(message, 'user');
    
    // Clear input
    messageInput.value = '';
    
    try {
        // Show typing indicator
        addTypingIndicator();
        
        // Send message to server
        const response = await axios.post('/api/send-message', {
            guest_id: guestData.guestId,
            message: message
        });
        
        // Remove typing indicator
        removeTypingIndicator();
        
        if (response.data.success) {
            // Add assistant's response to chat
            addMessageToChat(response.data.response, 'assistant');
        } else {
            // Show error
            addErrorMessage(response.data.error || 'Ocurrió un error al procesar tu mensaje');
        }
    } catch (error) {
        // Remove typing indicator
        removeTypingIndicator();
        
        console.error('Error sending message:', error);
        addErrorMessage('No pude enviar tu mensaje. Por favor intenta de nuevo.');
    }
}

// Add message to chat
function addMessageToChat(message, sender) {
    const messagesContainer = document.getElementById('messages');
    
    // Create message element
    const messageElement = document.createElement('div');
    messageElement.className = `message ${sender}-message mb-3`;
    
    // Create message content
    const contentElement = document.createElement('div');
    contentElement.className = sender === 'user' ? 'message-content bg-secondary text-light p-3 rounded-3' : 'message-content bg-dark border border-info p-3 rounded-3';
    
    // Parse markdown in assistant messages
    if (sender === 'assistant') {
        contentElement.innerHTML = marked.parse(message);
    } else {
        contentElement.textContent = message;
    }
    
    // Add avatar for assistant (could be an icon or initial)
    if (sender === 'assistant') {
        const avatarElement = document.createElement('div');
        avatarElement.className = 'avatar bg-info text-dark rounded-circle d-flex align-items-center justify-content-center me-2';
        avatarElement.innerHTML = 'L'; // L for Lina
        
        const messageWrapper = document.createElement('div');
        messageWrapper.className = 'd-flex align-items-start';
        messageWrapper.appendChild(avatarElement);
        messageWrapper.appendChild(contentElement);
        messageElement.appendChild(messageWrapper);
    } else {
        messageElement.appendChild(contentElement);
    }
    
    // Add message to container
    messagesContainer.appendChild(messageElement);
    
    // Scroll to bottom
    scrollToBottom();
}

// Add error message
function addErrorMessage(error) {
    const messagesContainer = document.getElementById('messages');
    
    // Create error element
    const errorElement = document.createElement('div');
    errorElement.className = 'alert alert-danger mt-3';
    errorElement.textContent = error;
    
    // Add error to container
    messagesContainer.appendChild(errorElement);
    
    // Scroll to bottom
    scrollToBottom();
}

// Add typing indicator
function addTypingIndicator() {
    const messagesContainer = document.getElementById('messages');
    
    // Check if typing indicator already exists
    if (document.getElementById('typing-indicator')) return;
    
    // Create typing indicator
    const typingElement = document.createElement('div');
    typingElement.id = 'typing-indicator';
    typingElement.className = 'message assistant-message mb-3';
    
    const avatarElement = document.createElement('div');
    avatarElement.className = 'avatar bg-info text-dark rounded-circle d-flex align-items-center justify-content-center me-2';
    avatarElement.innerHTML = 'L'; // L for Lina
    
    const contentElement = document.createElement('div');
    contentElement.className = 'message-content bg-dark border border-info p-3 rounded-3';
    contentElement.innerHTML = '<div class="typing-indicator"><span></span><span></span><span></span></div>';
    
    const messageWrapper = document.createElement('div');
    messageWrapper.className = 'd-flex align-items-start';
    messageWrapper.appendChild(avatarElement);
    messageWrapper.appendChild(contentElement);
    
    typingElement.appendChild(messageWrapper);
    
    // Add typing indicator to container
    messagesContainer.appendChild(typingElement);
    
    // Scroll to bottom
    scrollToBottom();
}

// Remove typing indicator
function removeTypingIndicator() {
    const typingIndicator = document.getElementById('typing-indicator');
    if (typingIndicator) {
        typingIndicator.remove();
    }
}

// Scroll to bottom of chat
function scrollToBottom() {
    const chatContainer = document.getElementById('chat-container');
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

// Send automatic welcome message
async function sendAutomaticMessage() {
    if (!isFirstMessage) return;
    
    try {
        // Show typing indicator
        addTypingIndicator();
        
        // Get welcome message from server
        const response = await axios.post('/api/send-message', {
            guest_id: guestData.guestId,
            message: 'Hola'  // This triggers the welcome flow
        });
        
        // Remove typing indicator
        removeTypingIndicator();
        
        if (response.data.success) {
            // Add assistant's response to chat
            addMessageToChat(response.data.response, 'assistant');
            isFirstMessage = false;
        } else {
            // Show error
            addErrorMessage('No pude cargar el mensaje de bienvenida. Por favor recarga la página.');
        }
    } catch (error) {
        // Remove typing indicator
        removeTypingIndicator();
        
        console.error('Error getting welcome message:', error);
        addErrorMessage('No pude cargar el mensaje de bienvenida. Por favor recarga la página.');
    }
}

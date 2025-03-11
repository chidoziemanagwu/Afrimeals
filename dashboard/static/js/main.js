// dashboard/static/js/main.js

// Toast Notification System
class ToastNotification {
    constructor() {
        this.container = document.getElementById('toast-container') || this.createContainer();
        this.duration = 5000; // Toast display duration in ms
    }

    createContainer() {
        const container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'position-fixed bottom-0 end-0 p-3';
        container.setAttribute('aria-live', 'polite');
        document.body.appendChild(container);
        return container;
    }

    show(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast show toast-${type}`;
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');
        
        toast.innerHTML = `
            <div class="toast-header">
                <strong class="me-auto">${type.charAt(0).toUpperCase() + type.slice(1)}</strong>
                <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        `;
        
        // Add close button functionality
        toast.querySelector('.btn-close').addEventListener('click', () => {
            toast.remove();
        });
        
        this.container.appendChild(toast);
        
        // Auto-remove toast after duration
        setTimeout(() => {
            toast.remove();
        }, this.duration);
        
        return toast;
    }
    
    success(message) {
        return this.show(message, 'success');
    }
    
    error(message) {
        return this.show(message, 'danger');
    }
    
    warning(message) {
        return this.show(message, 'warning');
    }
    
    info(message) {
        return this.show(message, 'info');
    }
}

// Task Status Checker
class TaskStatusChecker {
    constructor(taskId, onComplete, onError, checkInterval = 2000) {
        this.taskId = taskId;
        this.onComplete = onComplete;
        this.onError = onError;
        this.checkInterval = checkInterval;
        this.intervalId = null;
        this.toast = new ToastNotification();
    }

    start() {
        this.checkStatus();
        this.intervalId = setInterval(() => this.checkStatus(), this.checkInterval);
    }

    stop() {
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
        }
    }

    async checkStatus() {
        try {
            const response = await fetch(`/task-status/${this.taskId}/`);
            
            if (!response.ok) {
                throw new Error(`Server returned ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();

            if (data.status !== 'processing') {
                this.stop();
                if (data.success) {
                    this.onComplete(data);
                } else {
                    const errorMsg = data.error || 'An unknown error occurred';
                    this.onError(errorMsg);
                    this.toast.error(errorMsg);
                }
            }
        } catch (error) {
            this.stop();
            const errorMsg = 'Error checking task status: ' + error.message;
            this.onError(errorMsg);
            this.toast.error(errorMsg);
        }
    }
}

// Meal Generator Handler
class MealGeneratorHandler {
    constructor() {
        this.form = document.getElementById('mealPlanForm');
        this.loadingElement = document.getElementById('loading');
        this.resultsElement = document.getElementById('results');
        this.toast = new ToastNotification();
        this.setupEventListeners();
    }

    setupEventListeners() {
        if (this.form) {
            this.form.addEventListener('submit', (e) => this.handleSubmit(e));
            
            // Add keyboard navigation support
            const submitButton = this.form.querySelector('button[type="submit"]');
            if (submitButton) {
                submitButton.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter') {
                        e.preventDefault();
                        submitButton.click();
                    }
                });
            }
        }
    }

    async handleSubmit(e) {
        e.preventDefault();
        this.showLoading();

        try {
            const formData = new FormData(this.form);
            const response = await fetch('/meal-generator/', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                }
            });

            if (!response.ok) {
                throw new Error(`Server returned ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();

            if (data.requires_upgrade) {
                this.hideLoading();
                this.toast.warning(data.message || 'This feature requires a subscription upgrade.');
                return;
            }

            if (data.task_id) {
                new TaskStatusChecker(
                    data.task_id,
                    (result) => this.handleSuccess(result),
                    (error) => this.handleError(error)
                ).start();
            } else {
                this.handleSuccess(data);
            }
        } catch (error) {
            this.handleError('Error submitting form: ' + error.message);
        }
    }

    showLoading() {
        if (this.form) this.form.classList.add('hidden');
        if (this.loadingElement) {
            this.loadingElement.classList.remove('hidden');
            this.loadingElement.setAttribute('aria-busy', 'true');
            this.loadingElement.setAttribute('aria-label', 'Generating your meal plan, please wait');
        }
    }

    hideLoading() {
        if (this.loadingElement) {
            this.loadingElement.classList.add('hidden');
            this.loadingElement.setAttribute('aria-busy', 'false');
        }
        if (this.form) this.form.classList.remove('hidden');
    }

    handleSuccess(data) {
        this.hideLoading();
        if (this.resultsElement) {
            this.resultsElement.classList.remove('hidden');
            this.updateUI(data);
        }
        this.toast.success('Your meal plan was successfully generated!');
    }

    handleError(error) {
        this.hideLoading();
        this.toast.error(error);
    }

    updateUI(data) {
        if (!this.resultsElement) return;
        
        // Clear previous results
        this.resultsElement.innerHTML = '';
        
        if (data.meal_plan && data.meal_plan.length > 0) {
            // Create meal plan section
            const mealPlanSection = document.createElement('div');
            mealPlanSection.className = 'meal-plan-section mb-4';
            mealPlanSection.innerHTML = '<h3>Your Meal Plan</h3>';
            
            // Create meal plan table
            const table = document.createElement('table');
            table.className = 'table table-bordered';
            table.innerHTML = `
                <thead>
                    <tr>
                        <th>Day</th>
                        <th>Breakfast</th>
                        <th>Lunch</th>
                        ${data.meal_plan[0].meals.snack ? '<th>Snack</th>' : ''}
                        <th>Dinner</th>
                    </tr>
                </thead>
                <tbody></tbody>
            `;
            
            // Add rows for each day
            const tbody = table.querySelector('tbody');
            data.meal_plan.forEach(day => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${day.day}</td>
                    <td>${day.meals.breakfast}</td>
                    <td>${day.meals.lunch}</td>
                    ${day.meals.snack ? `<td>${day.meals.snack}</td>` : ''}
                    <td>${day.meals.dinner}</td>
                `;
                tbody.appendChild(row);
            });
            
            mealPlanSection.appendChild(table);
            this.resultsElement.appendChild(mealPlanSection);
            
            // Create grocery list section
            if (data.grocery_list && data.grocery_list.length > 0) {
                const grocerySection = document.createElement('div');
                grocerySection.className = 'grocery-list-section';
                grocerySection.innerHTML = '<h3>Grocery List</h3>';
                
                const list = document.createElement('ul');
                list.className = 'list-group';
                
                data.grocery_list.forEach(item => {
                    const listItem = document.createElement('li');
                    listItem.className = 'list-group-item';
                    listItem.textContent = item;
                    list.appendChild(listItem);
                });
                
                grocerySection.appendChild(list);
                this.resultsElement.appendChild(grocerySection);
            }
        } else {
            this.resultsElement.innerHTML = '<div class="alert alert-warning">No meal plan data available.</div>';
        }
    }
}

// PDF Export Handler
class PDFExportHandler {
    constructor() {
        this.toast = new ToastNotification();
        this.setupEventListeners();
    }

    setupEventListeners() {
        document.querySelectorAll('.export-pdf-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.handleExport(e));
            // Add keyboard support
            btn.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    btn.click();
                }
            });
        });
    }

    async handleExport(e) {
        const button = e.currentTarget;
        const mealPlanId = button.dataset.mealplanId;
        const loadingText = button.dataset.loadingText || 'Generating PDF...';
        const originalText = button.innerText;
        
        // Visual feedback for users
        const spinner = document.createElement('span');
        spinner.className = 'spinner-border spinner-border-sm me-2';
        spinner.setAttribute('role', 'status');
        spinner.setAttribute('aria-hidden', 'true');

        try {
            button.innerHTML = '';
            button.appendChild(spinner);
            button.insertAdjacentText('beforeend', ` ${loadingText}`);
            button.disabled = true;
            button.setAttribute('aria-busy', 'true');

            const response = await fetch(`/meal-plans/${mealPlanId}/export/`);
            
            if (!response.ok) {
                throw new Error(`Server returned ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();

            if (data.task_id) {
                new TaskStatusChecker(
                    data.task_id,
                    (result) => this.handlePDFSuccess(result, button, originalText),
                    (error) => this.handlePDFError(error, button, originalText)
                ).start();
            } else if (data.pdf_data) {
                this.handlePDFSuccess(data, button, originalText);
            } else {
                throw new Error('Invalid response from server');
            }
        } catch (error) {
            this.handlePDFError('Error generating PDF: ' + error.message, button, originalText);
        }
    }

    handlePDFSuccess(result, button, originalText) {
        // Reset button
        if (button) {
            button.innerText = originalText;
            button.disabled = false;
            button.setAttribute('aria-busy', 'false');
        }
        
        // Create a blob from the PDF data
        const blob = new Blob([this.base64ToArrayBuffer(result.pdf_data)], { type: 'application/pdf' });
        const url = window.URL.createObjectURL(blob);
        
        // Create and click a temporary download link
        const link = document.createElement('a');
        link.href = url;
        link.download = result.filename || 'meal_plan.pdf';
        link.setAttribute('aria-label', 'Download your meal plan PDF');
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
        
        this.toast.success('PDF successfully generated and downloaded!');
    }

    handlePDFError(error, button, originalText) {
        if (button) {
            button.innerText = originalText;
            button.disabled = false;
            button.setAttribute('aria-busy', 'false');
        }
        this.toast.error(error);
    }

    base64ToArrayBuffer(base64) {
        const binaryString = window.atob(base64);
        const bytes = new Uint8Array(binaryString.length);
        for (let i = 0; i < binaryString.length; i++) {
            bytes[i] = binaryString.charCodeAt(i);
        }
        return bytes.buffer;
    }
}

// Recipe Processing Handler
class RecipeProcessingHandler {
    constructor() {
        this.toast = new ToastNotification();
        this.setupEventListeners();
    }

    setupEventListeners() {
        document.querySelectorAll('.process-recipe-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.handleProcessing(e));
            // Add keyboard support
            btn.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    btn.click();
                }
            });
        });
    }

    async handleProcessing(e) {
        const button = e.currentTarget;
        const recipeId = button.dataset.recipeId;
        const loadingText = button.dataset.loadingText || 'Processing...';
        const originalText = button.innerText;
        
        // Visual feedback for users
        const spinner = document.createElement('span');
        spinner.className = 'spinner-border spinner-border-sm me-2';
        spinner.setAttribute('role', 'status');
        spinner.setAttribute('aria-hidden', 'true');

        try {
            button.innerHTML = '';
            button.appendChild(spinner);
            button.insertAdjacentText('beforeend', ` ${loadingText}`);
            button.disabled = true;
            button.setAttribute('aria-busy', 'true');

            const response = await fetch(`/recipes/${recipeId}/process/`);
            
            if (!response.ok) {
                throw new Error(`Server returned ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();

            if (data.task_id) {
                new TaskStatusChecker(
                    data.task_id,
                    (result) => this.handleSuccess(result, button, originalText),
                    (error) => this.handleError(error, button, originalText)
                ).start();
            } else {
                this.handleSuccess(data, button, originalText);
            }
        } catch (error) {
            this.handleError('Error processing recipe: ' + error.message, button, originalText);
        }
    }

    handleSuccess(result, button, originalText) {
        if (button) {
            button.innerText = originalText;
            button.disabled = false;
            button.setAttribute('aria-busy', 'false');
        }
        
        this.toast.success('Recipe successfully processed!');
        
        // Update UI with processed recipe data if needed
        if (result.recipe_data) {
            this.updateRecipeUI(result.recipe_data);
        }
    }

    handleError(error, button, originalText) {
        if (button) {
            button.innerText = originalText;
            button.disabled = false;
            button.setAttribute('aria-busy', 'false');
        }
        this.toast.error(error);
    }
    
    updateRecipeUI(recipeData) {
        // Find recipe container by ID
        const container = document.getElementById(`recipe-${recipeData.id}`);
        if (!container) return;
        
        // Update recipe details
        const titleEl = container.querySelector('.recipe-title');
        if (titleEl) titleEl.textContent = recipeData.title;
        
        // Update ingredients list
        const ingredientsList = container.querySelector('.ingredients-list');
        if (ingredientsList && recipeData.ingredients) {
            ingredientsList.innerHTML = '';
            recipeData.ingredients.forEach(ingredient => {
                const li = document.createElement('li');
                li.textContent = ingredient;
                ingredientsList.appendChild(li);
            });
        }
        
        // Update instructions
        const instructionsEl = container.querySelector('.instructions');
        if (instructionsEl && recipeData.instructions) {
            instructionsEl.innerHTML = '';
            recipeData.instructions.forEach(step => {
                const p = document.createElement('p');
                p.textContent = step;
                instructionsEl.appendChild(p);
            });
        }
    }
}

// Add necessary CSS for toast notifications
function addToastStyles() {
    if (!document.getElementById('toast-styles')) {
        const style = document.createElement('style');
        style.id = 'toast-styles';
        style.textContent = `
            #toast-container {
                position: fixed;
                bottom: 20px;
                right: 20px;
                z-index: 9999;
            }
            .toast {
                min-width: 250px;
                margin-bottom: 10px;
                background-color: white;
                border-radius: 4px;
                box-shadow: 0 0 10px rgba(0,0,0,0.2);
                animation: toast-in-right 0.7s;
            }
            .toast-success .toast-header {
                background-color: #d4edda;
                color: #155724;
            }
            .toast-danger .toast-header {
                background-color: #f8d7da;
                color: #721c24;
            }
            .toast-warning .toast-header {
                background-color: #fff3cd;
                color: #856404;
            }
            .toast-info .toast-header {
                background-color: #d1ecf1;
                color: #0c5460;
            }
            @keyframes toast-in-right {
                from { transform: translateX(100%); }
                to { transform: translateX(0); }
            }
            .hidden {
                display: none !important;
            }
            [aria-busy="true"] {
                cursor: wait;
            }
        `;
        document.head.appendChild(style);
    }
}

// Initialize handlers when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    addToastStyles();
    new MealGeneratorHandler();
    new PDFExportHandler();
    new RecipeProcessingHandler();
});
// dashboard/static/js/main.js

// Task Status Checker
class TaskStatusChecker {
    constructor(taskId, onComplete, onError, checkInterval = 2000) {
        this.taskId = taskId;
        this.onComplete = onComplete;
        this.onError = onError;
        this.checkInterval = checkInterval;
        this.intervalId = null;
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
            const data = await response.json();

            if (data.status !== 'processing') {
                this.stop();
                if (data.success) {
                    this.onComplete(data);
                } else {
                    this.onError(data.error);
                }
            }
        } catch (error) {
            this.stop();
            this.onError('Error checking task status');
        }
    }
}

// Meal Generator Handler
class MealGeneratorHandler {
    constructor() {
        this.form = document.getElementById('mealPlanForm');
        this.loadingElement = document.getElementById('loading');
        this.resultsElement = document.getElementById('results');
        this.setupEventListeners();
    }

    setupEventListeners() {
        this.form.addEventListener('submit', (e) => this.handleSubmit(e));
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

            const data = await response.json();

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
            this.handleError('Error submitting form');
        }
    }

    showLoading() {
        this.form.classList.add('hidden');
        this.loadingElement.classList.remove('hidden');
    }

    hideLoading() {
        this.loadingElement.classList.add('hidden');
        this.form.classList.remove('hidden');
    }

    handleSuccess(data) {
        this.hideLoading();
        this.resultsElement.classList.remove('hidden');
        this.updateUI(data);
    }

    handleError(error) {
        this.hideLoading();
        alert(error);
    }

    updateUI(data) {
        // Update meal plan table and grocery list
        // Implementation depends on your specific UI requirements
    }
}

// PDF Export Handler
class PDFExportHandler {
    constructor() {
        this.setupEventListeners();
    }

    setupEventListeners() {
        document.querySelectorAll('.export-pdf-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.handleExport(e));
        });
    }

    async handleExport(e) {
        const mealPlanId = e.target.dataset.mealplanId;
        const loadingText = e.target.dataset.loadingText || 'Generating PDF...';
        const originalText = e.target.innerText;

        try {
            e.target.innerText = loadingText;
            e.target.disabled = true;

            const response = await fetch(`/meal-plans/${mealPlanId}/export/`);
            const data = await response.json();

            if (data.task_id) {
                new TaskStatusChecker(
                    data.task_id,
                    (result) => this.handlePDFSuccess(result),
                    (error) => this.handlePDFError(error, e.target, originalText)
                ).start();
            }
        } catch (error) {
            this.handlePDFError('Error generating PDF', e.target, originalText);
        }
    }

    handlePDFSuccess(result) {
        // Create a blob from the PDF data
        const blob = new Blob([this.base64ToArrayBuffer(result.pdf_data)], { type: 'application/pdf' });
        const url = window.URL.createObjectURL(blob);
        
        // Create and click a temporary download link
        const link = document.createElement('a');
        link.href = url;
        link.download = result.filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
    }

    handlePDFError(error, button, originalText) {
        alert(error);
        if (button) {
            button.innerText = originalText;
            button.disabled = false;
        }
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
        this.setupEventListeners();
    }

    setupEventListeners() {
        document.querySelectorAll('.process-recipe-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.handleProcessing(e));
        });
    }

    async handleProcessing(e) {
        const recipeId = e.target.dataset.recipeId;
        const loadingText = e.target.dataset.loadingText || 'Processing...';
        const originalText = e.target.innerText;

        try {
            e.target.innerText = loadingText;
            e.target.disabled = true;

            const response = await fetch(`/recipes/${recipeId}/process/`);
            const data = await response.json();

            if (data.task_id) {
                new TaskStatusChecker(
                    data.task_id,
                    (result) => this.handleSuccess(result, e.target, originalText),
                    (error) => this.handleError(error, e.target, originalText)
                ).start();
            }
        } catch (error) {
            this.handleError('Error processing recipe', e.target, originalText);
        }
    }

    handleSuccess(result, button, originalText) {
        // Update UI with processed recipe data
        button.innerText = originalText;
        button.disabled = false;
    }

    handleError(error, button, originalText) {
        alert(error);
        button.innerText = originalText;
        button.disabled = false;
    }
}

// Initialize handlers when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new MealGeneratorHandler();
    new PDFExportHandler();
    new RecipeProcessingHandler();
});
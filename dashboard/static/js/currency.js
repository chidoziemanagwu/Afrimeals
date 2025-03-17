class CurrencyConverter {
    constructor() {
        // Initialize state
        this.currentCurrency = 'GBP';
        this.rates = null;
        
        // UI elements
        this.priceElements = document.querySelectorAll('[data-base-price]');
        this.currencySelect = document.getElementById('currency-select');
        this.notification = document.getElementById('notification');
        
        // Currency settings
        this.currencies = {
            'GBP': { symbol: '£', locale: 'en-GB' },
            'USD': { symbol: '$', locale: 'en-US' },
            'EUR': { symbol: '€', locale: 'de-DE' },
            'NGN': { symbol: '₦', locale: 'en-NG' }
        };

        this.init();
    }

    async init() {
        try {
            // Get exchange rates
            await this.fetchRates();
            
            // Setup event listeners
            if (this.currencySelect) {
                this.currencySelect.addEventListener('change', (e) => {
                    this.updatePrices(e.target.value);
                });
            }

            // Check for saved preference
            const savedCurrency = localStorage.getItem('preferred_currency');
            if (savedCurrency && this.currencies[savedCurrency]) {
                this.updatePrices(savedCurrency);
                if (this.currencySelect) {
                    this.currencySelect.value = savedCurrency;
                }
            }
        } catch (error) {
            console.error('Currency initialization error:', error);
            this.showNotification('Using default currency settings', 'error');
        }
    }

    async fetchRates() {
        try {
            const response = await fetch('/api/exchange-rates/');
            if (!response.ok) throw new Error('Failed to fetch exchange rates');
            
            const data = await response.json();
            this.rates = data.data;
        } catch (error) {
            console.error('Exchange rates error:', error);
            this.showNotification('Using estimated exchange rates', 'warning');
        }
    }

    updatePrices(newCurrency) {
        if (!this.currencies[newCurrency]) return;

        const rate = this.rates?.[newCurrency] || 1;
        
        this.priceElements.forEach(element => {
            const basePrice = parseFloat(element.dataset.basePrice);
            const convertedPrice = basePrice * rate;
            element.textContent = this.formatPrice(convertedPrice, newCurrency);
        });

        this.currentCurrency = newCurrency;
        localStorage.setItem('preferred_currency', newCurrency);
        
        this.showNotification(`Prices updated to ${newCurrency}`);
    }

    formatPrice(amount, currency) {
        try {
            return new Intl.NumberFormat(this.currencies[currency].locale, {
                style: 'currency',
                currency: currency,
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            }).format(amount);
        } catch (error) {
            return `${this.currencies[currency].symbol}${amount.toFixed(2)}`;
        }
    }

    showNotification(message, type = 'info') {
        if (!this.notification) return;

        this.notification.textContent = message;
        this.notification.className = `notification ${type}`;
        this.notification.style.display = 'block';

        setTimeout(() => {
            this.notification.style.display = 'none';
        }, 3000);
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    new CurrencyConverter();
});
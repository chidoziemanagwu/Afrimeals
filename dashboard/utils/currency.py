# dashboard/utils/currency.py

import requests
from django.conf import settings
from django.core.cache import cache
from typing import Dict, Any

class CurrencyManager:
    CACHE_KEY = 'currency_rates'
    CACHE_TIMEOUT = 3600  # 1 hour

    PRICES = {
        'pay_once': {'GBP': 5.99, 'USD': 7.99, 'EUR': 6.99, 'NGN': 3500},
        'weekly': {'GBP': 12.99, 'USD': 16.99, 'EUR': 14.99, 'NGN': 7500},
    }

    SYMBOLS = {
        'GBP': '£',
        'USD': '$',
        'EUR': '€',
        'NGN': '₦'
    }

    @classmethod
    def get_user_currency(cls, request) -> str:
        """Get user's currency based on their location or session"""
        # Check session first
        if 'user_currency' in request.session:
            return request.session['user_currency']

        try:
            # Use IP-based geolocation
            response = requests.get('https://ipapi.co/json/', timeout=5)
            data = response.json()
            currency = data.get('currency', 'GBP')

            # Store in session
            request.session['user_currency'] = currency
            return currency
        except Exception as e:
            # Log the error if needed
            print(f"Currency detection error: {str(e)}")
            return 'GBP'

    @classmethod
    def get_exchange_rates(cls) -> Dict[str, float]:
        """Get current exchange rates from cache or API"""
        rates = cache.get(cls.CACHE_KEY)

        if rates is None:
            try:
                api_key = settings.EXCHANGE_RATE_API_KEY
                response = requests.get(
                    f'https://api.exchangerate-api.com/v4/latest/GBP',
                    timeout=5
                )
                rates = response.json()['rates']
                cache.set(cls.CACHE_KEY, rates, cls.CACHE_TIMEOUT)
            except Exception as e:
                # Log the error if needed
                print(f"Exchange rate API error: {str(e)}")
                # Fallback rates
                rates = {'GBP': 1, 'USD': 1.25, 'EUR': 1.15, 'NGN': 583}

        return rates

    @classmethod
    def get_price_data(cls, currency: str) -> Dict[str, Any]:
        """Get complete price data including symbols and formatted prices"""
        # Use predefined prices if available
        if currency in cls.PRICES['pay_once']:
            prices = {
                'pay_once': cls.PRICES['pay_once'][currency],
                'weekly': cls.PRICES['weekly'][currency]
            }
        else:
            # Convert from GBP if currency not in predefined prices
            rates = cls.get_exchange_rates()
            rate = rates.get(currency, 1)
            prices = {
                'pay_once': round(cls.PRICES['pay_once']['GBP'] * rate, 2),
                'weekly': round(cls.PRICES['weekly']['GBP'] * rate, 2)
            }

        return {
            'currency': currency,
            'symbol': cls.SYMBOLS.get(currency, currency),
            'pay_once_price': prices['pay_once'],
            'weekly_price': prices['weekly'],
            'formatted_pay_once': f"{cls.SYMBOLS.get(currency, currency)}{prices['pay_once']}",
            'formatted_weekly': f"{cls.SYMBOLS.get(currency, currency)}{prices['weekly']}"
        }

    @classmethod
    def get_supported_currencies(cls) -> Dict[str, str]:
        """Get dictionary of supported currencies and their symbols"""
        return cls.SYMBOLS
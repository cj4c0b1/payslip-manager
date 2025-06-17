"""
Exchange rate service for fetching BRL to EUR exchange rates from Frankfurter API.
"""

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Dict, Optional
import requests
from functools import lru_cache

from src.config.exchange_rate_config import ExchangeRateConfig

logger = logging.getLogger(__name__)

class ExchangeRateServiceError(Exception):
    """Base exception for exchange rate service errors."""
    pass

class ExchangeRateService:
    """Service for fetching and managing exchange rates using Frankfurter API."""
    
    def __init__(self, config=None):
        """Initialize the exchange rate service."""
        self.config = config or ExchangeRateConfig()
        self.session = requests.Session()
        
    def get_rate(self, target_date: date = None) -> Dict:
        """Get the exchange rate for a specific date."""
        try:
            if target_date is None:
                return self._get_latest_rate()
            return self._get_historical_rate(target_date)
        except requests.RequestException as e:
            logger.error(f"Failed to fetch exchange rate: {e}")
            raise ExchangeRateServiceError(f"Failed to fetch exchange rate: {e}") from e
    
    @lru_cache(maxsize=1000)
    def _get_latest_rate(self) -> Dict:
        """Get the latest exchange rate."""
        url = f"{self.config.API_BASE_URL}/latest"
        params = {
            'from': self.config.BASE_CURRENCY,
            'to': self.config.TARGET_CURRENCY
        }
        
        response = self.session.get(
            url,
            params=params,
            timeout=self.config.REQUEST_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
        
        return {
            'date': datetime.strptime(data['date'], '%Y-%m-%d').date(),
            'rate': Decimal(str(data['rates'][self.config.TARGET_CURRENCY])),
            'base': data['base'],
            'target': self.config.TARGET_CURRENCY
        }
    
    @lru_cache(maxsize=1000)
    def _get_historical_rate(self, target_date: date) -> Dict:
        """Get historical exchange rate for a specific date."""
        url = f"{self.config.API_BASE_URL}/{target_date}"
        params = {
            'from': self.config.BASE_CURRENCY,
            'to': self.config.TARGET_CURRENCY
        }
        
        response = self.session.get(
            url,
            params=params,
            timeout=self.config.REQUEST_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
        
        return {
            'date': datetime.strptime(data['date'], '%Y-%m-%d').date(),
            'rate': Decimal(str(data['rates'][self.config.TARGET_CURRENCY])),
            'base': data['base'],
            'target': self.config.TARGET_CURRENCY
        }
    
    def convert_amount(self, amount: float, from_currency: str, to_currency: str, 
                      target_date: date = None) -> Dict:
        """Convert an amount from one currency to another."""
        if from_currency == to_currency:
            return {
                'amount': Decimal(str(amount)),
                'converted_amount': Decimal(str(amount)),
                'rate': Decimal('1.0'),
                'date': target_date or date.today(),
                'from_currency': from_currency,
                'to_currency': to_currency
            }
            
        if (from_currency == self.config.BASE_CURRENCY and 
            to_currency == self.config.TARGET_CURRENCY):
            rate_data = self.get_rate(target_date)
            converted = amount * rate_data['rate']
            return {
                'amount': Decimal(str(amount)),
                'converted_amount': converted.quantize(Decimal('0.01')),
                'rate': rate_data['rate'],
                'date': rate_data['date'],
                'from_currency': from_currency,
                'to_currency': to_currency
            }
        else:
            raise ValueError(
                f"Conversion from {from_currency} to {to_currency} not supported. "
                f"Only {self.config.BASE_CURRENCY} to {self.config.TARGET_CURRENCY} "
                "is supported."
            )
    
    def clear_cache(self) -> None:
        """Clear the LRU cache."""
        self._get_latest_rate.cache_clear()
        self._get_historical_rate.cache_clear()

# Singleton instance
exchange_rate_service = ExchangeRateService()

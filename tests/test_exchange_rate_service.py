"""Tests for the exchange rate service."""

import os
import sys
import unittest
from datetime import date
from unittest.mock import patch, Mock
from decimal import Decimal

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.services.exchange_rate_service import ExchangeRateService, ExchangeRateServiceError

class TestExchangeRateService(unittest.TestCase):
    """Test cases for the ExchangeRateService class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.service = ExchangeRateService()
        
    @patch('requests.Session.get')
    def test_get_latest_rate(self, mock_get):
        """Test getting the latest exchange rate."""
        # Mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            'amount': 1.0,
            'base': 'EUR',
            'date': '2023-06-17',
            'rates': {'BRL': 5.5}
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Test
        result = self.service.get_rate()
        
        # Assertions
        self.assertEqual(result['rate'], Decimal('5.5'))
        self.assertEqual(result['date'], date(2023, 6, 17))
        self.assertEqual(result['base'], 'EUR')
        self.assertEqual(result['target'], 'BRL')
        
        # Verify the API was called with the correct parameters
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        self.assertIn('params', kwargs)
        self.assertEqual(kwargs['params']['from'], 'EUR')
        self.assertEqual(kwargs['params']['to'], 'BRL')
    
    @patch('requests.Session.get')
    def test_convert_amount(self, mock_get):
        """Test converting an amount from EUR to BRL."""
        # Mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            'amount': 1.0,
            'base': 'EUR',
            'date': '2023-06-17',
            'rates': {'BRL': 5.5}
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Test
        result = self.service.convert_amount(100, 'EUR', 'BRL')
        
        # Assertions
        self.assertEqual(result['amount'], Decimal('100'))
        self.assertEqual(result['converted_amount'], Decimal('550.00'))
        self.assertEqual(result['rate'], Decimal('5.5'))
        self.assertEqual(result['date'], date(2023, 6, 17))
        self.assertEqual(result['from_currency'], 'EUR')
        self.assertEqual(result['to_currency'], 'BRL')

if __name__ == '__main__':
    unittest.main()

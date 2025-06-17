#Frankfurter API
import requests
from datetime import datetime

def get_eur_brl_rate(date=None):
    """Get EUR to BRL exchange rate for a specific date or latest"""
    base_url = "https://api.frankfurter.app"
    
    if date:
        # Historical rate for specific date (format: YYYY-MM-DD)
        url = f"{base_url}/{date}?from=EUR&to=BRL"
    else:
        # Latest rate
        url = f"{base_url}/latest?from=EUR&to=BRL"
    
    response = requests.get(url)
    data = response.json()
    
    return {
        'date': data['date'],
        'rate': data['rates']['BRL'],
        'base': 'EUR',
        'target': 'BRL'
    }

def convert_eur_to_brl(amount, date=None):
    """Convert EUR amount to BRL"""
    rate_data = get_eur_brl_rate(date)
    converted_amount = amount * rate_data['rate']
    
    return {
        'date': rate_data['date'],
        'eur_amount': amount,
        'brl_amount': round(converted_amount, 2),
        'exchange_rate': rate_data['rate']
    }

# Usage examples
latest_rate = get_eur_brl_rate()
print(f"Latest EUR/BRL rate: {latest_rate['rate']}")

historical_rate = get_eur_brl_rate("2024-01-15")
print(f"Historical rate: {historical_rate['rate']}")

conversion = convert_eur_to_brl(100, "2024-01-15")
print(f"100 EUR = {conversion['brl_amount']} BRL")

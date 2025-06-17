"""
Currency formatting and conversion utilities.
"""
from decimal import Decimal
from typing import Optional, Union

def format_currency(
    amount: Union[Decimal, float, int, None], 
    currency: str = 'BRL',
    exchange_rate: Optional[Union[Decimal, float]] = None
) -> str:
    """
    Format a monetary amount according to the specified currency.
    
    Args:
        amount: The amount in the base currency (BRL)
        currency: The target currency to display ('BRL' or 'EUR')
        exchange_rate: The exchange rate (BRL to EUR) to use for conversion
        
    Returns:
        Formatted currency string with appropriate symbol and formatting
    """
    if amount is None:
        return "N/A"
    
    # Convert to Decimal if not already
    amount = Decimal(str(amount)) if not isinstance(amount, Decimal) else amount
    
    if currency.upper() == 'EUR':
        if exchange_rate is None:
            return "N/A (No exchange rate)"
            
        # Convert amount using the provided exchange rate
        exchange_rate = Decimal(str(exchange_rate)) if not isinstance(exchange_rate, Decimal) else exchange_rate
        value = amount * exchange_rate
        
        # Format with European-style number formatting: 1.234,56
        formatted_value = f"{value:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        return f"€ {formatted_value}"
    else:
        # Default to BRL formatting: 1.234,56
        formatted_amount = f"{amount:,.2f}".replace('.', 'X').replace(',', '.').replace('X', ',')
        return f"R$ {formatted_amount}"

def get_currency_symbol(currency: str = 'BRL') -> str:
    """
    Get the currency symbol for display.
    
    Args:
        currency: Currency code ('BRL' or 'EUR')
        
    Returns:
        Currency symbol (R$ or €)
    """
    return 'R$' if currency.upper() == 'BRL' else '€'

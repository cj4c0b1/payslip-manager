from datetime import timedelta

class ExchangeRateConfig:
    """Configuration for exchange rate service."""
    API_BASE_URL = "https://api.frankfurter.app"
    REQUEST_TIMEOUT = 10
    CACHE_TTL = timedelta(days=1)
    MAX_CACHE_SIZE = 1000
    BASE_CURRENCY = "BRL"
    TARGET_CURRENCY = "EUR"

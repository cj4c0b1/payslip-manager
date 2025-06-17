# Payslip Management System

[![Security](https://img.shields.io/badge/security-enabled-brightgreen)](SECURITY.md)
[![CodeQL](https://github.com/yourusername/payslip-manager/actions/workflows/codeql-analysis.yml/badge.svg)](https://github.com/yourusername/payslip-manager/actions/workflows/codeql-analysis.yml)

A Streamlit-based application for managing and analyzing employee payslips in PDF format. The system allows users to upload, store, and visualize payslip data with various reporting capabilities.

A Streamlit-based application for managing and analyzing employee payslips in PDF format. The system allows users to upload, store, and visualize payslip data with various reporting capabilities.

## Features

- **PDF Processing**: Extract data from PDF payslips automatically
- **Data Storage**: Store all payslip information in an SQLite database
- **Dashboard**: View key metrics and visualizations
- **Reports**: Generate detailed reports on earnings and deductions
- **Export**: Export data in multiple formats (CSV, Excel, PDF)
- **Currency Conversion**: Automatic BRL to EUR conversion with historical rates
  - Real-time exchange rate lookups
  - Cached rates for performance
  - Historical rate tracking by payslip date
- **Secure Authentication**: Passwordless email-based authentication with magic links
  - No passwords to remember or manage
  - Single-use, time-limited login links
  - Automatic cleanup of expired tokens
  - Rate limiting for security
- **Role-Based Access Control**: Fine-grained permissions for different user roles
- **Audit Logging**: Track all authentication events and sensitive operations
- **Data Encryption**: Sensitive data encrypted at rest and in transit

## Security Features

This project implements several security measures to protect your data:

- **Security Policy**: Clear guidelines for reporting vulnerabilities ([SECURITY.md](SECURITY.md))
- **Dependency Scanning**: Automated monitoring for vulnerable dependencies
- **Code Analysis**: Static code analysis with CodeQL to detect security issues
- **Secret Scanning**: Automatic detection of exposed secrets in commits
- **Private Vulnerability Reporting**: Secure channel for reporting security issues
- **Regular Updates**: Dependencies are automatically kept up-to-date

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd payslip-manager
   ```

2. Create and activate a virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\activate
   ```

3. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

4. For better performance, install the Watchdog module:
   ```bash
   xcode-select --install  # Required for Watchdog on macOS
   pip install watchdog
   ```

## Usage

1. Start the Streamlit application:
   ```bash
   streamlit run main.py
   ```

2. Open your web browser and navigate to `http://localhost:8501`

3. Use the sidebar to navigate between different sections:
   - **Upload**: Upload and process new payslip PDFs
   - **View**: Browse and filter existing payslips
   - **Reports**: View analytics and export data

### Currency Conversion

Payslips in BRL are automatically converted to EUR using the exchange rate from the payslip's reference date. The converted amounts are displayed alongside the original values.

#### How It Works:
1. When a payslip is uploaded, the system:
   - Identifies the reference date
   - Fetches the historical exchange rate for that date
   - Stores the rate and converted amounts in the database

2. The exchange rate information is displayed in the payslip details view

3. Both original (BRL) and converted (EUR) amounts are shown in all relevant views

#### Manual Refresh
To refresh exchange rates for existing payslips:
1. Go to the payslip details
2. Click the "Refresh Exchange Rate" button
3. The system will fetch the latest rate for the payslip's reference date

> **Note**: Exchange rates are cached for 24 hours to reduce API calls. Manual refresh overrides the cache for specific payslips.

## Project Structure

```
payslip-manager/
├── src/
│   ├── __init__.py
│   ├── auth/                  # Authentication module
│   │   ├── __init__.py
│   │   ├── models.py          # Database models for auth
│   │   ├── schemas.py         # Pydantic schemas
│   │   ├── service.py         # Core auth logic
│   │   └── email_utils.py     # Email sending utilities
│   ├── database.py            # Database connection and session management
│   ├── models/                # SQLAlchemy models
│   │   ├── __init__.py
│   │   ├── base.py            # Base model and mixins
│   │   ├── employee.py        # Employee model
│   │   ├── payslip.py         # Payslip model
│   │   ├── earning.py         # Earning model
│   │   └── deduction.py       # Deduction model
│   └── security.py            # Security utilities
├── tests/                     # Test files
│   ├── __init__.py
│   ├── conftest.py            # Test configuration
│   └── test_auth.py           # Authentication tests
├── uploads/                   # Directory for uploaded PDFs
│   └── processed/             # Processed PDFs are moved here
├── data/                      # Data directory
│   └── payslips.db            # SQLite database
├── main.py                    # Main Streamlit application
├── requirements.txt           # Python dependencies
├── .env.example              # Example environment variables
└── README.md                 # This file
```

## Browser Compatibility

This application has been tested and works best with the following browsers:

- **Google Chrome** (Recommended)
  - Full support for all features including PDF viewing and downloading
  - Best performance and compatibility

- **Mozilla Firefox**
  - Full support for most features
  - PDF viewing and downloading works as expected

- **Safari**
  - Basic functionality works
  - Some PDF viewing features may be limited

- **Microsoft Edge**
  - Based on Chromium, so most features work well
  - PDF handling is generally good

> **Note**: The built-in browser in some IDEs (like Windsurf) may have limited PDF viewing/downloading capabilities. For the best experience, please use a standard web browser like Chrome or Firefox.

## Configuration

Create a `.env` file in the project root with the following variables:

```
# Database Configuration
DATABASE_URL=sqlite:///data/payslips.db
SECRET_KEY=your-secret-key-here

# Exchange Rate Configuration (optional)
EXCHANGE_RATE_API_BASE_URL=https://api.frankfurter.app  # Default Frankfurter API
EXCHANGE_RATE_CACHE_TTL=86400  # 24 hours in seconds
EXCHANGE_RATE_REQUEST_TIMEOUT=10  # API request timeout in seconds

# Email Configuration (for magic links)
SMTP_SERVER=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=your-email@example.com
SMTP_PASSWORD=your-email-password
EMAIL_FROM=noreply@example.com
```

### Exchange Rate Configuration

The system automatically converts BRL amounts to EUR using the [Frankfurter API](https://www.frankfurter.app/). By default, it uses the following configuration:

- **Base Currency**: BRL (Brazilian Real)
- **Target Currency**: EUR (Euro)
- **Rate Lookup**: Uses the payslip's reference date for historical accuracy
- **Caching**: Rates are cached for 24 hours to reduce API calls

To customize the exchange rate service, you can modify the following in `src/config/exchange_rate_config.py`:

```python
class ExchangeRateConfig:
    API_BASE_URL = "https://api.frankfurter.app"  # Frankfurter API endpoint
    REQUEST_TIMEOUT = 10  # Request timeout in seconds
    CACHE_TTL = 86400  # Cache time-to-live in seconds (24 hours)
    BASE_CURRENCY = "BRL"  # Source currency
    TARGET_CURRENCY = "EUR"  # Target currency
```

## Changelog

See the [CHANGELOG.md](CHANGELOG.md) file for a detailed history of changes.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

1. Fork the repository
2. Create a new branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

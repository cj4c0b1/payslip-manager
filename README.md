# Payslip Management System

[![Security](https://img.shields.io/badge/security-enabled-brightgreen)](SECURITY.md)
[![CodeQL](https://github.com/cj4c0b1/payslip-manager/actions/workflows/codeql-analysis.yml/badge.svg)](https://github.com/cj4c0b1/payslip-manager/actions/workflows/codeql-analysis.yml)
[![Streamlit Cloud](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://payslip-manager.streamlit.app/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

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
  - Dynamic currency toggle (🇧🇷/🇪🇺) in the sidebar
  - On-the-fly conversion using stored exchange rates
  - Persistent user preference for currency display
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

## 🚀 Quick Start

### Option 1: Use the Live Demo

Access the live application at: [payslip-manager.streamlit.app](https://payslip-manager.streamlit.app/)

### Option 2: Local Development

1. **Clone the repository**:
   ```bash
   git clone https://github.com/cj4c0b1/payslip-manager.git
   cd payslip-manager
   ```

2. **Set up the environment**:
   ```bash
   # Create and activate virtual environment
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements.txt
   
   # For better performance
   pip install watchdog
   ```

3. **Initialize the database**:
   ```bash
   mkdir -p data uploads logs
   python -c "from src.database import init_db; init_db()"
   ```

## 🚀 Deployment

### Streamlit Cloud

The application is pre-configured for deployment to Streamlit Cloud:

1. Fork this repository
2. Go to [Streamlit Cloud](https://share.streamlit.io/)
3. Click "New app" and select your forked repository
4. Set the main file to `streamlit_app.py`
5. Configure your secrets in the Streamlit Cloud settings
6. Click "Deploy!"

### Environment Variables

For local development, create a `.env` file with:

```
DATABASE_URL=sqlite:///data/payslips.db
SECRET_KEY=your-secret-key
# Optional email settings
SMTP_SERVER=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=your-email@example.com
SMTP_PASSWORD=your-email-password
```

## 🖥️ Usage

### Local Development

1. **Start the application**:
   ```bash
   streamlit run main.py
   ```

2. Open your browser to [http://localhost:8501](http://localhost:8501)

3. **Login**:
   - Use the credentials configured in your `.streamlit/secrets.toml` file
   - For local development, you can set up your admin credentials in the secrets file

### Key Features

- **📤 Upload**: Process new payslip PDFs with automatic data extraction
- **👁️ View**: Browse and search payslips with advanced filtering
- **📊 Reports**: Generate analytics and export data in multiple formats
- **🔄 Currency**: Automatic BRL to EUR conversion with historical rates
- **🔐 Security**: Role-based access control and audit logging

### Currency Conversion

- Automatic BRL to EUR conversion using historical exchange rates
- Rate information stored with each payslip
- Manual refresh option available
- Toggle between original and converted amounts

## 🛠️ Development

### Project Structure

```
payslip-manager/
├── .streamlit/           # Streamlit configuration
│   ├── config.toml      # App settings
│   └── secrets.toml     # Sensitive data (gitignored)
├── data/                # Database and uploads
├── src/                 # Source code
│   ├── database.py      # Database setup and models
│   └── ...
├── main.py             # Main application
└── requirements.txt     # Dependencies
```

### Running Tests

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Run tests
pytest
```

### Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Style

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/)
- Type hints for all function parameters and return values
- Docstrings for all public functions and classes
- Meaningful commit messages
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

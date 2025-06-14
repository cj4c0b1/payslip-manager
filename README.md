# Payslip Management System

A Streamlit-based application for managing and analyzing employee payslips in PDF format. The system allows users to upload, store, and visualize payslip data with various reporting capabilities.

## Features

- **PDF Processing**: Extract data from PDF payslips automatically
- **Data Storage**: Store all payslip information in an SQLite database
- **Dashboard**: View key metrics and visualizations
- **Reports**: Generate detailed reports on earnings and deductions
- **Export**: Export data in multiple formats (CSV, Excel, PDF)
- **Secure Authentication**: Passwordless email-based authentication with magic links
  - No passwords to remember or manage
  - Single-use, time-limited login links
  - Automatic cleanup of expired tokens
  - Rate limiting for security
- **Role-Based Access Control**: Fine-grained permissions for different user roles
- **Audit Logging**: Track all authentication events and sensitive operations
- **Data Encryption**: Sensitive data encrypted at rest and in transit

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

## Configuration

Create a `.env` file in the project root with the following variables:

```
DATABASE_URL=sqlite:///data/payslips.db
SECRET_KEY=your-secret-key-here
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

1. Fork the repository
2. Create a new branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

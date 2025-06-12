# Payslip Management System

A Streamlit-based application for managing and analyzing employee payslips in PDF format. The system allows users to upload, store, and visualize payslip data with various reporting capabilities.

## Features

- **PDF Processing**: Extract data from PDF payslips automatically
- **Data Storage**: Store all payslip information in an SQLite database
- **Dashboard**: View key metrics and visualizations
- **Reports**: Generate detailed reports on earnings and deductions
- **Export**: Export data in multiple formats (CSV, Excel, PDF)
- **Secure Authentication**: Passwordless magic link authentication
- **Role-based Access Control**: Fine-grained permissions for different user roles
- **Audit Logging**: Track all authentication events

## Magic Link Authentication

The application features a secure, passwordless authentication system using magic links. Users can log in by requesting a one-time-use link sent to their email address.

### Key Security Features

- **No Passwords**: Eliminates password-related security risks
- **Single-Use Links**: Each link can only be used once
- **Short Expiration**: Links expire after 15 minutes by default
- **Device & Location Awareness**: Tracks device and location for security
- **Rate Limiting**: Prevents abuse of the authentication system

For detailed documentation, see [Magic Link Authentication](docs/magic_link_authentication.md).

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

4. Set up environment variables:
   Create a `.env` file in the project root with the following variables:
   ```env
   # Required for magic link authentication
   SECRET_KEY=your-secret-key-here
   BASE_URL=http://localhost:8501  # Update with your deployment URL
   
   # Email configuration (for sending magic links)
   SMTP_SERVER=smtp.example.com
   SMTP_PORT=587
   SMTP_USERNAME=your-email@example.com
   SMTP_PASSWORD=your-email-password
   EMAIL_FROM=noreply@example.com
   ```

## Usage

### Authentication

1. Access the application at `http://localhost:8501`
2. Enter your email address and click "Send Magic Link"
3. Check your email for a login link
4. Click the link to be automatically logged in

### Application Features

1. Start the Streamlit application:
   ```bash
   streamlit run main.py
   ```

2. Once authenticated, use the sidebar to navigate between sections:
   - **Dashboard**: View key metrics and visualizations
   - **Upload**: Upload and process new payslip PDFs
   - **View**: Browse and filter existing payslips
   - **Reports**: Generate and export detailed reports
   - **Admin**: Manage users and settings (admin only)

## Security

- All authentication tokens are single-use and expire after 15 minutes
- Sensitive operations require re-authentication
- Failed login attempts are rate-limited
- All communications are encrypted (HTTPS required in production)

For detailed security information, see [Security Guidelines](docs/security.md)

## Project Structure

```
payslip-manager/
├── src/
│   ├── __init__.py
│   ├── database.py      # Database models and connection
│   └── pdf_parser.py    # PDF processing logic
├── uploads/             # Directory for uploaded PDFs
│   └── processed/       # Processed PDFs are moved here
├── data/
│   └── payslips.db    # SQLite database
├── main.py              # Main Streamlit application
├── requirements.txt     # Python dependencies
└── README.md           # This file
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

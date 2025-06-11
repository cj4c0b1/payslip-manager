# Payslip Management System

A Streamlit-based application for managing and analyzing employee payslips in PDF format. The system allows users to upload, store, and visualize payslip data with various reporting capabilities.

## Features

- **PDF Processing**: Extract data from PDF payslips automatically
- **Data Storage**: Store all payslip information in an SQLite database
- **Dashboard**: View key metrics and visualizations
- **Reports**: Generate detailed reports on earnings and deductions
- **Export**: Export data in multiple formats (CSV, Excel, PDF)
- **User Authentication**: Basic authentication for security

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

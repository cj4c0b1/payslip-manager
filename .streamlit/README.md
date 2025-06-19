# Streamlit Cloud Deployment Guide

This directory contains configuration files for deploying the Payslip Manager application to Streamlit Cloud.

## Files

- `config.toml` - Main Streamlit configuration
- `secrets.template.toml` - Template for secrets (copy to `secrets.toml` and fill in your values)
- `secrets.toml` - Local development secrets (DO NOT COMMIT)
- `cloud_setup.sh` - Setup script that runs on Streamlit Cloud during deployment
- `credentials.toml` - Streamlit credentials and authentication settings

## Deployment Instructions

### Prerequisites

1. A GitHub account
2. A Streamlit Cloud account (https://share.streamlit.io/)
3. Your application code pushed to a GitHub repository

### Steps

1. **Prepare your repository**
   - Make sure all your code is committed and pushed to GitHub
   - Ensure you have a `requirements.txt` file with all dependencies
   - Make sure you have a `streamlit_app.py` file in the root directory

2. **Set up Streamlit Cloud**
   - Log in to [Streamlit Cloud](https://share.streamlit.io/)
   - Click "New app"
   - Select your repository, branch, and main file path (`streamlit_app.py`)
   - Click "Advanced settings" and add any environment variables from your `.env` file

3. **Configure secrets**
   - In the Streamlit Cloud settings, go to "Secrets"
   - Copy the contents of your `.streamlit/secrets.toml` file into the secrets editor
   - Make sure to replace any placeholder values with actual secrets

4. **Deploy**
   - Click "Deploy" to start the deployment
   - Streamlit Cloud will automatically install dependencies and start your app

## Environment Variables

For local development, create a `.env` file in the root of your project with the following variables:

```
# Database
DATABASE_URL=sqlite:///data/payslips.db

# Authentication
SECRET_KEY=your-secret-key

# Email (optional)
SMTP_SERVER=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=your-email@example.com
SMTP_PASSWORD=your-email-password
```

## Troubleshooting

- **App not starting**: Check the logs in the Streamlit Cloud dashboard for errors
- **Database issues**: Make sure the database file is writable and the path is correct
- **Missing dependencies**: Ensure all dependencies are listed in `requirements.txt`
- **Authentication problems**: Verify your secrets are correctly set in Streamlit Cloud

## Security Considerations

- Never commit sensitive information (passwords, API keys) to version control
- Use environment variables for configuration in production
- Regularly rotate your secrets and API keys
- Enable two-factor authentication for your Streamlit Cloud account

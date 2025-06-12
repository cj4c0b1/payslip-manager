# Magic Link Authentication

This document provides an overview of the magic link authentication system implemented in the application.

## Overview

Magic link authentication provides a secure, passwordless login mechanism. Instead of using passwords, users receive a one-time login link via email. This approach enhances security by eliminating password-related vulnerabilities.

## Key Components

### 1. MagicLink Model

Located in `src/models/magic_link.py`, this model represents a magic link in the database.

**Fields:**
- `id`: Primary key
- `token_hash`: Hashed version of the token (not stored in plaintext)
- `email`: Email address the link was sent to
- `created_at`: When the link was created
- `expires_at`: When the link expires
- `used`: Whether the link has been used
- `used_at`: When the link was used (if applicable)
- `user_agent`: User agent of the browser that requested the link
- `ip_address`: IP address that requested the link
- `user_id`: Foreign key to the User model (optional)

### 2. MagicLinkService

Located in `src/services/magic_link_service.py`, this service handles the core logic for magic link operations.

**Key Methods:**
- `create_magic_link()`: Generates and stores a new magic link
- `validate_magic_link()`: Validates a magic link token
- `mark_used()`: Marks a magic link as used

### 3. API Endpoints

#### Request a Magic Link

```http
POST /auth/magic-link/request
Content-Type: application/json

{
  "email": "user@example.com"
}
```

**Response:**
- 200: Magic link sent successfully
- 400: Invalid request
- 404: User not found (if user lookup is required)

#### Validate Magic Link

```http
GET /auth/magic-link/validate?token=abc123&email=user@example.com
```

**Response:**
- 302: Redirect to success URL with session token
- 400: Invalid or expired token
- 404: Magic link not found

## Security Considerations

1. **Token Security**
   - Tokens are generated using cryptographically secure methods
   - Only token hashes are stored in the database
   - Tokens are single-use and expire after a configurable time (default: 15 minutes)

2. **Rate Limiting**
   - Implement rate limiting to prevent abuse
   - Consider IP-based rate limiting for magic link requests

3. **Email Security**
   - Use HTTPS for all magic links
   - Include user agent and IP information in the email for security awareness
   - Consider adding a confirmation step for new devices

## Configuration

Configuration is handled through environment variables:

```env
# Magic link expiration time in minutes (default: 15)
MAGIC_LINK_EXPIRATION_MINUTES=15

# Base URL for magic links (e.g., https://yourapp.com)
BASE_URL=https://yourapp.com

# Email Configuration (required for magic links)
SMTP_SERVER=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=your-email@example.com
SMTP_PASSWORD=your-email-password
FROM_EMAIL=noreply@example.com

# Optional email settings
EMAIL_USE_TLS=true
EMAIL_USE_SSL=false
EMAIL_DEBUG=false
```

## Email Service Integration

The magic link system relies on the email service to deliver authentication links. The system uses SMTP and supports various providers including Gmail, SendGrid, AWS SES, and Mailtrap (for testing).

### Email Templates

Email templates are located in the `email_templates` directory:
- `magic_link.html` - HTML version of the magic link email
- `magic_link.txt` - Plain text fallback version

### Email Content Variables

The following variables are available in email templates:
- `magic_link` - The full magic link URL
- `expiration_minutes` - How long the link is valid (in minutes)
- `user_agent` - The user agent that requested the link
- `ip_address` - The IP address that requested the link
- `current_year` - Current year for copyright notices

### Testing Email Delivery

For development and testing, you can use Mailtrap or a local SMTP server. To test email delivery:

1. Configure your `.env` file with test SMTP settings
2. Run the email test script:
   ```bash
   python -m pytest tests/test_email_live.py -v
   ```

This will verify that:
- SMTP connection can be established
- Authentication works
- Emails are properly formatted
- Templates are rendered correctly

### Mocking Email Service in Tests

For unit tests, the email service is automatically mocked. You can verify email sending in tests:

```python
def test_magic_link_email(mock_smtp):
    # Test that magic link email is sent
    response = client.post("/auth/magic-link/request", 
                         json={"email": "test@example.com"})
    
    # Verify email was sent
    assert response.status_code == 200
    assert mock_smtp.called
    
    # Verify email content
    email_args = mock_smtp.return_value.send_message.call_args[0][0]
    assert "magic-link" in email_args["Subject"]
    assert "test@example.com" in email_args["To"]
```

## Testing

The magic link authentication system includes comprehensive test coverage for all major components. Tests are organized by component and functionality.

### Running Tests

Run all magic link authentication tests:
```bash
pytest tests/test_magic_link_auth.py -v
```

Run tests with coverage report:
```bash
pytest --cov=src.services.magic_link_service --cov=src.services.email_service tests/test_magic_link_auth.py -v
```

### Test Categories

#### 1. Unit Tests
- Test individual functions in isolation
- Mock all external dependencies
- Located in `tests/unit/test_magic_link_service.py`

#### 2. Integration Tests
- Test interaction between components
- Use test database
- Located in `tests/integration/test_magic_link_auth.py`

#### 3. Live Email Tests
- Test actual email delivery (requires SMTP configuration)
- Run manually or in CI with test credentials
- Located in `tests/test_email_live.py`

### Test Fixtures

Key fixtures available in `conftest.py`:

```python
# Database session for tests
@pytest.fixture
db_session():
    # Setup test database
    yield session
    # Cleanup after test

# Mock SMTP server
@pytest.fixture
def mock_smtp(mocker):
    return mocker.patch('smtplib.SMTP')

# Test client
@pytest.fixture
def test_client():
    app = create_test_app()
    with app.test_client() as client:
        yield client
```

### Example Test Case

```python
def test_magic_link_creation(db_session, mock_smtp):
    # Setup test data
    email = "test@example.com"
    ip_address = "192.168.1.1"
    user_agent = "Test User Agent"
    
    # Call service
    magic_link = MagicLinkService.create_magic_link(
        email=email,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    # Verify database record
    db_session.add(magic_link)
    db_session.commit()
    
    # Verify email was sent
    assert mock_smtp.return_value.send_message.called
    
    # Verify link properties
    assert magic_link.email == email
    assert not magic_link.used
    assert magic_link.expires_at > datetime.utcnow()
```

### Testing Best Practices

1. **Isolation**
   - Each test should be independent
   - Use transactions that roll back after each test
   - Mock external services

2. **Coverage**
   - Aim for high test coverage (90%+)
   - Test edge cases and error conditions
   - Include both happy path and failure scenarios

3. **Performance**
   - Keep tests fast by using mocks
   - Use test factories for complex objects
   - Avoid unnecessary database operations

4. **Maintainability**
   - Use descriptive test names
   - Follow the Arrange-Act-Assert pattern
   - Keep tests focused on a single behavior

### Debugging Tests

To debug a failing test:

1. Run a specific test with `-s` to see print statements:
   ```bash
   pytest tests/test_magic_link_auth.py::test_specific_test -v -s
   ```

2. Use `pdb` for interactive debugging:
   ```python
   import pdb; pdb.set_trace()  # Add to your test
   ```

3. Check the test database state:
   ```python
   # In your test
   from app import db
   print(db.session.query(MagicLink).all())
   ```

## Future Enhancements

1. Add support for device fingerprinting
2. Implement account lockout after multiple failed attempts
3. Add audit logging for security events
4. Support for customizing email templates
5. Add support for magic link revocation

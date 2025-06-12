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
```

## Testing

Tests are located in `tests/test_magic_link_auth.py`. To run the tests:

```bash
pytest tests/test_magic_link_auth.py -v
```

## Future Enhancements

1. Add support for device fingerprinting
2. Implement account lockout after multiple failed attempts
3. Add audit logging for security events
4. Support for customizing email templates
5. Add support for magic link revocation

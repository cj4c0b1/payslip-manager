# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added
- Magic link authentication feature for passwordless login
- Email service for sending magic links
- Database models for magic link sessions
- API endpoints for requesting and validating magic links
- Comprehensive test suite for authentication flow
- Documentation for configuration and usage
- Security features including rate limiting and link expiration

### Changed
- Updated dependencies to latest secure versions
- Improved error handling and logging
- Enhanced security headers and CSRF protection

### Fixed
- Resolved circular import issues in database models
- Fixed test fixtures for reliable test execution
- Addressed SQLAlchemy deprecation warnings
- Improved error messages for better debugging

### Security
- Implemented secure token generation and validation
- Added rate limiting to prevent abuse
- Ensured all sensitive data is properly hashed
- Added comprehensive input validation
- Improved session management

## [1.0.0] - YYYY-MM-DD
### Added
- Initial release of the Payslip Management System

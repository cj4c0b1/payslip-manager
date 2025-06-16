# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Fixed
- **Earnings Parsing**
  - Fixed `parse_earnings_and_deductions` to correctly return tuple of (earnings, deductions)
  - Improved handling of malformed numeric data in earnings, especially for "AD C DISP MIL"
  - Added fallback calculation for correct earnings amount when parsing fails
  
- **Date Handling**
  - Fixed duplicate check warning message to handle both date objects and date strings
  - Added robust error handling for date formatting in warning messages
  - Improved logging for date parsing issues

### Added
- **Security Enhancements**
  - Added SECURITY.md with vulnerability reporting guidelines
  - Implemented Dependabot for automated dependency updates and security alerts
  - Set up CodeQL for static code analysis and security scanning
  - Enabled secret scanning for detecting exposed credentials
  - Added private vulnerability reporting for secure issue disclosure
  - Updated README with security features and documentation

### Added
- GitHub Issue Management System
  - Added issue templates for features, bugs, and tasks
  - Created comprehensive label system for issue tracking
  - Set up initial set of issues for project tracking
- Magic link authentication system
  - Passwordless email-based authentication
  - Single-use, time-limited login links
  - Rate limiting for security
- Database schema updates
  - Added `magic_tokens` table with necessary indexes
  - Added `used_at` column to track token usage
  - Updated `employees` table with authentication fields
- New API endpoints for authentication
  - `/auth/magic-link/request` - Request a magic link
  - `/auth/magic-link/verify` - Verify a magic link
  - `/auth/me` - Get current user information
- Security enhancements
  - Environment-based configuration
  - Secure session management
  - CSRF protection

### Changed
- Updated project documentation structure
- Enhanced security configurations
- Improved error handling and logging
- Updated Pydantic models for V2 compatibility
  - Replaced `orm_mode` with `from_attributes`
  - Updated model configurations
- Enhanced documentation in README.md and DATABASE_PLAN.md

### Fixed
- Resolved database migration conflicts
- Fixed schema mismatch in `magic_tokens` table
- Addressed security vulnerabilities in dependencies

## [0.1.0] - 2024-06-15
### Added
- Initial project setup with basic structure
- Core functionality for payslip management
- Basic authentication system
- Database models and migrations
- Streamlit-based user interface

## Maintenance

### Changelog Maintenance
- All notable changes to this project will be documented in this file
- The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
- This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)

### Versioning Policy
- **MAJOR** version for incompatible API changes
- **MINOR** version for added functionality in a backward-compatible manner
- **PATCH** version for backward-compatible bug fixes

### How to Update
1. Add your changes to the [Unreleased] section
2. When releasing a new version, move the changes to a new version section
3. Update the version number in `__version__.py` and other relevant files
4. Commit with message: "chore: release vX.Y.Z"
5. Tag the commit with "vX.Y.Z"
6. Push the tag with `git push origin vX.Y.Z`

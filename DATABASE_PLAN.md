# Database Schema and Migration Plan

## Current Database Schema

### Tables

#### 1. `employees`
- `id` (INTEGER, PK): Unique identifier for the employee
- `email` (VARCHAR(100)): Employee's email address (unique)
- `first_name` (VARCHAR(50)): Employee's first name
- `last_name` (VARCHAR(50)): Employee's last name
- `cpf` (VARCHAR(14)): Brazilian CPF number (unique)
- `department` (VARCHAR(100)): Department name
- `position` (VARCHAR(100)): Job position
- `is_active` (BOOLEAN): Whether the account is active
- `created_at` (DATETIME): When the record was created
- `updated_at` (DATETIME): When the record was last updated
- `last_login_at` (DATETIME): Last login timestamp
- `failed_login_attempts` (INTEGER): Count of failed login attempts
- `account_locked_until` (DATETIME): When the account will be unlocked
- `password_reset_token` (VARCHAR(100)): Token for password reset
- `password_reset_token_expires` (DATETIME): When the password reset token expires

#### 2. `payslips`
- `id` (INTEGER, PK): Unique identifier for the payslip
- `employee_id` (INTEGER, FK to employees.id): Reference to the employee
- `reference_month` (DATE): The month/year this payslip is for
- `gross_salary` (DECIMAL(10,2)): Gross salary amount
- `net_salary` (DECIMAL(10,2)): Net salary amount
- `payment_date` (DATE): When the payment was made
- `created_at` (DATETIME): When the record was created
- `updated_at` (DATETIME): When the record was last updated

#### 3. `earnings`
- `id` (INTEGER, PK): Unique identifier
- `payslip_id` (INTEGER, FK to payslips.id): Reference to the payslip
- `description` (VARCHAR(255)): Description of the earning
- `amount` (DECIMAL(10,2)): Earning amount
- `type` (VARCHAR(50)): Type of earning (e.g., salary, bonus)

#### 4. `deductions`
- `id` (INTEGER, PK): Unique identifier
- `payslip_id` (INTEGER, FK to payslips.id): Reference to the payslip
- `description` (VARCHAR(255)): Description of the deduction
- `amount` (DECIMAL(10,2)): Deduction amount
- `type` (VARCHAR(50)): Type of deduction (e.g., tax, insurance)

#### 5. `magic_tokens`
- `id` (INTEGER, PK): Unique identifier
- `email` (VARCHAR(100)): Email the token was sent to
- `token_hash` (VARCHAR(64)): Hashed token value
- `expires_at` (DATETIME): When the token expires
- `used` (BOOLEAN): Whether the token has been used
- `used_at` (DATETIME): When the token was used (nullable)
- `created_at` (DATETIME): When the token was created
- `user_agent` (VARCHAR(255)): User agent from the login request
- `ip_address` (VARCHAR(45)): IP address from the login request

## Indexes

### Employees Table
- Primary Key: `id`
- Unique Index: `email`
- Index: `cpf` (for faster lookups by CPF)
- Index: `is_active` (for filtering active/inactive employees)

### Magic Tokens Table
- Primary Key: `id`
- Index: `email` (for looking up tokens by email)
- Index: `token_hash` (for verifying tokens)
- Index: `expires_at` (for cleaning up expired tokens)
- Index: `used` (for finding unused tokens)
- Composite Index: `(email, token_hash, expires_at, used)` for fast token validation

## Migration History

1. `20250614_add_auth_tables.py`
   - Initial database schema with employees, payslips, earnings, deductions, and magic_tokens tables

2. `20250614_add_cpf_department_position_to_employee.py`
   - Added `cpf`, `department`, and `position` columns to employees table
   - Added `first_name` and `last_name` columns (replaced `name`)

3. `20250614_add_used_at_to_magic_tokens_fix.py`
   - Added `used_at` column to magic_tokens table
   - Fixed schema to match model definition

## Pending Migrations

None - all migrations have been applied.

## Database Maintenance

### Backup Strategy
- Daily automated backups to a secure location
- Before any major schema changes, create a manual backup
- Backup command: `cp data/payslips.db data/backups/payslips_$(date +%Y%m%d_%H%M%S).db`

### Cleanup Tasks
- Expired magic tokens are automatically cleaned up by the application
- Old backups should be rotated (keep last 30 days)

## Known Issues

1. **Encryption Key Warning**
   - Warning: "Failed to get encryption key from secrets"
   - Impact: Some security features may not work as expected
   - Solution: Set up proper encryption key in environment variables

2. **bcrypt Version Warning**
   - Warning about bcrypt version
   - Impact: None - just a deprecation warning
   - Solution: Update bcrypt when possible

## Future Improvements

1. **Schema Changes**
   - Add unique constraint on `cpf` column
   - Add more indexes for performance
   - Consider partitioning large tables by date

2. **Data Validation**
   - Add CHECK constraints for data validation
   - Add more NOT NULL constraints where appropriate

3. **Performance**
   - Add database-level constraints and indexes
   - Consider denormalization for frequently accessed data

4. **Security**
   - Implement row-level security
   - Add audit logging for sensitive operations

## How to Add a New Migration

1. Create a new migration file:
   ```bash
   alembic revision -m "description_of_changes"
   ```

2. Edit the generated migration file to include your changes

3. Test the migration on a development database

4. Commit the migration file to version control

5. Apply the migration to production:
   ```bash
   alembic upgrade head
   ```

## Troubleshooting

### Common Issues

1. **Duplicate Column Errors**
   - Cause: Trying to add a column that already exists
   - Solution: Check current schema and modify migration to be idempotent

2. **Migration Conflicts**
   - Cause: Multiple developers creating migrations simultaneously
   - Solution: Merge branches carefully, resolve conflicts in migration files

3. **Database Locked**
   - Cause: Another process has locked the database
   - Solution: Ensure all database connections are properly closed

### Recovery

If a migration fails:
1. Restore from the most recent backup
2. Fix the migration script
3. Test the migration on a copy of the database
4. Re-apply the fixed migration

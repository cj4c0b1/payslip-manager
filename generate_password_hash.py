from getpass import getpass
from passlib.context import CryptContext

def main():
    # Create a password context
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    # Prompt for password securely
    password = getpass("Enter password to hash: ")
    confirm_password = getpass("Confirm password: ")
    
    if password != confirm_password:
        print("Error: Passwords do not match!")
        return
    
    # Hash the password
    hashed_password = pwd_context.hash(password)
    
    print("\nHashed password (copy this to secrets.toml):")
    print(f"password = \"{hashed_password}\"")
    
    # Verify the hash works
    if pwd_context.verify(password, hashed_password):
        print("\n✅ Verification successful!")
    else:
        print("\n❌ Verification failed!")

if __name__ == "__main__":
    main()

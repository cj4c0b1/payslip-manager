from setuptools import setup, find_packages

setup(
    name="payslip-manager",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        'streamlit>=1.22.0',
        'python-dotenv>=0.19.0',
        'python-jose[cryptography]>=3.3.0',
        'passlib[bcrypt]>=1.7.4',
        'pyjwt>=2.3.0',
        'cryptography>=36.0.0',
        'jinja2>=3.0.0',
        'python-multipart>=0.0.5',
        'email-validator>=1.1.3',
        'python-slugify>=6.1.2',
        'pytest>=7.0.0',
    ],
    python_requires=">=3.8",
    author="Your Name",
    author_email="your.email@example.com",
    description="Payslip Manager Application",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/payslip-manager",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)

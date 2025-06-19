from setuptools import setup, find_packages

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="payslip-manager",
    version="1.0.0",
    packages=find_packages(),
    install_requires=requirements,
    python_requires=">=3.8",
    author="Cicero Jacobi",
    author_email="j4c0b1@gmail.com",
    description="A Streamlit application for managing and analyzing payslips",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/cj4c0b1/payslip-manager",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    entry_points={
        "console_scripts": [
            "payslip-manager=main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.toml", "*.json", "*.md"],
    },
)

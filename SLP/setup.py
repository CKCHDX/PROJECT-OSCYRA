#!/usr/bin/env python
"""
Setup script for SLP project.
"""

from setuptools import setup, find_packages
from pathlib import Path

README = (Path(__file__).parent / "README.md").read_text()

setup(
    name="slp",
    version="1.0.0",
    description="Secure Line Protocol - Military-grade encrypted communication protocol",
    long_description=README,
    long_description_content_type="text/markdown",
    author="CKCHDX",
    author_email="contact@oscyra.solutions",
    url="https://github.com/CKCHDX/SLP",
    project_urls={
        "Documentation": "https://github.com/CKCHDX/SLP/tree/main/docs",
        "Source": "https://github.com/CKCHDX/SLP",
        "Tracker": "https://github.com/CKCHDX/SLP/issues",
    },
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "PyYAML>=6.0",
        "aiofiles>=23.0.0",
        "fastapi>=0.104.0",
        "uvicorn>=0.24.0",
        "cryptography>=41.0.0",
        "pynacl>=1.5.0",
        "aiohttp>=3.9.0",
        "uvloop>=0.19.0",
        "psutil>=5.9.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.1.0",
            "black>=23.0.0",
            "flake8>=6.1.0",
            "mypy>=1.7.0",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Security :: Cryptography",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    keywords="protocol security encryption communication async udp",
    entry_points={
        "console_scripts": [
            "slp-csh=csh.csh:main",
        ],
    },
)

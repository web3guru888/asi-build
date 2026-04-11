"""
AGI Economics Platform Setup
===========================

Setup script for the comprehensive AGI Economics Platform.
"""

from setuptools import setup, find_packages
import os

# Read README file
_setup_dir = os.path.dirname(os.path.abspath(__file__))
_readme_path = os.path.join(_setup_dir, "README.md")
try:
    with open(_readme_path, "r", encoding="utf-8") as fh:
        long_description = fh.read()
except FileNotFoundError:
    long_description = ""

# Read requirements
def read_requirements():
    """Read requirements from requirements.txt"""
    _req_path = os.path.join(_setup_dir, "requirements.txt")
    try:
        with open(_req_path, "r") as f:
            return [line.strip() for line in f if line.strip() and not line.startswith("#")]
    except FileNotFoundError:
        return []

# Version
VERSION = "1.0.0"

if __name__ == "__main__":
  setup(
    name="agi-economics",
    version=VERSION,
    author="Kenny AGI Team",
    author_email="kenny-agi@example.com",
    description="Comprehensive AGI Economic Simulation Platform for SingularityNET",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/kenny-agi/agi-economics",
    project_urls={
        "Bug Tracker": "https://github.com/kenny-agi/agi-economics/issues",
        "Documentation": "https://agi-economics.readthedocs.io/",
        "Source": "https://github.com/kenny-agi/agi-economics",
    },
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Office/Business :: Financial",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Distributed Computing",
    ],
    python_requires=">=3.8",
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0", 
            "pytest-cov>=4.1.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.5.0",
            "pre-commit>=3.3.0",
        ],
        "docs": [
            "sphinx>=7.1.0",
            "sphinx-rtd-theme>=1.3.0",
            "sphinx-autodoc-typehints>=1.24.0",
        ],
        "blockchain": [
            "web3>=6.0.0",
            "eth-account>=0.8.0",
            "py-solc-x>=1.12.0",
        ],
        "performance": [
            "uvloop>=0.17.0",
            "orjson>=3.9.0",
            "cython>=3.0.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "agi-economics=agi_economics.cli:main",
            "agi-demo=agi_economics.examples.complete_example:main",
        ],
    },
    include_package_data=True,
    package_data={
        "agi_economics": [
            "contracts/templates/*.sol",
            "docs/*.md",
            "examples/*.py",
            "config/*.yaml",
        ],
    },
    keywords=[
        "agi", "artificial intelligence", "economics", "blockchain", 
        "singularitynet", "token economics", "game theory", "reputation",
        "smart contracts", "decentralized", "marketplace"
    ],
    zip_safe=False,
)
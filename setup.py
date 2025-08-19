#!/usr/bin/env python3
"""
ASI:BUILD Production Installation Package
========================================

Production installation setup for the ASI:BUILD Superintelligence Framework.
Handles installation, configuration, and dependencies for all 47 subsystems.
"""

import os
import sys
from pathlib import Path
from setuptools import setup, find_packages

# Ensure Python version compatibility
if sys.version_info < (3, 11):
    raise RuntimeError("ASI:BUILD requires Python 3.11 or higher")

# Package metadata
HERE = Path(__file__).parent.resolve()
README = (HERE / "README.md").read_text(encoding="utf-8") if (HERE / "README.md").exists() else ""
VERSION = "1.0.0"

# Read requirements
def read_requirements(filename):
    """Read requirements from file"""
    requirements_file = HERE / filename
    if requirements_file.exists():
        with open(requirements_file, 'r', encoding='utf-8') as f:
            requirements = []
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if line and not line.startswith('#'):
                    # Remove version constraints for core setup
                    if '>=' in line:
                        package = line.split('>=')[0]
                        requirements.append(package)
                    elif '==' in line:
                        package = line.split('==')[0]
                        requirements.append(package)
                    else:
                        requirements.append(line)
            return requirements
    return []

# Core requirements (essential for basic functionality)
CORE_REQUIREMENTS = [
    "fastapi",
    "uvicorn[standard]",
    "pydantic",
    "PyJWT",
    "redis",
    "asyncpg",
    "sqlalchemy[asyncio]",
    "prometheus-client",
    "psutil",
    "aiohttp",
    "aiofiles",
    "click",
    "pyyaml",
    "python-dotenv",
    "cryptography",
    "numpy",
    "scipy",
    "pandas",
    "torch",
    "transformers"
]

# Optional requirements for specific features
QUANTUM_REQUIREMENTS = [
    "qiskit",
    "qiskit-aer",
    "cirq",
    "pennylane"
]

AI_REQUIREMENTS = [
    "torch",
    "torchvision",
    "transformers",
    "accelerate",
    "datasets",
    "scikit-learn",
    "tensorflow"
]

MONITORING_REQUIREMENTS = [
    "prometheus-client",
    "grafana-api",
    "elasticsearch",
    "redis",
    "psutil"
]

SECURITY_REQUIREMENTS = [
    "cryptography",
    "PyJWT",
    "passlib[bcrypt]",
    "pycryptodome"
]

CONSCIOUSNESS_REQUIREMENTS = [
    "brian2",
    "networkx",
    "sympy",
    "scipy"
]

BLOCKCHAIN_REQUIREMENTS = [
    "web3",
    "eth-hash",
    "ethereum"
]

DEV_REQUIREMENTS = [
    "pytest",
    "pytest-asyncio",
    "pytest-cov",
    "black",
    "flake8",
    "mypy",
    "bandit",
    "safety"
]

# All optional requirements
EXTRAS_REQUIRE = {
    "quantum": QUANTUM_REQUIREMENTS,
    "ai": AI_REQUIREMENTS,
    "monitoring": MONITORING_REQUIREMENTS,
    "security": SECURITY_REQUIREMENTS,
    "consciousness": CONSCIOUSNESS_REQUIREMENTS,
    "blockchain": BLOCKCHAIN_REQUIREMENTS,
    "dev": DEV_REQUIREMENTS,
    "all": (QUANTUM_REQUIREMENTS + AI_REQUIREMENTS + MONITORING_REQUIREMENTS + 
            SECURITY_REQUIREMENTS + CONSCIOUSNESS_REQUIREMENTS + BLOCKCHAIN_REQUIREMENTS)
}

# Console scripts
CONSOLE_SCRIPTS = [
    "asi-build=asi_build_launcher:main",
    "asi-build-api=asi_build_api:main",
    "asi-build-monitor=monitoring:main",
    "asi-build-safety=safety_protocols:main"
]

# Package data
PACKAGE_DATA = {
    "asi_build": [
        "configs/*.json",
        "configs/*.yaml",
        "templates/*.html",
        "static/*",
        "kubernetes/*.yaml",
        "monitoring/*.yml",
        "data/*"
    ]
}

# Data files
DATA_FILES = [
    ("etc/asi_build", ["configs/default_config.json"]),
    ("var/log/asi_build", []),
    ("var/lib/asi_build", []),
    ("usr/share/asi_build/docs", ["README.md"]),
]

setup(
    name="asi-build",
    version=VERSION,
    description="ASI:BUILD - Production Superintelligence Framework",
    long_description=README,
    long_description_content_type="text/markdown",
    
    # Author information
    author="ASI:BUILD Development Team",
    author_email="contact@asi-build.ai",
    url="https://github.com/asi-build/asi-build",
    project_urls={
        "Documentation": "https://docs.asi-build.ai",
        "Bug Reports": "https://github.com/asi-build/asi-build/issues",
        "Source": "https://github.com/asi-build/asi-build",
        "Funding": "https://opencollective.com/asi-build",
    },
    
    # License
    license="MIT",
    
    # Package discovery
    packages=find_packages(exclude=["tests", "tests.*", "docs", "docs.*"]),
    package_data=PACKAGE_DATA,
    data_files=DATA_FILES,
    include_package_data=True,
    
    # Dependencies
    python_requires=">=3.11",
    install_requires=CORE_REQUIREMENTS,
    extras_require=EXTRAS_REQUIRE,
    
    # Console scripts
    entry_points={
        "console_scripts": CONSOLE_SCRIPTS,
    },
    
    # Classification
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Distributed Computing",
        "Environment :: Console",
        "Environment :: Web Environment",
        "Framework :: AsyncIO",
        "Natural Language :: English",
    ],
    
    # Keywords
    keywords=[
        "artificial-intelligence", "superintelligence", "agi", "asi", 
        "machine-learning", "deep-learning", "consciousness", "quantum-computing",
        "safety", "alignment", "ethics", "governance", "monitoring",
        "production", "framework", "distributed-systems"
    ],
    
    # Platform support
    platforms=["any"],
    
    # Zip safe
    zip_safe=False,
    
    # Additional metadata
    cmdclass={},
)

# Post-installation setup
def post_install():
    """Post-installation setup tasks"""
    print("ASI:BUILD Installation Complete!")
    print("=" * 50)
    print()
    print("Next steps:")
    print("1. Initialize configuration: asi-build init")
    print("2. Start the system: asi-build start")
    print("3. Access the API: http://localhost:8080")
    print("4. View documentation: https://docs.asi-build.ai")
    print()
    print("Safety Notice:")
    print("- ASI:BUILD includes powerful capabilities")
    print("- Always run with safety protocols enabled")
    print("- Ensure human oversight is configured")
    print("- Review security settings before production use")
    print()
    print("Support:")
    print("- Documentation: https://docs.asi-build.ai")
    print("- Issues: https://github.com/asi-build/asi-build/issues")
    print("- Community: https://discord.gg/asi-build")
    print()

if __name__ == "__main__":
    setup()
    post_install()
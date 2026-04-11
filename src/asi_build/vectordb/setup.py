"""Setup script for Kenny Vector Database System."""

from setuptools import find_packages, setup

with open("requirements.txt", "r", encoding="utf-8") as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="kenny-vectordb",
    version="1.0.0",
    author="Kenny AGI System",
    author_email="kenny@example.com",
    description="Advanced vector database system with multi-database support",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/kenny-agi/vectordb",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Database",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0.0",
            "black>=22.0.0",
            "flake8>=5.0.0",
            "mypy>=0.991",
        ],
        "optional": [
            "faiss-cpu>=1.7.0",
            "chromadb>=0.4.0",
            "langchain>=0.0.200",
        ],
    },
    entry_points={
        "console_scripts": [
            "kenny-vectordb=kenny_vectordb.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "kenny_vectordb": [
            "config.yaml",
            ".env.example",
        ],
    },
    project_urls={
        "Bug Reports": "https://github.com/kenny-agi/vectordb/issues",
        "Source": "https://github.com/kenny-agi/vectordb",
        "Documentation": "https://kenny-agi.github.io/vectordb",
    },
)

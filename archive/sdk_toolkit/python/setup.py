#!/usr/bin/env python3
"""
Kenny AGI RDK - Python SDK
Setup configuration for PyPI distribution
"""

from setuptools import setup, find_packages
import os

# Read README file
def read_readme():
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return ''

# Read requirements
def read_requirements():
    requirements_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    if os.path.exists(requirements_path):
        with open(requirements_path, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]
    return []

setup(
    name='kenny-agi-sdk',
    version='1.0.0',
    description='Kenny AGI RDK - Python SDK for Artificial General Intelligence',
    long_description=read_readme(),
    long_description_content_type='text/markdown',
    
    # Author information
    author='Kenny AGI Development Team',
    author_email='dev@kenny-agi.dev',
    
    # URLs
    url='https://github.com/kenny-agi/rdk',
    project_urls={
        'Documentation': 'https://kenny-agi.dev/docs/python-sdk',
        'Bug Reports': 'https://github.com/kenny-agi/rdk/issues',
        'Source': 'https://github.com/kenny-agi/rdk/tree/main/sdk/python',
        'Funding': 'https://github.com/sponsors/kenny-agi',
    },
    
    # Package information
    packages=find_packages(exclude=['tests*', 'docs*', 'examples*']),
    py_modules=['kenny_sdk'],
    
    # Python version requirements
    python_requires='>=3.8',
    
    # Dependencies
    install_requires=[
        'requests>=2.31.0',
        'websockets>=11.0.2',
        'aiohttp>=3.8.5',
        'pydantic>=2.0.0',
        'typing-extensions>=4.7.0',
    ],
    
    # Optional dependencies
    extras_require={
        'dev': [
            'pytest>=7.4.0',
            'pytest-asyncio>=0.21.0',
            'pytest-cov>=4.1.0',
            'black>=23.7.0',
            'flake8>=6.0.0',
            'mypy>=1.5.0',
            'isort>=5.12.0',
            'pre-commit>=3.3.0',
        ],
        'docs': [
            'sphinx>=7.1.0',
            'sphinx-rtd-theme>=1.3.0',
            'sphinxcontrib-asyncio>=0.3.0',
            'myst-parser>=2.0.0',
        ],
        'performance': [
            'orjson>=3.9.0',
            'uvloop>=0.17.0; sys_platform != "win32"',
            'aiofiles>=23.1.0',
        ],
        'observability': [
            'opentelemetry-api>=1.19.0',
            'opentelemetry-sdk>=1.19.0',
            'opentelemetry-instrumentation-requests>=0.40b0',
            'opentelemetry-instrumentation-aiohttp-client>=0.40b0',
            'structlog>=23.1.0',
        ],
        'cli': [
            'click>=8.1.0',
            'rich>=13.5.0',
            'typer>=0.9.0',
        ],
        'jupyter': [
            'jupyter>=1.0.0',
            'ipywidgets>=8.0.0',
            'matplotlib>=3.7.0',
            'pandas>=2.0.0',
        ],
        'all': [
            'orjson>=3.9.0',
            'uvloop>=0.17.0; sys_platform != "win32"',
            'aiofiles>=23.1.0',
            'opentelemetry-api>=1.19.0',
            'opentelemetry-sdk>=1.19.0',
            'structlog>=23.1.0',
            'click>=8.1.0',
            'rich>=13.5.0',
            'jupyter>=1.0.0',
            'pandas>=2.0.0',
        ],
    },
    
    # Package classification
    classifiers=[
        # Development Status
        'Development Status :: 5 - Production/Stable',
        
        # Intended Audience
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'Intended Audience :: Information Technology',
        
        # License
        'License :: OSI Approved :: MIT License',
        
        # Programming Language
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        
        # Operating System
        'Operating System :: OS Independent',
        'Operating System :: POSIX',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: MacOS',
        
        # Topic
        'Topic :: Scientific/Engineering :: Artificial Intelligence',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: System :: Networking',
        'Topic :: Scientific/Engineering :: Physics',
        
        # Framework
        'Framework :: AsyncIO',
        'Framework :: Jupyter',
        
        # Environment
        'Environment :: Console',
        'Environment :: Web Environment',
        
        # Natural Language
        'Natural Language :: English',
        
        # Typing
        'Typing :: Typed',
    ],
    
    # Keywords for PyPI search
    keywords=[
        'agi', 'artificial-intelligence', 'consciousness', 'reality-manipulation',
        'quantum-computing', 'machine-learning', 'neural-networks', 'sdk',
        'api-client', 'websocket', 'async', 'asyncio', 'real-time',
        'temporal-mechanics', 'dimensional-portal', 'probability-manipulation',
        'kenny-agi', 'rdk', 'transcendence', 'omniscience'
    ],
    
    # Include package data
    include_package_data=True,
    package_data={
        'kenny_sdk': [
            'py.typed',
            '*.pyi',
            'data/*.json',
            'schemas/*.json',
        ],
    },
    
    # Entry points for CLI tools
    entry_points={
        'console_scripts': [
            'kenny-agi=kenny_sdk.cli:main [cli]',
            'kenny-monitor=kenny_sdk.monitoring:main [observability]',
            'kenny-benchmark=kenny_sdk.benchmark:main [performance]',
        ],
    },
    
    # Minimum requirements for wheels
    zip_safe=False,
    
    # Project metadata
    license='MIT',
    platforms=['any'],
    
    # Test suite
    test_suite='tests',
    tests_require=[
        'pytest>=7.4.0',
        'pytest-asyncio>=0.21.0',
        'pytest-cov>=4.1.0',
        'responses>=0.23.0',
        'pytest-mock>=3.11.0',
    ],
    
    # Setup requires
    setup_requires=[
        'wheel>=0.41.0',
        'setuptools>=68.0.0',
    ],
    
    # Options for bdist_wheel
    options={
        'bdist_wheel': {
            'universal': False,  # Not universal (has C extensions in deps)
        },
        'egg_info': {
            'tag_build': '',
            'tag_date': False,
        },
    },
    
    # Metadata for PEP 621 compatibility
    dynamic=['dependencies', 'optional-dependencies'],
)

# Verify Python version
import sys
if sys.version_info < (3, 8):
    print("Error: Kenny AGI SDK requires Python 3.8 or higher.")
    sys.exit(1)

print("Kenny AGI Python SDK setup complete!")
print("Documentation: https://kenny-agi.dev/docs/python-sdk")
print("Examples: https://github.com/kenny-agi/rdk/tree/main/examples/python")
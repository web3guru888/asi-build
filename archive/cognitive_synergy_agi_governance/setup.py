#!/usr/bin/env python3
"""
AGI Governance & Ethics Platform Setup Script

Installation and configuration script for the AGI Governance & Ethics Platform,
implementing Ben Goertzel's vision of beneficial AGI through democratic
governance and ethical constraints.
"""

import os
import sys
import asyncio
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# Ensure minimum Python version
if sys.version_info < (3, 9):
    print("ERROR: AGI Governance Platform requires Python 3.9 or higher")
    print(f"Current version: {sys.version}")
    sys.exit(1)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('agi_governance_setup.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class AGIGovernanceSetup:
    """Setup and configuration manager for AGI Governance Platform."""
    
    def __init__(self, base_path: str = None):
        self.base_path = Path(base_path) if base_path else Path.cwd()
        self.config_path = self.base_path / 'config'
        self.data_path = self.base_path / 'data'
        self.logs_path = self.base_path / 'logs'
        self.docs_path = self.base_path / 'docs'
        
        self.setup_complete = False
        
    def run_setup(self, mode: str = 'development') -> bool:
        """Run complete platform setup."""
        try:
            logger.info("=== AGI Governance & Ethics Platform Setup ===")
            logger.info(f"Setup mode: {mode}")
            logger.info(f"Base path: {self.base_path}")
            logger.info(f"Python version: {sys.version}")
            
            # Create directory structure
            self._create_directory_structure()
            
            # Check dependencies
            self._check_dependencies()
            
            # Generate configuration
            config = self._generate_configuration(mode)
            
            # Initialize database
            self._initialize_database()
            
            # Setup security
            self._setup_security()
            
            # Create initial data
            self._create_initial_data()
            
            # Validate setup
            self._validate_setup()
            
            # Generate deployment scripts
            self._generate_deployment_scripts(mode)
            
            self.setup_complete = True
            
            logger.info("=== Setup Complete ===")
            logger.info("AGI Governance Platform successfully configured!")
            logger.info(f"Configuration saved to: {self.config_path}")
            logger.info(f"Database initialized at: {self.data_path}")
            logger.info(f"Logs will be written to: {self.logs_path}")
            
            self._print_next_steps(mode)
            
            return True
            
        except Exception as e:
            logger.error(f"Setup failed: {e}")
            logger.error("Please check the logs and try again")
            return False
    
    def _create_directory_structure(self):
        """Create necessary directory structure."""
        logger.info("Creating directory structure...")
        
        directories = [
            self.config_path,
            self.data_path,
            self.logs_path,
            self.data_path / 'audit_ledger',
            self.data_path / 'backups',
            self.config_path / 'templates',
            self.logs_path / 'archived'
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created directory: {directory}")
    
    def _check_dependencies(self):
        """Check and validate dependencies."""
        logger.info("Checking dependencies...")
        
        required_modules = [
            'sympy', 'numpy', 'asyncio', 'sqlite3', 'json',
            'hashlib', 'hmac', 'datetime', 'dataclasses'
        ]
        
        missing_modules = []
        
        for module in required_modules:
            try:
                __import__(module)
                logger.info(f"✓ {module}")
            except ImportError:
                missing_modules.append(module)
                logger.warning(f"✗ {module} - Missing")
        
        if missing_modules:
            logger.error(f"Missing required modules: {missing_modules}")
            logger.error("Please install requirements: pip install -r requirements.txt")
            raise ImportError(f"Missing dependencies: {missing_modules}")
        
        logger.info("All dependencies satisfied")
    
    def _generate_configuration(self, mode: str) -> Dict[str, Any]:
        """Generate platform configuration."""
        logger.info(f"Generating {mode} configuration...")
        
        if mode == 'development':
            config = self._get_development_config()
        elif mode == 'production':
            config = self._get_production_config()
        elif mode == 'distributed':
            config = self._get_distributed_config()
        else:
            raise ValueError(f"Unknown setup mode: {mode}")
        
        # Save configuration
        config_file = self.config_path / f'{mode}_config.json'
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2, default=str)
        
        logger.info(f"Configuration saved to: {config_file}")
        return config
    
    def _get_development_config(self) -> Dict[str, Any]:
        """Get development configuration."""
        return {
            "mode": "development",
            "database_path": str(self.data_path / "agi_governance_dev.db"),
            "log_level": "DEBUG",
            "blockchain_config": {
                "network": "local",
                "consensus": "proof_of_stake",
                "block_time_minutes": 1,  # Fast for development
                "difficulty": 1
            },
            "voting_parameters": {
                "voting_period_days": 1,  # Short for testing
                "quorum_threshold": 0.05,  # Low for testing
                "approval_threshold": 0.5,
                "veto_threshold": 0.8
            },
            "ethics_frameworks": [
                "utilitarian",
                "deontological",
                "virtue_ethics"
            ],
            "stakeholder_categories": [
                "general_public",
                "technical_experts",
                "ethicists",
                "policymakers",
                "agi_entities"
            ],
            "audit_settings": {
                "block_size": 10,  # Small for development
                "retention_period_days": 30,
                "public_access_level": "stakeholder"
            },
            "emergency_contacts": [
                "dev_admin",
                "test_safety_officer"
            ],
            "human_oversight_config": {
                "required_for_critical": True,
                "timeout_minutes": 5,  # Short for testing
                "max_concurrent_sessions": 10
            },
            "security": {
                "encryption_enabled": False,  # Disabled for dev
                "multi_factor_auth": False,
                "session_timeout_minutes": 60
            }
        }
    
    def _get_production_config(self) -> Dict[str, Any]:
        """Get production configuration."""
        return {
            "mode": "production",
            "database_path": str(self.data_path / "agi_governance_prod.db"),
            "log_level": "INFO",
            "blockchain_config": {
                "network": "mainnet",
                "consensus": "proof_of_stake",
                "block_time_minutes": 10,
                "difficulty": 4
            },
            "voting_parameters": {
                "voting_period_days": 7,
                "quorum_threshold": 0.1,
                "approval_threshold": 0.6,
                "veto_threshold": 0.8
            },
            "ethics_frameworks": [
                "utilitarian",
                "deontological",
                "virtue_ethics",
                "care_ethics",
                "environmental_ethics"
            ],
            "stakeholder_categories": [
                "general_public",
                "technical_experts",
                "ethicists",
                "policymakers",
                "affected_communities",
                "agi_entities",
                "organizations"
            ],
            "audit_settings": {
                "block_size": 100,
                "retention_period_days": 2555,  # 7 years
                "public_access_level": "public",
                "backup_schedule": "daily",
                "backup_encryption": True
            },
            "emergency_contacts": [
                "emergency_response_team",
                "safety_officer",
                "governance_chair",
                "ethics_chair",
                "legal_counsel"
            ],
            "human_oversight_config": {
                "required_for_critical": True,
                "timeout_minutes": 30,
                "max_concurrent_sessions": 50,
                "expert_verification_required": True
            },
            "security": {
                "encryption_enabled": True,
                "multi_factor_auth": True,
                "session_timeout_minutes": 30,
                "ip_whitelist_enabled": True,
                "rate_limiting": {
                    "requests_per_minute": 100,
                    "burst_allowance": 10
                }
            },
            "monitoring": {
                "health_check_interval_seconds": 60,
                "performance_monitoring": True,
                "alert_thresholds": {
                    "cpu_percent": 80,
                    "memory_percent": 85,
                    "disk_percent": 90
                }
            }
        }
    
    def _get_distributed_config(self) -> Dict[str, Any]:
        """Get distributed system configuration."""
        config = self._get_production_config()
        config.update({
            "mode": "distributed",
            "network_config": {
                "node_type": "primary",  # Will be updated per node
                "discovery_method": "static",
                "consensus_protocol": "raft",
                "replication_factor": 3,
                "heartbeat_interval_seconds": 30
            },
            "load_balancing": {
                "enabled": True,
                "algorithm": "round_robin",
                "health_check_path": "/health"
            },
            "clustering": {
                "enabled": True,
                "cluster_size": 3,
                "auto_failover": True
            }
        })
        return config
    
    def _initialize_database(self):
        """Initialize the governance database."""
        logger.info("Initializing database...")
        
        import sqlite3
        
        db_path = self.data_path / "agi_governance.db"
        
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Create audit records table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_records (
                id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                event_data TEXT NOT NULL,
                metadata TEXT,
                audit_level TEXT NOT NULL,
                privacy_mask TEXT,
                timestamp TEXT NOT NULL,
                block_height INTEGER,
                transaction_hash TEXT NOT NULL,
                previous_hash TEXT,
                merkle_root TEXT,
                digital_signature TEXT,
                verification_status TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create stakeholders table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stakeholders (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                category TEXT NOT NULL,
                reputation_score REAL DEFAULT 0.0,
                voting_power REAL DEFAULT 1.0,
                verified BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        ''')
        
        # Create proposals table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS proposals (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                category TEXT NOT NULL,
                proposer_id TEXT NOT NULL,
                status TEXT NOT NULL,
                voting_deadline TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT,
                FOREIGN KEY (proposer_id) REFERENCES stakeholders (id)
            )
        ''')
        
        # Create votes table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS votes (
                id TEXT PRIMARY KEY,
                proposal_id TEXT NOT NULL,
                voter_id TEXT NOT NULL,
                vote_type TEXT NOT NULL,
                reasoning TEXT,
                voting_power REAL DEFAULT 1.0,
                cast_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (proposal_id) REFERENCES proposals (id),
                FOREIGN KEY (voter_id) REFERENCES stakeholders (id),
                UNIQUE(proposal_id, voter_id)
            )
        ''')
        
        # Create indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_records(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_event_type ON audit_records(event_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_proposals_status ON proposals(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_votes_proposal ON votes(proposal_id)')
        
        # Commit and close
        conn.commit()
        conn.close()
        
        logger.info(f"Database initialized at: {db_path}")
    
    def _setup_security(self):
        """Setup security configuration."""
        logger.info("Setting up security...")
        
        # Generate encryption keys
        from cryptography.fernet import Fernet
        
        # Platform encryption key
        platform_key = Fernet.generate_key()
        key_file = self.config_path / 'platform.key'
        
        with open(key_file, 'wb') as f:
            f.write(platform_key)
        
        # Set secure permissions
        os.chmod(key_file, 0o600)
        
        # Generate API tokens
        import secrets
        
        api_tokens = {
            'admin_token': secrets.token_urlsafe(32),
            'governance_token': secrets.token_urlsafe(32),
            'audit_token': secrets.token_urlsafe(32)
        }
        
        tokens_file = self.config_path / 'api_tokens.json'
        with open(tokens_file, 'w') as f:
            json.dump(api_tokens, f, indent=2)
        
        os.chmod(tokens_file, 0o600)
        
        logger.info("Security configuration completed")
    
    def _create_initial_data(self):
        """Create initial system data."""
        logger.info("Creating initial data...")
        
        # Create initial stakeholders data
        initial_stakeholders = [
            {
                'id': 'governance_committee',
                'name': 'Governance Committee',
                'type': 'organization',
                'category': 'policymakers',
                'reputation_score': 5.0,
                'voting_power': 5.0,
                'verified': True
            },
            {
                'id': 'ethics_committee',
                'name': 'Ethics Committee', 
                'type': 'organization',
                'category': 'ethicists',
                'reputation_score': 5.0,
                'voting_power': 3.0,
                'verified': True
            },
            {
                'id': 'safety_committee',
                'name': 'Safety Committee',
                'type': 'organization',
                'category': 'technical_experts',
                'reputation_score': 5.0,
                'voting_power': 4.0,
                'verified': True
            }
        ]
        
        initial_data_file = self.data_path / 'initial_stakeholders.json'
        with open(initial_data_file, 'w') as f:
            json.dump(initial_stakeholders, f, indent=2)
        
        # Create initial ethical constraints
        initial_constraints = [
            {
                'name': 'Human Safety Priority',
                'description': 'Human safety takes precedence over other considerations',
                'formal_specification': 'human_safety_risk -> immediate_intervention',
                'enforcement': 'emergency_stop'
            },
            {
                'name': 'Autonomy Preservation',
                'description': 'Respect human autonomy and self-determination',
                'formal_specification': 'affects_human_choice -> requires_consent',
                'enforcement': 'consent_verification'
            },
            {
                'name': 'Transparency Requirement',
                'description': 'AGI decisions must be explainable and auditable',
                'formal_specification': 'agi_decision -> provides_explanation',
                'enforcement': 'audit_trail'
            }
        ]
        
        constraints_file = self.data_path / 'initial_constraints.json'
        with open(constraints_file, 'w') as f:
            json.dump(initial_constraints, f, indent=2)
        
        logger.info("Initial data created")
    
    def _validate_setup(self):
        """Validate that setup completed successfully."""
        logger.info("Validating setup...")
        
        # Check directory structure
        required_dirs = [self.config_path, self.data_path, self.logs_path]
        for directory in required_dirs:
            if not directory.exists():
                raise FileNotFoundError(f"Required directory not found: {directory}")
        
        # Check configuration files
        config_files = list(self.config_path.glob('*_config.json'))
        if not config_files:
            raise FileNotFoundError("No configuration files found")
        
        # Check database
        db_path = self.data_path / "agi_governance.db"
        if not db_path.exists():
            raise FileNotFoundError(f"Database not found: {db_path}")
        
        # Test database connection
        import sqlite3
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            conn.close()
            
            required_tables = {'audit_records', 'stakeholders', 'proposals', 'votes'}
            existing_tables = {table[0] for table in tables}
            
            if not required_tables.issubset(existing_tables):
                missing = required_tables - existing_tables
                raise ValueError(f"Missing database tables: {missing}")
                
        except Exception as e:
            raise RuntimeError(f"Database validation failed: {e}")
        
        # Check security files
        key_file = self.config_path / 'platform.key'
        if not key_file.exists():
            raise FileNotFoundError("Platform encryption key not found")
        
        logger.info("Setup validation completed successfully")
    
    def _generate_deployment_scripts(self, mode: str):
        """Generate deployment and management scripts."""
        logger.info("Generating deployment scripts...")
        
        scripts_dir = self.base_path / 'scripts'
        scripts_dir.mkdir(exist_ok=True)
        
        # Start script
        start_script = f"""#!/bin/bash
# AGI Governance Platform Start Script

cd {self.base_path}
export PYTHONPATH="${{PYTHONPATH}}:{self.base_path}"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Set configuration
export AGI_GOVERNANCE_CONFIG="{self.config_path}/{mode}_config.json"
export AGI_GOVERNANCE_MODE="{mode}"

# Start platform
python -m agi_governance_platform --config "$AGI_GOVERNANCE_CONFIG" --mode "$AGI_GOVERNANCE_MODE"
"""
        
        start_script_path = scripts_dir / f'start_{mode}.sh'
        with open(start_script_path, 'w') as f:
            f.write(start_script)
        os.chmod(start_script_path, 0o755)
        
        # Stop script
        stop_script = f"""#!/bin/bash
# AGI Governance Platform Stop Script

echo "Stopping AGI Governance Platform..."

# Find and stop platform processes
pkill -f "agi_governance_platform"

echo "Platform stopped"
"""
        
        stop_script_path = scripts_dir / f'stop_{mode}.sh'
        with open(stop_script_path, 'w') as f:
            f.write(stop_script)
        os.chmod(stop_script_path, 0o755)
        
        # Health check script
        health_script = f"""#!/bin/bash
# AGI Governance Platform Health Check

curl -f http://localhost:8000/health || exit 1
echo "Platform health check passed"
"""
        
        health_script_path = scripts_dir / 'health_check.sh'
        with open(health_script_path, 'w') as f:
            f.write(health_script)
        os.chmod(health_script_path, 0o755)
        
        # Backup script
        backup_script = f"""#!/bin/bash
# AGI Governance Platform Backup Script

BACKUP_DIR="{self.data_path}/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="agi_governance_backup_$DATE"

mkdir -p "$BACKUP_DIR"

# Backup database
cp "{self.data_path}/agi_governance.db" "$BACKUP_DIR/${{BACKUP_NAME}}.db"

# Backup configuration
cp -r "{self.config_path}" "$BACKUP_DIR/${{BACKUP_NAME}}_config"

# Backup audit ledger
cp -r "{self.data_path}/audit_ledger" "$BACKUP_DIR/${{BACKUP_NAME}}_ledger"

# Compress backup
tar -czf "$BACKUP_DIR/${{BACKUP_NAME}}.tar.gz" -C "$BACKUP_DIR" "${{BACKUP_NAME}}"*

# Clean up uncompressed files
rm -rf "$BACKUP_DIR/${{BACKUP_NAME}}"*

echo "Backup completed: $BACKUP_DIR/${{BACKUP_NAME}}.tar.gz"
"""
        
        backup_script_path = scripts_dir / 'backup.sh'
        with open(backup_script_path, 'w') as f:
            f.write(backup_script)
        os.chmod(backup_script_path, 0o755)
        
        logger.info(f"Deployment scripts generated in: {scripts_dir}")
    
    def _print_next_steps(self, mode: str):
        """Print next steps for user."""
        print("\n" + "="*60)
        print("🎉 AGI GOVERNANCE PLATFORM SETUP COMPLETE! 🎉")
        print("="*60)
        print("\n📋 NEXT STEPS:")
        print("\n1. Start the platform:")
        print(f"   ./scripts/start_{mode}.sh")
        print("\n2. Access the platform:")
        print("   - Dashboard: http://localhost:8000/dashboard")
        print("   - API: http://localhost:8000/api")
        print("   - Documentation: http://localhost:8000/docs")
        print("\n3. Initial configuration:")
        print("   - Register your first stakeholder")
        print("   - Submit a test proposal")
        print("   - Verify audit logging")
        print("\n4. Security setup:")
        print("   - Change default API tokens")
        print("   - Configure user authentication")
        print("   - Set up backup procedures")
        print("\n📚 DOCUMENTATION:")
        print("   - Deployment Guide: docs/DEPLOYMENT.md")
        print("   - Governance Guide: docs/GOVERNANCE_GUIDE.md")
        print("   - Ethics Framework: docs/ETHICS_FRAMEWORK.md")
        print("\n🆘 SUPPORT:")
        print("   - GitHub Issues: [repository-url]/issues")
        print("   - Documentation: docs/")
        print("   - Community Forum: [forum-url]")
        print("\n" + "="*60)
        print("🤖 Building beneficial AGI through democratic governance! 🤖")
        print("="*60)


def main():
    """Main setup function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='AGI Governance Platform Setup')
    parser.add_argument('--mode', choices=['development', 'production', 'distributed'],
                       default='development', help='Setup mode')
    parser.add_argument('--path', help='Installation path (default: current directory)')
    parser.add_argument('--force', action='store_true', help='Force overwrite existing setup')
    
    args = parser.parse_args()
    
    # Create setup manager
    setup = AGIGovernanceSetup(args.path)
    
    # Check if already setup (unless force)
    if not args.force and (setup.config_path).exists():
        response = input("Setup already exists. Continue? (y/N): ")
        if response.lower() != 'y':
            print("Setup cancelled")
            return
    
    # Run setup
    success = setup.run_setup(args.mode)
    
    if success:
        print("\n✅ Setup completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Setup failed!")
        sys.exit(1)


if __name__ == '__main__':
    main()
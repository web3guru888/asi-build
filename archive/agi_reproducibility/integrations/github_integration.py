"""
GitHub Integration

Integration with GitHub for seamless experiment sharing, collaboration,
and version control within the AGI reproducibility platform.
"""

import json
import asyncio
import aiohttp
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from pathlib import Path
import base64

from ..core.config import PlatformConfig
from ..core.exceptions import *


class GitHubIntegration:
    """
    GitHub integration for AGI reproducibility platform.
    
    Features:
    - Automated experiment repository creation
    - Code synchronization with version control
    - Pull request creation for experiment sharing
    - Issue tracking for reproducibility problems
    - Release management for experiment versions
    - Collaboration workflow automation
    - Citation and attribution tracking
    - Integration with GitHub Actions for CI/CD
    """
    
    def __init__(self, config: PlatformConfig):
        self.config = config
        self.github_token = config.integrations.github_token
        self.api_base = "https://api.github.com"
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def initialize(self) -> None:
        """Initialize GitHub integration."""
        if not self.github_token:
            raise IntegrationError("GitHub token not configured")
        
        # Create HTTP session with authentication
        headers = {
            'Authorization': f'token {self.github_token}',
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': f'AGI-Reproducibility-Platform/{self.config.version}'
        }
        
        self.session = aiohttp.ClientSession(headers=headers)
        
        # Verify token and permissions
        await self._verify_authentication()
    
    async def _verify_authentication(self) -> None:
        """Verify GitHub authentication and permissions."""
        try:
            async with self.session.get(f"{self.api_base}/user") as response:
                if response.status != 200:
                    raise GitHubIntegrationError(f"GitHub authentication failed: {response.status}")
                
                user_data = await response.json()
                print(f"Authenticated as GitHub user: {user_data.get('login', 'unknown')}")
                
        except Exception as e:
            raise GitHubIntegrationError(f"Failed to verify GitHub authentication: {str(e)}")
    
    async def create_experiment_repository(self, experiment_id: str, 
                                         metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Create a GitHub repository for an experiment."""
        validate_experiment_id(experiment_id)
        
        repo_name = f"agi-experiment-{experiment_id}"
        
        # Repository configuration
        repo_config = {
            "name": repo_name,
            "description": f"AGI Experiment: {metadata.get('title', experiment_id)}",
            "private": False,  # Make public for reproducibility
            "has_issues": True,
            "has_projects": True,
            "has_wiki": True,
            "auto_init": True,
            "license_template": "mit",
            "topics": [
                "agi",
                "artificial-general-intelligence", 
                "reproducible-research",
                "experiment",
                metadata.get('agi_framework', '').lower(),
                metadata.get('research_area', '').lower()
            ]
        }
        
        # Remove empty topics
        repo_config["topics"] = [t for t in repo_config["topics"] if t]
        
        try:
            async with self.session.post(f"{self.api_base}/user/repos", json=repo_config) as response:
                if response.status == 201:
                    repo_data = await response.json()
                    
                    # Setup repository with initial content
                    await self._setup_experiment_repository(repo_data, experiment_id, metadata)
                    
                    return {
                        'repository_url': repo_data['html_url'],
                        'clone_url': repo_data['clone_url'],
                        'api_url': repo_data['url'],
                        'full_name': repo_data['full_name'],
                        'created_at': repo_data['created_at']
                    }
                else:
                    error_data = await response.json()
                    raise GitHubIntegrationError(f"Failed to create repository: {error_data.get('message', 'Unknown error')}")
        
        except Exception as e:
            raise GitHubIntegrationError(f"Repository creation failed: {str(e)}")
    
    async def _setup_experiment_repository(self, repo_data: Dict[str, Any], 
                                         experiment_id: str, metadata: Dict[str, Any]) -> None:
        """Setup experiment repository with initial content."""
        repo_full_name = repo_data['full_name']
        
        # Create README.md
        readme_content = self._generate_experiment_readme(experiment_id, metadata)
        await self._create_file(repo_full_name, "README.md", readme_content, "Initial experiment documentation")
        
        # Create experiment configuration
        config_content = json.dumps({
            'experiment_id': experiment_id,
            'platform_version': self.config.version,
            'metadata': metadata,
            'created_at': datetime.now(timezone.utc).isoformat()
        }, indent=2)
        await self._create_file(repo_full_name, "experiment_config.json", config_content, "Add experiment configuration")
        
        # Create directory structure
        structure_files = {
            "code/.gitkeep": "",
            "data/.gitkeep": "", 
            "results/.gitkeep": "",
            "docs/.gitkeep": "",
            "tests/.gitkeep": ""
        }
        
        for file_path, content in structure_files.items():
            await self._create_file(repo_full_name, file_path, content, f"Create {file_path.split('/')[0]} directory")
        
        # Create GitHub Actions workflow
        workflow_content = self._generate_ci_workflow(experiment_id, metadata)
        await self._create_file(repo_full_name, ".github/workflows/experiment.yml", workflow_content, "Add CI/CD workflow")
    
    def _generate_experiment_readme(self, experiment_id: str, metadata: Dict[str, Any]) -> str:
        """Generate README content for experiment repository."""
        return f"""# AGI Experiment: {metadata.get('title', experiment_id)}

## Overview
{metadata.get('description', 'AGI experiment for reproducible research')}

## Experiment Details
- **Experiment ID**: `{experiment_id}`
- **Author**: {metadata.get('author', 'Unknown')}
- **Framework**: {metadata.get('agi_framework', 'Unknown')}
- **Research Area**: {metadata.get('research_area', 'General')}
- **Created**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}

## Hypothesis
{metadata.get('hypothesis', 'No hypothesis specified')}

## Expected Outcomes
{chr(10).join(f"- {outcome}" for outcome in metadata.get('expected_outcomes', []))}

## Directory Structure
```
├── code/           # Experiment implementation
├── data/           # Input data and datasets  
├── results/        # Experiment outputs and results
├── docs/           # Documentation and analysis
├── tests/          # Test cases and validation
└── experiment_config.json  # Experiment configuration
```

## Reproducibility
This experiment is part of the AGI Reproducibility Platform and follows standardized practices for:
- Environment capture and containerization
- Deterministic execution
- Result validation and comparison
- Peer review and collaboration

## Usage

### Running the Experiment
```bash
# Clone the repository
git clone {metadata.get('repository_url', 'TBD')}
cd agi-experiment-{experiment_id}

# Install dependencies (if requirements.txt exists)
pip install -r requirements.txt

# Run the experiment
python code/main.py
```

### Reproducing Results
1. Use the provided Docker container for exact environment replication
2. Follow the execution steps in `docs/reproduction_guide.md`
3. Compare results with the reference outputs in `results/`

## Contributing
1. Fork the repository
2. Create a feature branch
3. Make your changes following the experiment protocols
4. Submit a pull request with detailed description

## Citation
If you use this experiment in your research, please cite:
```bibtex
@misc{{{experiment_id},
    title={{{metadata.get('title', experiment_id)}}},
    author={{{metadata.get('author', 'Unknown')}}},
    year={{{datetime.now().year}}},
    url={{{metadata.get('repository_url', 'TBD')}}},
    note={{AGI Reproducibility Platform}}
}}
```

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Reproducibility Platform
Generated by the AGI Reproducibility Platform v{self.config.version}
"""
    
    def _generate_ci_workflow(self, experiment_id: str, metadata: Dict[str, Any]) -> str:
        """Generate GitHub Actions CI/CD workflow."""
        framework = metadata.get('agi_framework', '').lower()
        
        # Customize workflow based on framework
        setup_steps = []
        if framework in ['hyperon', 'opencog']:
            setup_steps.extend([
                "      - name: Setup Hyperon Environment",
                "        run: |",
                "          # Add Hyperon-specific setup commands",
                "          echo 'Setting up Hyperon environment'"
            ])
        
        return f"""name: AGI Experiment CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v3
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
        pip install pytest numpy scipy
    
{chr(10).join(setup_steps)}
    
    - name: Run experiment tests
      run: |
        if [ -d tests ]; then pytest tests/; fi
    
    - name: Validate experiment configuration
      run: |
        python -c "import json; json.load(open('experiment_config.json'))"
    
    - name: Run reproducibility checks
      run: |
        # Add reproducibility validation commands
        echo "Running reproducibility checks for experiment {experiment_id}"
    
  reproducibility:
    runs-on: ubuntu-latest
    needs: test
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up AGI Reproducibility Platform
      run: |
        # Install platform tools
        pip install agi-reproducibility-platform
    
    - name: Run experiment
      run: |
        # Execute experiment with platform monitoring
        agi-repro run {experiment_id}
    
    - name: Validate results
      run: |
        # Validate experiment results
        agi-repro validate {experiment_id}
    
    - name: Upload results
      uses: actions/upload-artifact@v3
      with:
        name: experiment-results
        path: results/
"""
    
    async def _create_file(self, repo_full_name: str, file_path: str, 
                          content: str, commit_message: str) -> None:
        """Create a file in the GitHub repository."""
        encoded_content = base64.b64encode(content.encode()).decode()
        
        file_data = {
            "message": commit_message,
            "content": encoded_content
        }
        
        try:
            async with self.session.put(
                f"{self.api_base}/repos/{repo_full_name}/contents/{file_path}", 
                json=file_data
            ) as response:
                if response.status not in [200, 201]:
                    error_data = await response.json()
                    raise GitHubIntegrationError(f"Failed to create {file_path}: {error_data.get('message', 'Unknown error')}")
        
        except Exception as e:
            raise GitHubIntegrationError(f"File creation failed for {file_path}: {str(e)}")
    
    async def sync_experiment(self, experiment_id: str, repo_full_name: str,
                            experiment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronize experiment data with GitHub repository."""
        sync_results = {
            'files_updated': [],
            'files_created': [],
            'commit_sha': None
        }
        
        try:
            # Update experiment configuration
            config_content = json.dumps(experiment_data, indent=2)
            await self._update_file(repo_full_name, "experiment_config.json", config_content, 
                                  f"Update experiment configuration for {experiment_id}")
            sync_results['files_updated'].append('experiment_config.json')
            
            # Sync code files
            if 'code' in experiment_data:
                for filename, content in experiment_data['code'].items():
                    file_path = f"code/{filename}"
                    await self._update_file(repo_full_name, file_path, content,
                                          f"Update {filename}")
                    sync_results['files_updated'].append(file_path)
            
            # Sync results
            if 'results' in experiment_data:
                results_content = json.dumps(experiment_data['results'], indent=2)
                await self._update_file(repo_full_name, "results/latest.json", results_content,
                                      f"Update experiment results")
                sync_results['files_updated'].append('results/latest.json')
            
            return sync_results
            
        except Exception as e:
            raise GitHubIntegrationError(f"Experiment sync failed: {str(e)}")
    
    async def _update_file(self, repo_full_name: str, file_path: str,
                          content: str, commit_message: str) -> None:
        """Update an existing file in the repository."""
        # First, get the current file to get its SHA
        try:
            async with self.session.get(f"{self.api_base}/repos/{repo_full_name}/contents/{file_path}") as response:
                if response.status == 200:
                    file_data = await response.json()
                    current_sha = file_data['sha']
                elif response.status == 404:
                    # File doesn't exist, create it
                    await self._create_file(repo_full_name, file_path, content, commit_message)
                    return
                else:
                    raise GitHubIntegrationError(f"Failed to get file {file_path}: {response.status}")
            
            # Update the file
            encoded_content = base64.b64encode(content.encode()).decode()
            update_data = {
                "message": commit_message,
                "content": encoded_content,
                "sha": current_sha
            }
            
            async with self.session.put(
                f"{self.api_base}/repos/{repo_full_name}/contents/{file_path}",
                json=update_data
            ) as response:
                if response.status not in [200, 201]:
                    error_data = await response.json()
                    raise GitHubIntegrationError(f"Failed to update {file_path}: {error_data.get('message', 'Unknown error')}")
        
        except Exception as e:
            raise GitHubIntegrationError(f"File update failed for {file_path}: {str(e)}")
    
    async def create_pull_request(self, repo_full_name: str, experiment_id: str,
                                changes: Dict[str, Any]) -> Dict[str, Any]:
        """Create a pull request for experiment updates."""
        pr_title = f"Update AGI Experiment {experiment_id}"
        pr_body = f"""
## Experiment Update

**Experiment ID**: {experiment_id}
**Updated**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}

### Changes Made
{chr(10).join(f"- {change}" for change in changes.get('changes', []))}

### Reproducibility Status
- Environment: {'✓' if changes.get('environment_captured') else '✗'} Captured
- Results: {'✓' if changes.get('results_validated') else '✗'} Validated  
- Tests: {'✓' if changes.get('tests_passing') else '✗'} Passing

### Review Checklist
- [ ] Results are reproducible
- [ ] Code follows AGI platform standards
- [ ] Documentation is updated
- [ ] Tests pass successfully
- [ ] Environment is properly captured

Generated by AGI Reproducibility Platform v{self.config.version}
"""
        
        pr_data = {
            "title": pr_title,
            "body": pr_body,
            "head": "experiment-update",
            "base": "main"
        }
        
        try:
            async with self.session.post(f"{self.api_base}/repos/{repo_full_name}/pulls", json=pr_data) as response:
                if response.status == 201:
                    pr_data = await response.json()
                    return {
                        'pull_request_url': pr_data['html_url'],
                        'number': pr_data['number'],
                        'created_at': pr_data['created_at']
                    }
                else:
                    error_data = await response.json()
                    raise GitHubIntegrationError(f"Failed to create pull request: {error_data.get('message', 'Unknown error')}")
        
        except Exception as e:
            raise GitHubIntegrationError(f"Pull request creation failed: {str(e)}")
    
    async def create_release(self, repo_full_name: str, experiment_id: str,
                           version: str, results: Dict[str, Any]) -> Dict[str, Any]:
        """Create a GitHub release for experiment version."""
        release_data = {
            "tag_name": f"v{version}",
            "target_commitish": "main",
            "name": f"AGI Experiment {experiment_id} v{version}",
            "body": f"""
## AGI Experiment Release v{version}

**Experiment ID**: {experiment_id}
**Released**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}

### Results Summary
- **Validation Score**: {results.get('validation_score', 'N/A')}
- **Reproducibility**: {'✓ Verified' if results.get('reproducible', False) else '✗ Issues found'}
- **Performance**: {results.get('performance_metrics', {}).get('execution_time', 'N/A')}

### Reproducibility Information
This release includes complete environment capture and validation results for full experiment reproduction.

### Assets
- Experiment code and configuration
- Complete results and analysis
- Environment specification
- Reproduction instructions

Generated by AGI Reproducibility Platform v{self.config.version}
""",
            "draft": False,
            "prerelease": False
        }
        
        try:
            async with self.session.post(f"{self.api_base}/repos/{repo_full_name}/releases", json=release_data) as response:
                if response.status == 201:
                    release_data = await response.json()
                    return {
                        'release_url': release_data['html_url'],
                        'tag_name': release_data['tag_name'],
                        'created_at': release_data['created_at']
                    }
                else:
                    error_data = await response.json()
                    raise GitHubIntegrationError(f"Failed to create release: {error_data.get('message', 'Unknown error')}")
        
        except Exception as e:
            raise GitHubIntegrationError(f"Release creation failed: {str(e)}")
    
    async def search_experiments(self, query: str, framework: str = None) -> List[Dict[str, Any]]:
        """Search for AGI experiments on GitHub."""
        search_query = f"agi-experiment topic:agi topic:reproducible-research {query}"
        if framework:
            search_query += f" topic:{framework.lower()}"
        
        try:
            params = {
                'q': search_query,
                'sort': 'updated',
                'order': 'desc'
            }
            
            async with self.session.get(f"{self.api_base}/search/repositories", params=params) as response:
                if response.status == 200:
                    search_results = await response.json()
                    
                    experiments = []
                    for repo in search_results.get('items', []):
                        experiments.append({
                            'name': repo['name'],
                            'full_name': repo['full_name'],
                            'description': repo['description'],
                            'html_url': repo['html_url'],
                            'clone_url': repo['clone_url'],
                            'updated_at': repo['updated_at'],
                            'stars': repo['stargazers_count'],
                            'topics': repo.get('topics', [])
                        })
                    
                    return experiments
                else:
                    error_data = await response.json()
                    raise GitHubIntegrationError(f"Search failed: {error_data.get('message', 'Unknown error')}")
        
        except Exception as e:
            raise GitHubIntegrationError(f"Experiment search failed: {str(e)}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on GitHub integration."""
        try:
            if not self.session:
                return {
                    'status': 'unhealthy',
                    'error': 'Session not initialized',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            
            # Test API connectivity
            async with self.session.get(f"{self.api_base}/user") as response:
                api_accessible = response.status == 200
                
                if api_accessible:
                    user_data = await response.json()
                    return {
                        'status': 'healthy',
                        'authenticated_user': user_data.get('login'),
                        'api_accessible': True,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                else:
                    return {
                        'status': 'degraded',
                        'api_accessible': False,
                        'response_status': response.status,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
        
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    async def cleanup(self) -> None:
        """Cleanup GitHub integration resources."""
        if self.session:
            await self.session.close()
            self.session = None
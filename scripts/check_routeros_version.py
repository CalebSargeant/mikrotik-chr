#!/usr/bin/env python3
"""
RouterOS Version Checker for Kubernetes

This script checks for new MikroTik RouterOS releases and triggers a GitHub
workflow dispatch event when a new version is detected. Designed to run as a
Kubernetes CronJob.

Features:
- Check MikroTik download page for latest RouterOS version
- Compare with stored version in ConfigMap/file
- Authenticate using GitHub App (JWT + installation token)
- Trigger workflow dispatch event
- Comprehensive logging and error handling
"""

import os
import sys
import time
import json
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any

import requests
import jwt


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class RouterOSVersionChecker:
    """Check for new RouterOS versions and trigger GitHub workflows."""
    
    def __init__(
        self,
        github_app_id: str,
        github_private_key: str,
        github_repo: str,
        workflow_id: str,
        version_file: str = "/data/current_version.txt"
    ):
        """
        Initialize the version checker.
        
        Args:
            github_app_id: GitHub App ID
            github_private_key: GitHub App private key (PEM format)
            github_repo: Repository in format "owner/repo"
            workflow_id: Workflow filename or ID to trigger
            version_file: Path to file storing the current version
        """
        self.github_app_id = github_app_id
        self.github_private_key = github_private_key
        self.github_repo = github_repo
        self.workflow_id = workflow_id
        self.version_file = Path(version_file)
        self.mikrotik_download_url = "https://mikrotik.com/download"
        
    def get_latest_routeros_version(self) -> Optional[str]:
        """
        Fetch the latest RouterOS version from MikroTik's download page.
        
        Returns:
            Latest version string (e.g., "7.20.2") or None if failed
        """
        logger.info("Fetching latest RouterOS version from MikroTik...")
        
        try:
            response = requests.get(self.mikrotik_download_url, timeout=30)
            response.raise_for_status()
            
            # Parse the download page for CHR version
            # Looking for patterns like: chr-7.20.2.img.zip
            pattern = r'chr-(\d+\.\d+(?:\.\d+)?)\.img\.zip'
            matches = re.findall(pattern, response.text)
            
            if not matches:
                logger.error("Could not find RouterOS CHR version on download page")
                return None
            
            # Filter out beta/rc versions and get the latest stable
            stable_versions = [v for v in matches if 'beta' not in v.lower() and 'rc' not in v.lower()]
            
            if not stable_versions:
                logger.warning("No stable versions found, using all matches")
                stable_versions = matches
            
            # Sort versions and get the latest
            latest_version = sorted(stable_versions, key=lambda v: [int(x) for x in v.split('.')])[-1]
            
            logger.info(f"Latest RouterOS version found: {latest_version}")
            return latest_version
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch MikroTik download page: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error while fetching version: {e}")
            return None
    
    def get_current_version(self) -> Optional[str]:
        """
        Read the currently known version from storage.
        
        Returns:
            Current version string or None if not found
        """
        try:
            if self.version_file.exists():
                version = self.version_file.read_text().strip()
                logger.info(f"Current stored version: {version}")
                return version
            else:
                logger.info("No version file found, treating as first run")
                return None
        except Exception as e:
            logger.error(f"Error reading version file: {e}")
            return None
    
    def update_current_version(self, version: str) -> bool:
        """
        Update the stored version.
        
        Args:
            version: Version string to store
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure parent directory exists
            self.version_file.parent.mkdir(parents=True, exist_ok=True)
            
            self.version_file.write_text(version + "\n")
            logger.info(f"Updated stored version to: {version}")
            return True
        except Exception as e:
            logger.error(f"Error updating version file: {e}")
            return False
    
    def generate_jwt(self) -> str:
        """
        Generate a JWT for GitHub App authentication.
        
        Returns:
            JWT token string
        """
        logger.debug("Generating GitHub App JWT...")
        
        # JWT expires in 10 minutes (maximum allowed is 10 minutes)
        now = int(time.time())
        payload = {
            'iat': now - 60,  # Issued at (1 minute in the past to account for clock skew)
            'exp': now + 600,  # Expires in 10 minutes
            'iss': self.github_app_id  # GitHub App ID
        }
        
        # Generate JWT
        token = jwt.encode(payload, self.github_private_key, algorithm='RS256')
        logger.debug("JWT generated successfully")
        return token
    
    def get_installation_token(self, jwt_token: str) -> Optional[str]:
        """
        Exchange JWT for an installation access token.
        
        Args:
            jwt_token: GitHub App JWT
            
        Returns:
            Installation access token or None if failed
        """
        logger.info("Getting GitHub App installation token...")
        
        headers = {
            'Authorization': f'Bearer {jwt_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        try:
            # Get installations for this app
            response = requests.get(
                'https://api.github.com/app/installations',
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            installations = response.json()
            if not installations:
                logger.error("No installations found for this GitHub App")
                return None
            
            # Use the first installation (or find the one matching our repo)
            installation_id = installations[0]['id']
            logger.debug(f"Using installation ID: {installation_id}")
            
            # Get installation access token
            response = requests.post(
                f'https://api.github.com/app/installations/{installation_id}/access_tokens',
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            token_data = response.json()
            access_token = token_data['token']
            logger.info("Installation token obtained successfully")
            return access_token
            
        except requests.RequestException as e:
            logger.error(f"Failed to get installation token: {e}")
            if hasattr(e.response, 'text'):
                logger.error(f"Response: {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting installation token: {e}")
            return None
    
    def trigger_workflow(self, access_token: str, version: str) -> bool:
        """
        Trigger the GitHub workflow dispatch event.
        
        Args:
            access_token: GitHub installation access token
            version: RouterOS version that triggered the workflow
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Triggering workflow for RouterOS version {version}...")
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/vnd.github.v3+json',
            'Content-Type': 'application/json'
        }
        
        # Workflow dispatch payload
        payload = {
            'ref': 'main',  # Branch to run the workflow on
            'inputs': {
                'version': version
            }
        }
        
        url = f'https://api.github.com/repos/{self.github_repo}/actions/workflows/{self.workflow_id}/dispatches'
        
        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            logger.info(f"Workflow triggered successfully for version {version}")
            return True
            
        except requests.RequestException as e:
            logger.error(f"Failed to trigger workflow: {e}")
            if hasattr(e.response, 'text'):
                logger.error(f"Response: {e.response.text}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error triggering workflow: {e}")
            return False
    
    def run(self) -> int:
        """
        Main execution flow.
        
        Returns:
            Exit code (0 for success, 1 for failure)
        """
        logger.info("=" * 60)
        logger.info("RouterOS Version Checker - Starting")
        logger.info("=" * 60)
        
        try:
            # Get latest version from MikroTik
            latest_version = self.get_latest_routeros_version()
            if not latest_version:
                logger.error("Failed to fetch latest RouterOS version")
                return 1
            
            # Get current stored version
            current_version = self.get_current_version()
            
            # Check if we need to trigger a workflow
            if current_version == latest_version:
                logger.info(f"No new version detected (current: {current_version})")
                logger.info("No action needed")
                return 0
            
            logger.info(f"New version detected! Current: {current_version or 'None'}, Latest: {latest_version}")
            
            # Generate GitHub App JWT
            jwt_token = self.generate_jwt()
            
            # Get installation access token
            access_token = self.get_installation_token(jwt_token)
            if not access_token:
                logger.error("Failed to obtain GitHub installation token")
                return 1
            
            # Trigger workflow
            if not self.trigger_workflow(access_token, latest_version):
                logger.error("Failed to trigger workflow")
                return 1
            
            # Update stored version
            if not self.update_current_version(latest_version):
                logger.warning("Failed to update version file, but workflow was triggered")
            
            logger.info("=" * 60)
            logger.info("RouterOS Version Checker - Completed Successfully")
            logger.info("=" * 60)
            return 0
            
        except Exception as e:
            logger.error(f"Unexpected error in main execution: {e}", exc_info=True)
            return 1


def main():
    """Main entry point."""
    # Load configuration from environment variables
    github_app_id = os.getenv('GITHUB_APP_ID')
    github_private_key = os.getenv('GITHUB_PRIVATE_KEY')
    github_repo = os.getenv('GITHUB_REPO', 'CalebSargeant/mikrotik-chr')
    workflow_id = os.getenv('WORKFLOW_ID', 'build-chr.yml')
    version_file = os.getenv('VERSION_FILE', '/data/current_version.txt')
    
    # Validate required environment variables
    if not github_app_id:
        logger.error("GITHUB_APP_ID environment variable is required")
        sys.exit(1)
    
    if not github_private_key:
        logger.error("GITHUB_PRIVATE_KEY environment variable is required")
        sys.exit(1)
    
    # Create checker instance
    checker = RouterOSVersionChecker(
        github_app_id=github_app_id,
        github_private_key=github_private_key,
        github_repo=github_repo,
        workflow_id=workflow_id,
        version_file=version_file
    )
    
    # Run the checker
    exit_code = checker.run()
    sys.exit(exit_code)


if __name__ == '__main__':
    main()

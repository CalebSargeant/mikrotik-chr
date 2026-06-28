#!/usr/bin/env python3
"""
Basic tests for the RouterOS Version Checker

These tests verify the structure and basic functionality of the version checker
without requiring network access or GitHub credentials.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

import check_routeros_version


class TestRouterOSVersionChecker(unittest.TestCase):
    """Test cases for RouterOSVersionChecker class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.version_file = os.path.join(self.temp_dir, 'version.txt')
        
        self.checker = check_routeros_version.RouterOSVersionChecker(
            github_app_id="12345",
            github_private_key="dummy-key",
            github_repo="owner/repo",
            workflow_id="workflow.yml",
            version_file=self.version_file
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_initialization(self):
        """Test that the checker initializes correctly."""
        self.assertEqual(self.checker.github_app_id, "12345")
        self.assertEqual(self.checker.github_repo, "owner/repo")
        self.assertEqual(self.checker.workflow_id, "workflow.yml")
        self.assertEqual(str(self.checker.version_file), self.version_file)
    
    def test_get_current_version_no_file(self):
        """Test getting current version when file doesn't exist."""
        version = self.checker.get_current_version()
        self.assertIsNone(version)
    
    def test_update_and_get_current_version(self):
        """Test updating and retrieving the current version."""
        # Update version
        result = self.checker.update_current_version("7.20.2")
        self.assertTrue(result)
        
        # Read it back
        version = self.checker.get_current_version()
        self.assertEqual(version, "7.20.2")
    
    def test_update_current_version_creates_directory(self):
        """Test that update_current_version creates parent directories."""
        nested_file = os.path.join(self.temp_dir, 'subdir', 'version.txt')
        checker = check_routeros_version.RouterOSVersionChecker(
            github_app_id="12345",
            github_private_key="dummy-key",
            github_repo="owner/repo",
            workflow_id="workflow.yml",
            version_file=nested_file
        )
        
        result = checker.update_current_version("7.20.2")
        self.assertTrue(result)
        self.assertTrue(os.path.exists(nested_file))
    
    def test_version_comparison_logic(self):
        """Test the version comparison logic in run method."""
        # Set up a current version
        self.checker.update_current_version("7.20.1")
        
        # Mock the get_latest_routeros_version to return the same version
        with patch.object(self.checker, 'get_latest_routeros_version', return_value="7.20.1"):
            with patch.object(self.checker, 'generate_jwt', return_value="fake-jwt"):
                with patch.object(self.checker, 'get_installation_token', return_value="fake-token"):
                    with patch.object(self.checker, 'trigger_workflow', return_value=True) as mock_trigger:
                        result = self.checker.run()
                        
                        # Should return 0 (success) without triggering workflow
                        self.assertEqual(result, 0)
                        mock_trigger.assert_not_called()
    
    def test_new_version_detected(self):
        """Test that a new version triggers the workflow."""
        # Set up an old version
        self.checker.update_current_version("7.20.1")
        
        # Mock methods
        with patch.object(self.checker, 'get_latest_routeros_version', return_value="7.20.2"):
            with patch.object(self.checker, 'generate_jwt', return_value="fake-jwt"):
                with patch.object(self.checker, 'get_installation_token', return_value="fake-token"):
                    with patch.object(self.checker, 'trigger_workflow', return_value=True) as mock_trigger:
                        result = self.checker.run()
                        
                        # Should trigger workflow and return success
                        self.assertEqual(result, 0)
                        mock_trigger.assert_called_once_with("fake-token", "7.20.2")
                        
                        # Version should be updated
                        self.assertEqual(self.checker.get_current_version(), "7.20.2")
    
    @patch('check_routeros_version.requests.get')
    def test_get_latest_routeros_version_success(self, mock_get):
        """Test successful version fetching from MikroTik."""
        # Mock response
        mock_response = Mock()
        mock_response.text = '''
        <html>
            <a href="chr-7.20.2.img.zip">Download CHR 7.20.2</a>
            <a href="chr-7.20.1.img.zip">Download CHR 7.20.1</a>
            <a href="chr-7.19.6.img.zip">Download CHR 7.19.6</a>
        </html>
        '''
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        version = self.checker.get_latest_routeros_version()
        self.assertEqual(version, "7.20.2")
    
    @patch('check_routeros_version.requests.get')
    def test_get_latest_routeros_version_filters_beta(self, mock_get):
        """Test that beta versions are filtered out."""
        mock_response = Mock()
        mock_response.text = '''
        <html>
            <a href="chr-7.21beta1.img.zip">Download CHR 7.21 beta</a>
            <a href="chr-7.20.2.img.zip">Download CHR 7.20.2</a>
        </html>
        '''
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        version = self.checker.get_latest_routeros_version()
        self.assertEqual(version, "7.20.2")
    
    @patch('check_routeros_version.requests.get')
    def test_get_latest_routeros_version_network_error(self, mock_get):
        """Test handling of network errors."""
        mock_get.side_effect = Exception("Network error")
        
        version = self.checker.get_latest_routeros_version()
        self.assertIsNone(version)
    
    @patch('check_routeros_version.jwt.encode')
    def test_generate_jwt(self, mock_jwt_encode):
        """Test JWT generation."""
        mock_jwt_encode.return_value = "fake-jwt-token"
        
        token = self.checker.generate_jwt()
        
        self.assertEqual(token, "fake-jwt-token")
        mock_jwt_encode.assert_called_once()
        
        # Verify the payload structure
        call_args = mock_jwt_encode.call_args
        payload = call_args[0][0]
        self.assertIn('iat', payload)
        self.assertIn('exp', payload)
        self.assertIn('iss', payload)
        self.assertEqual(payload['iss'], "12345")
    
    @patch('check_routeros_version.requests.post')
    def test_trigger_workflow_success(self, mock_post):
        """Test successful workflow trigger."""
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        result = self.checker.trigger_workflow("fake-token", "7.20.2")
        
        self.assertTrue(result)
        mock_post.assert_called_once()
        
        # Verify the request structure
        call_args = mock_post.call_args
        self.assertIn('https://api.github.com/repos/owner/repo/actions/workflows/workflow.yml/dispatches', call_args[0])
    
    @patch('check_routeros_version.requests.post')
    def test_trigger_workflow_failure(self, mock_post):
        """Test workflow trigger failure handling."""
        mock_post.side_effect = Exception("API error")
        
        result = self.checker.trigger_workflow("fake-token", "7.20.2")
        
        self.assertFalse(result)


class TestMainFunction(unittest.TestCase):
    """Test cases for the main function."""
    
    @patch.dict(os.environ, {}, clear=True)
    def test_main_missing_required_env_vars(self):
        """Test that main exits if required env vars are missing."""
        with self.assertRaises(SystemExit) as cm:
            check_routeros_version.main()
        
        self.assertEqual(cm.exception.code, 1)
    
    @patch.dict(os.environ, {
        'GITHUB_APP_ID': '12345',
        'GITHUB_PRIVATE_KEY': 'dummy-key',
    })
    @patch('check_routeros_version.RouterOSVersionChecker')
    def test_main_with_env_vars(self, mock_checker_class):
        """Test main function with environment variables."""
        mock_checker = Mock()
        mock_checker.run.return_value = 0
        mock_checker_class.return_value = mock_checker
        
        with self.assertRaises(SystemExit) as cm:
            check_routeros_version.main()
        
        self.assertEqual(cm.exception.code, 0)
        mock_checker_class.assert_called_once()
        mock_checker.run.assert_called_once()


if __name__ == '__main__':
    unittest.main()

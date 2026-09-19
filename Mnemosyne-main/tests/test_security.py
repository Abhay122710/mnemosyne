import pytest
import tempfile
from pathlib import Path
from mnemosyne.memory.client import MemoryClient
from mnemosyne.utils.security_scanner import SecurityScanner

@pytest.fixture(autouse=True)
def mock_offline(monkeypatch):
    monkeypatch.setenv("MNEMOSYNE_OFFLINE", "1")

def test_heuristic_scan_secrets():
    content = """
    # Configuration
    api_key = "secret_api_key_value_12345"
    db_password = 'my_secure_db_password_123'
    dummy_key = "example_value"  # Should be ignored (placeholder keyword)
    """
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        client = MemoryClient(root)
        scanner = SecurityScanner(client)
        
        issues = scanner._run_heuristic_scan(content, "test.py")
        vuln_types = [i.vulnerability_type for i in issues]
        
        assert len(issues) == 2
        assert "Hardcoded Secret / API Key" in vuln_types

def test_heuristic_scan_sql_injection():
    content = """
    def get_user(user_id):
        # Vulnerable SQL query interpolation
        query = f"SELECT * FROM users WHERE id = {user_id}"
        db.execute(query)
    """
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        client = MemoryClient(root)
        scanner = SecurityScanner(client)
        
        issues = scanner._run_heuristic_scan(content, "test.py")
        vuln_types = [i.vulnerability_type for i in issues]
        
        assert len(issues) == 1
        assert "SQL Injection Risk" in vuln_types

def test_heuristic_scan_dangerous_functions():
    content = """
    # Dangerous eval
    user_input = "__import__('os').system('clear')"
    eval(user_input)
    """
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        client = MemoryClient(root)
        scanner = SecurityScanner(client)
        
        issues = scanner._run_heuristic_scan(content, "test.py")
        vuln_types = [i.vulnerability_type for i in issues]
        
        assert len(issues) == 1
        assert "eval() Execution" in vuln_types

def test_scan_file_offline():
    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        client = MemoryClient(root)
        scanner = SecurityScanner(client)
        
        # Write unsafe script to file
        unsafe_file = root / "unsafe.py"
        unsafe_file.write_text("""
        import subprocess
        
        api_key = "super_secret_api_key_123456"
        subprocess.Popen("ls -la", shell=True)
        """)
        
        issues = scanner.scan_file(unsafe_file)
        vuln_types = [i.vulnerability_type for i in issues]
        
        assert len(issues) == 2
        assert "Hardcoded Secret / API Key" in vuln_types
        assert "subprocess with shell=True" in vuln_types

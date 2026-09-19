import pytest
from pathlib import Path
import tempfile
from mnemosyne.memory.client import MemoryClient
from mnemosyne.memory.schemas import BugFixMemory, MemoryType
from mnemosyne.memory.consolidator import MemoryConsolidator

@pytest.fixture(autouse=True)
def mock_cognee(monkeypatch):
    monkeypatch.setenv("MNEMOSYNE_OFFLINE", "1")


def test_remember_and_recall_bug():
    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        client = MemoryClient(root)

        bug = BugFixMemory(
            file_path="services/user_service.py",
            title="Unchecked null pointer",
            root_cause="Missing null check on user object",
            fix_description="Added guard clause if user is None",
            severity="high"
        )
        rec = client.remember_bug(bug)
        assert rec.id.startswith("mem_bug_")

        recalled = client.recall("null check user", file_context="services/user_service.py")
        assert len(recalled) > 0
        assert recalled[0].id == rec.id

def test_reflect_consolidation():
    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        client = MemoryClient(root)

        bug1 = BugFixMemory(
            file_path="services/user_service.py",
            title="Null response crash",
            root_cause="Unchecked response.json()",
            fix_description="Check status 200"
        )
        client.remember_bug(bug1)

        consolidator = MemoryConsolidator(client)
        rules = consolidator.reflect()
        assert len(rules) > 0
        assert len(client.get_rules()) > 0

def test_forget_memory():
    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        client = MemoryClient(root)

        bug = BugFixMemory(
            file_path="services/payment_service.py",
            title="Payment gateway timeout",
            root_cause="Missing timeout parameter",
            fix_description="Set timeout=5.0"
        )
        rec = client.remember_bug(bug)
        assert len(client.list_memories()) == 1

        removed = client.forget(rec.id)
        assert rec.id in removed
        assert len(client.list_memories()) == 0

def test_remember_doc_and_improve():
    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        client = MemoryClient(root)

        rec = client.remember_doc("Architecture Decision", "Always use service layer for DB calls", file_path="architecture.md")
        assert rec.id.startswith("mem_doc_")
        assert client.improve() is True
        
        recalled = client.recall("service layer DB calls")
        assert len(recalled) > 0
        assert recalled[0].id == rec.id

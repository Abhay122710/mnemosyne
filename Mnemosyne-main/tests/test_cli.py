import pytest
from typer.testing import CliRunner
from mnemosyne.cli import app

runner = CliRunner()

def test_cli_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "Mnemosyne version" in result.stdout

def test_cli_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "init" in result.stdout
    assert "remember-bug" in result.stdout
    assert "remember" in result.stdout
    assert "improve" in result.stdout
    assert "ask" in result.stdout
    assert "reflect" in result.stdout
    assert "rules" in result.stdout
    assert "forget" in result.stdout
    assert "status" in result.stdout

def test_cli_config():
    result_show = runner.invoke(app, ["config", "show"])
    assert result_show.exit_code == 0
    assert "Mnemosyne Configuration Dashboard" in result_show.stdout

    result_set = runner.invoke(app, ["config", "set-cloud-key", "test-cognee-key-123"])
    assert result_set.exit_code == 0
    assert "Cognee Cloud API Key configured" in result_set.stdout

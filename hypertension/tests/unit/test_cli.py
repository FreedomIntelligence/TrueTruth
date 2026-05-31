import pytest
from typer.testing import CliRunner
from hypertensiondb.cli import app


runner = CliRunner()


@pytest.mark.unit
def test_cli_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.stdout


@pytest.mark.unit
def test_cli_help_lists_commands():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "ingest" in result.stdout
    assert "index" in result.stdout
    assert "lint" in result.stdout

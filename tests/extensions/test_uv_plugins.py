"""Tests for uv-managed invoke-toolkit plugin support."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from invoke_toolkit.extensions.uv_tools import (
    Plugin,
    UvTool,
    active_tool,
    add_command,
    install_arguments,
    parse_tool_list,
    receipt_requirement,
    receipt_requirements,
    reinstall_command,
    upgrade_command,
)


def test_parse_tool_list_handles_metadata_and_warnings(tmp_path: Path):
    output = f"""warning: Ignoring malformed tool glances
invoke-toolkit v0.0.69 [with: invoke-toolkit-litellm, other>=1] [extras: full] ({tmp_path})
- intk ({tmp_path}/bin/intk)
- invoke-toolkit ({tmp_path}/bin/invoke-toolkit)
ruff v0.15.6 ({tmp_path}/ruff)
- ruff ({tmp_path}/bin/ruff)
"""

    tools = parse_tool_list(output)

    assert [tool.name for tool in tools] == ["invoke-toolkit", "ruff"]
    assert tools[0].version == "0.0.69"
    assert tools[0].requirements == ("invoke-toolkit-litellm", "other>=1")
    assert tools[0].entrypoints == (
        tmp_path / "bin/intk",
        tmp_path / "bin/invoke-toolkit",
    )


def test_active_tool_matches_running_prefix(tmp_path: Path, monkeypatch):
    tool = UvTool("invoke-toolkit", "1.2.3", tmp_path)
    monkeypatch.setattr("invoke_toolkit.extensions.uv_tools.sys.prefix", str(tmp_path))

    assert active_tool((tool,)) == tool


def test_receipt_requirement_preserves_extras(tmp_path: Path):
    (tmp_path / "uv-receipt.toml").write_text(
        '[tool]\nrequirements = [{ name = "invoke-toolkit", extras = ["full"] }]\n',
        encoding="utf-8",
    )
    tool = UvTool("invoke-toolkit", "1.2.3", tmp_path)

    assert receipt_requirement(tool) == "invoke-toolkit[full]"


def test_install_arguments_use_editable_and_pinned_plugins(tmp_path: Path):
    plugins = (
        Plugin("invoke-toolkit-litellm", "0.1.0", tmp_path / "litellm"),
        Plugin("invoke-toolkit-other", "2.0.0"),
    )

    assert install_arguments(plugins) == [
        "--with-editable",
        str(tmp_path / "litellm"),
        "--with",
        "invoke-toolkit-other==2.0.0",
    ]


def test_reinstall_and_upgrade_commands(tmp_path: Path):
    tool = UvTool("invoke-toolkit", "1.2.3", tmp_path)
    plugin = Plugin("invoke-toolkit-litellm", "0.1.0")
    (tmp_path / "uv-receipt.toml").write_text(
        '[tool]\nrequirements = [{ name = "invoke-toolkit", extras = ["full"] }]\n',
        encoding="utf-8",
    )

    assert reinstall_command(tool, (plugin,)) == (
        "uv tool install --force --with invoke-toolkit-litellm==0.1.0 "
        "'invoke-toolkit[full]'"
    )
    assert upgrade_command(tool) == "uv tool upgrade invoke-toolkit"


def test_receipt_preserves_git_and_editable_sources(tmp_path: Path):
    (tmp_path / "uv-receipt.toml").write_text(
        """[tool]
requirements = [
  { name = "invoke-toolkit", specifier = ">=1" },
  { name = "invoke-toolkit-litellm", git = "https://github.com/D3f0/invoke-toolkit-litellm" },
  { name = "invoke-toolkit-local", editable = "/tmp/plugin" },
]
""",
        encoding="utf-8",
    )
    tool = UvTool("invoke-toolkit", "1.2.3", tmp_path)

    requirements = receipt_requirements(tool)
    assert requirements[0].value == "invoke-toolkit>=1"
    assert requirements[1].value == "git+https://github.com/D3f0/invoke-toolkit-litellm"
    assert requirements[2].option == "--with-editable"
    assert requirements[2].value == "/tmp/plugin"
    command = reinstall_command(tool, remove="invoke-toolkit-litellm")
    assert "git+https://github.com/D3f0/invoke-toolkit-litellm" not in command
    assert "/tmp/plugin" in command


def test_add_command_preserves_existing_receipt_requirements(tmp_path: Path):
    (tmp_path / "uv-receipt.toml").write_text(
        '[tool]\nrequirements = [{ name = "invoke-toolkit", git = "https://example.test/intk" }]\n',
        encoding="utf-8",
    )
    tool = UvTool("invoke-toolkit", "1.2.3", tmp_path)

    command = add_command(tool, editable="/tmp/plugin")
    assert "git+https://example.test/intk" in command
    assert "--with-editable /tmp/plugin" in command


def test_plugin_add_accepts_editable_only(tmp_path: Path):
    from invoke_toolkit.extensions.tasks import plugin

    ctx = MagicMock()
    tool = UvTool("invoke-toolkit", "1.2.3", tmp_path)
    (tmp_path / "uv-receipt.toml").write_text(
        '[tool]\nrequirements = [{ name = "invoke-toolkit" }]\n',
        encoding="utf-8",
    )
    with (
        patch.object(plugin, "active_tool", return_value=tool),
        patch.object(plugin, "installed_plugins", return_value=()),
    ):
        plugin.add.body(ctx, editable=str(tmp_path / "plugin"))

    assert "--with-editable" in ctx.run.call_args.args[0]
    assert str(tmp_path / "plugin") in ctx.run.call_args.args[0]


def test_create_script_prints_generated_code(tmp_path: Path, monkeypatch):
    from invoke_toolkit.extensions.tasks.create import script

    monkeypatch.chdir(tmp_path)
    ctx = MagicMock()
    script.body(ctx, name="tasks.py", location=".")

    assert (tmp_path / "tasks.py").exists()
    assert ctx.print_err.call_count == 4


def test_plugin_remove_reinstalls_without_selected_plugin(tmp_path: Path):
    from invoke_toolkit.extensions.tasks import plugin

    ctx = MagicMock()
    tool = UvTool("invoke-toolkit", "1.2.3", tmp_path)
    (tmp_path / "uv-receipt.toml").write_text(
        """[tool]
requirements = [
  { name = "invoke-toolkit" },
  { name = "invoke-toolkit-litellm", specifier = "==0.1.0" },
  { name = "invoke-toolkit-other", specifier = "==0.2.0" },
]
""",
        encoding="utf-8",
    )
    plugins = (
        Plugin("invoke-toolkit-litellm", "0.1.0"),
        Plugin("invoke-toolkit-other", "0.2.0"),
    )
    with (
        patch.object(plugin, "active_tool", return_value=tool),
        patch.object(plugin, "installed_plugins", return_value=plugins),
    ):
        plugin.remove.body(ctx, package="litellm")

    command = ctx.run.call_args.args[0]
    assert "invoke-toolkit-litellm" not in command
    assert "invoke-toolkit-other==0.2.0" in command


def _load_root_tasks():
    import importlib.util

    root = Path(__file__).parents[2] / "tasks.py"
    spec = importlib.util.spec_from_file_location("issue84_root_tasks", root)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_version_summary_is_empty_outside_uv_tool(monkeypatch):
    tasks = _load_root_tasks()
    monkeypatch.setattr(tasks, "active_tool", lambda: None)
    assert tasks._uv_tool_summary() == ""


def test_version_summary_lists_plugin_versions(tmp_path: Path, monkeypatch):
    tasks = _load_root_tasks()
    monkeypatch.setattr(
        tasks, "active_tool", lambda: UvTool("invoke-toolkit", "1.2.3", tmp_path)
    )
    monkeypatch.setattr(
        tasks,
        "installed_plugins",
        lambda: (Plugin("invoke-toolkit-litellm", "0.1.0"),),
    )

    assert tasks._uv_tool_summary() == (
        " (uv tool; plugins: invoke-toolkit-litellm 0.1.0)"
    )

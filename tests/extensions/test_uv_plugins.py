"""Tests for uv-managed invoke-toolkit plugin support."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from invoke_toolkit.extensions import uv_tools
from invoke_toolkit.extensions.uv_tools import (
    AmbiguousPluginError,
    Plugin,
    PluginNotFoundError,
    ReceiptError,
    RequirementSource,
    ToolReceipt,
    UvTool,
    active_tool,
    add_args,
    install_args,
    installed_plugins,
    link_args,
    load_receipt,
    parse_tool_list,
    remove_args,
    resolve_plugin,
    run_uv,
    update_plan,
)


def _receipt(tmp_path: Path) -> ToolReceipt:
    (tmp_path / "uv-receipt.toml").write_text(
        """[tool]
requirements = [
  { name = "invoke-toolkit", extras = ["full"], specifier = ">=1" },
  { name = "registry-plugin", specifier = "<3" },
  { name = "git-plugin", git = "https://example.test/plugin.git", rev = "v2" },
  { name = "url-plugin", url = "https://example.test/plugin.whl" },
  { name = "static-plugin", directory = "/plugins/static" },
  { name = "linked-plugin", editable = "/plugins/linked" },
]
""",
        encoding="utf-8",
    )
    return load_receipt(UvTool("invoke-toolkit", "1.2.3", tmp_path))


def test_parse_tool_list_handles_metadata_and_warnings(tmp_path: Path):
    output = f"""warning: Ignoring malformed tool glances
invoke-toolkit v0.0.69 [with: plugin, other>=1] [extras: full] ({tmp_path})
- intk ({tmp_path}/bin/intk)
ruff v0.15.6 ({tmp_path}/ruff)
- ruff ({tmp_path}/bin/ruff)
"""
    tools = parse_tool_list(output)
    assert [tool.name for tool in tools] == ["invoke-toolkit", "ruff"]
    assert tools[0].requirements == ("plugin", "other>=1")
    assert tools[0].entrypoints == (tmp_path / "bin/intk",)


def test_active_tool_matches_running_prefix(tmp_path: Path, monkeypatch):
    tool = UvTool("invoke-toolkit", "1.2.3", tmp_path)
    monkeypatch.setattr(uv_tools.sys, "prefix", str(tmp_path))
    assert active_tool((tool,)) == tool


def test_load_receipt_preserves_every_source_kind(tmp_path: Path):
    receipt = _receipt(tmp_path)
    assert receipt.base.value == "invoke-toolkit[full]>=1"
    assert [
        (item.name, item.value, item.source, item.editable)
        for item in receipt.supplemental
    ] == [
        ("registry-plugin", "registry-plugin<3", RequirementSource.REGISTRY, False),
        (
            "git-plugin",
            "git+https://example.test/plugin.git@v2",
            RequirementSource.GIT,
            False,
        ),
        (
            "url-plugin",
            "https://example.test/plugin.whl",
            RequirementSource.URL,
            False,
        ),
        ("static-plugin", "/plugins/static", RequirementSource.DIRECTORY, False),
        ("linked-plugin", "/plugins/linked", RequirementSource.EDITABLE, True),
    ]


def test_load_receipt_preserves_local_archive_path(tmp_path: Path):
    (tmp_path / "uv-receipt.toml").write_text(
        """[tool]
requirements = [
  { name = "invoke-toolkit" },
  { name = "archive-plugin", path = "/packages/archive-plugin.whl" },
]
""",
        encoding="utf-8",
    )

    receipt = load_receipt(UvTool("invoke-toolkit", "1", tmp_path))

    assert receipt.supplemental == (
        uv_tools.ReceiptRequirement(
            "archive-plugin",
            "/packages/archive-plugin.whl",
            RequirementSource.DIRECTORY,
        ),
    )
    assert "/packages/archive-plugin.whl" in install_args(receipt)


def test_plugin_list_works_when_receipt_is_unavailable(tmp_path: Path):
    from invoke_toolkit.extensions.tasks import plugin

    tool = UvTool("invoke-toolkit", "1", tmp_path)
    provider = Plugin("acme-plugin", "2", ("acme",), None)
    ctx = MagicMock()
    with (
        patch.object(plugin, "active_tool", return_value=tool),
        patch.object(plugin, "load_receipt", side_effect=ReceiptError("missing")),
        patch.object(plugin, "installed_plugins", return_value=(provider,)),
    ):
        plugin.list_.body(ctx)  # type: ignore[attr-defined]

    ctx.print.assert_any_call("- acme-plugin v2 [acme] (source unavailable)")


def test_load_receipt_preserves_extras_on_direct_sources(tmp_path: Path):
    (tmp_path / "uv-receipt.toml").write_text(
        """[tool]
requirements = [
  { name = "invoke-toolkit" },
  { name = "git-plugin", extras = ["feature"], git = "https://example.test/plugin.git" },
  { name = "url-plugin", extras = ["speed"], url = "https://example.test/plugin.whl" },
  { name = "local-plugin", extras = ["dev"], directory = "/plugins/local" },
  { name = "linked-plugin", extras = ["dev"], editable = "/plugins/linked" },
]
""",
        encoding="utf-8",
    )

    receipt = load_receipt(UvTool("invoke-toolkit", "1", tmp_path))

    assert [item.value for item in receipt.supplemental] == [
        "git-plugin[feature] @ git+https://example.test/plugin.git",
        "url-plugin[speed] @ https://example.test/plugin.whl",
        "local-plugin[dev] @ file:///plugins/local",
        "linked-plugin[dev] @ file:///plugins/linked",
    ]


@pytest.mark.parametrize(
    "contents, message",
    [
        (None, "Could not read"),
        ("not = [valid", "Could not parse"),
        ("[tool]\nrequirements = []\n", "does not contain requirements"),
        (
            '[tool]\nrequirements = [{ name = "invoke-toolkit" }, { name = "invoke_toolkit" }]\n',
            "exactly one base",
        ),
    ],
)
def test_invalid_receipt_is_rejected(
    tmp_path: Path, contents: str | None, message: str
):
    if contents is not None:
        (tmp_path / "uv-receipt.toml").write_text(contents, encoding="utf-8")
    with pytest.raises(ReceiptError, match=message):
        load_receipt(UvTool("invoke-toolkit", "1", tmp_path))


def test_install_args_replays_receipt_and_refreshes_selected_plugins(tmp_path: Path):
    receipt = _receipt(tmp_path)
    assert install_args(
        receipt,
        upgrade=("git-plugin",),
        reinstall=("git-plugin", "static-plugin"),
    ) == [
        "uv",
        "tool",
        "install",
        "--force",
        "--with",
        "registry-plugin<3",
        "--with",
        "git+https://example.test/plugin.git@v2",
        "--with",
        "https://example.test/plugin.whl",
        "--with",
        "/plugins/static",
        "--with-editable",
        "/plugins/linked",
        "--upgrade-package",
        "git-plugin",
        "--reinstall-package",
        "git-plugin",
        "--reinstall-package",
        "static-plugin",
        "invoke-toolkit[full]>=1",
    ]


class FakeEntryPoints(list):
    def select(self, *, group: str):
        assert group == "invoke_toolkit.collection"
        return self


def _entry_point(name: str, distribution: str, version: str = "1"):
    dist = SimpleNamespace(metadata={"Name": distribution}, version=version)
    return SimpleNamespace(name=name, dist=dist)


def test_installed_plugins_uses_collection_entrypoint_owner(monkeypatch):
    entry_points = FakeEntryPoints(
        [
            _entry_point("release", "acme-automation", "2.1"),
            _entry_point("deploy", "acme-automation", "2.1"),
        ]
    )
    monkeypatch.setattr(
        uv_tools.importlib.metadata, "entry_points", lambda: entry_points
    )
    assert installed_plugins() == (
        Plugin("acme-automation", "2.1", ("deploy", "release"), None),
    )


def test_prefixed_distribution_without_entrypoint_is_not_a_plugin(monkeypatch):
    monkeypatch.setattr(
        uv_tools.importlib.metadata, "entry_points", lambda: FakeEntryPoints()
    )
    assert installed_plugins() == ()


def test_resolve_plugin_accepts_distribution_or_entrypoint():
    plugin = Plugin("acme-automation", "2.1", ("deploy", "release"), None)
    assert resolve_plugin((plugin,), "ACME_automation") is plugin
    assert resolve_plugin((plugin,), "deploy") is plugin


def test_resolve_plugin_reports_missing_and_ambiguous_names():
    plugins = (
        Plugin("acme-one", "1", ("deploy",), None),
        Plugin("acme-two", "1", ("deploy",), None),
    )
    with pytest.raises(AmbiguousPluginError, match="acme-one.*acme-two"):
        resolve_plugin(plugins, "deploy")
    with pytest.raises(PluginNotFoundError, match="missing"):
        resolve_plugin(plugins, "missing")


def test_add_and_link_preserve_existing_requirements(tmp_path: Path):
    receipt = _receipt(tmp_path)
    added = add_args(receipt, "git+https://example.test/new.git")
    assert added[-3:] == [
        "--with",
        "git+https://example.test/new.git",
        "invoke-toolkit[full]>=1",
    ]
    plugin_path = tmp_path / "plugin with spaces"
    plugin_path.mkdir()
    linked = link_args(receipt, plugin_path)
    assert linked[-3:] == [
        "--with-editable",
        str(plugin_path.resolve()),
        "invoke-toolkit[full]>=1",
    ]
    with pytest.raises(ValueError, match="existing directory"):
        link_args(receipt, tmp_path / "missing")


def test_remove_and_update_preserve_unrelated_requirements(tmp_path: Path):
    receipt = _receipt(tmp_path)
    static = Plugin("static-plugin", "1", ("static",), receipt.supplemental[3])
    linked = Plugin("linked-plugin", "1", ("linked",), receipt.supplemental[4])

    removed = remove_args(receipt, static)
    assert "/plugins/static" not in removed
    assert "registry-plugin<3" in removed
    assert "/plugins/linked" in removed

    named = update_plan(receipt, (static, linked), "static")
    assert named.updated == (static,)
    assert named.skipped == ()
    assert named.args is not None
    assert ["--upgrade-package", "static-plugin"] == named.args[-5:-3]
    assert ["--reinstall-package", "static-plugin"] == named.args[-3:-1]

    all_plugins = update_plan(receipt, (static, linked))
    assert all_plugins.updated == (static,)
    assert all_plugins.skipped == (linked,)

    editable = update_plan(receipt, (linked,), "linked")
    assert editable.args is None
    assert editable.skipped == (linked,)


def test_remove_rejects_transitive_plugin(tmp_path: Path):
    receipt = _receipt(tmp_path)
    plugin = Plugin("transitive-plugin", "1", ("transitive",), None)
    with pytest.raises(ReceiptError, match="direct supplemental requirement"):
        remove_args(receipt, plugin)


def test_run_uv_uses_argument_vector():
    with patch.object(uv_tools.subprocess, "run") as subprocess_run:
        subprocess_run.return_value.returncode = 7
        assert run_uv(["uv", "tool", "install", "a path"]) == 7
    subprocess_run.assert_called_once_with(
        ["uv", "tool", "install", "a path"], check=False
    )


def test_plugin_name_completion_filters_direct_plugins(tmp_path: Path):
    from invoke_toolkit.extensions.tasks import plugin

    receipt = _receipt(tmp_path)
    plugins = (
        Plugin("static-plugin", "1", ("static",), receipt.supplemental[3]),
        Plugin("linked-plugin", "1", ("linked",), receipt.supplemental[4]),
        Plugin("transitive-plugin", "1", ("transitive",), None),
    )
    with patch.object(
        plugin, "_plugin_state", return_value=(MagicMock(), receipt, plugins)
    ):
        assert plugin._complete_plugin_names(MagicMock(), "st") == ["static-plugin"]
        assert plugin._complete_plugin_names(MagicMock(), "") == [
            "linked-plugin",
            "static-plugin",
        ]


def test_plugin_name_completion_returns_empty_when_state_is_unavailable():
    from invoke_toolkit.extensions.tasks import plugin

    with patch.object(plugin, "_plugin_state", side_effect=ReceiptError("missing")):
        assert plugin._complete_plugin_names(MagicMock(), "") == []


def test_remove_and_update_attach_native_completion_callback():
    from invoke_toolkit.extensions.tasks import plugin

    remove_callbacks = getattr(plugin.remove, "_completion_callbacks", {})
    update_callbacks = getattr(plugin.update, "_completion_callbacks", {})
    assert remove_callbacks["name"] is plugin._complete_plugin_names
    assert update_callbacks["name"] is plugin._complete_plugin_names


def test_plugin_tasks_run_plans_and_report_editable_skip(tmp_path: Path):
    from invoke_toolkit.extensions.tasks import plugin

    receipt = _receipt(tmp_path)
    linked = Plugin("linked-plugin", "1", ("linked",), receipt.supplemental[4])
    ctx = MagicMock()
    with (
        patch.object(
            plugin,
            "_active_state",
            return_value=(UvTool("invoke-toolkit", "1", tmp_path), receipt),
        ),
        patch.object(plugin, "run_uv", return_value=0) as execute,
    ):
        plugin.add.body(ctx, source="acme-plugin>=2")  # type: ignore[attr-defined]
    execute.assert_called_once_with(add_args(receipt, "acme-plugin>=2"))

    ctx.reset_mock()
    with (
        patch.object(
            plugin,
            "_plugin_state",
            return_value=(UvTool("invoke-toolkit", "1", tmp_path), receipt, (linked,)),
        ),
        patch.object(plugin, "run_uv", return_value=0) as execute,
    ):
        plugin.update.body(ctx, name="")  # type: ignore[attr-defined]
    execute.assert_not_called()
    ctx.print.assert_any_call("Skipped editable plugin: linked-plugin")


def test_plugin_task_propagates_uv_failure(tmp_path: Path):
    from invoke_toolkit.extensions.tasks import plugin

    receipt = _receipt(tmp_path)
    ctx = MagicMock()
    with (
        patch.object(
            plugin,
            "_active_state",
            return_value=(UvTool("invoke-toolkit", "1", tmp_path), receipt),
        ),
        patch.object(plugin, "run_uv", return_value=2),
    ):
        plugin.add.body(ctx, source="acme-plugin")  # type: ignore[attr-defined]
    ctx.rich_exit.assert_called_once_with("uv tool install failed", exit_code=2)

from invoke_toolkit.program import InvokeToolkitProgram


def test_import_from_git_repo(monkeypatch, tmp_path_factory):
    breakpoint()
    plugin_dir_ = tmp_path_factory.mktemp("plugin_dir")
    plugin = tmp_path_factory.mktemp("plugin_for_test")
    workdir = tmp_path_factory.mktemp("work_dir")

    def plugin_dir(*args):
        return plugin_dir_

    monkeypatch.setattr(InvokeToolkitProgram, "plugin_dir", plugin_dir)
    program = InvokeToolkitProgram()
    program.run(["--with", str(plugin)])
    breakpoint()

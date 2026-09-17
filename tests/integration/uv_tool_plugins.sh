#!/bin/sh
export UV_DYNAMIC_VERSIONING_BYPASS=0.0.0
set -eu

rm -rf /work
mkdir -p /work
cp -R /repo /work/invoke-toolkit
uv tool install /work/invoke-toolkit
export PATH="/root/.local/bin:$PATH"

make_plugin() {
    directory=$1
    distribution=$2
    module=$3
    entrypoint=$4
    marker=$5
    mkdir -p "$directory/$module"
    cat >"$directory/pyproject.toml" <<EOF
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "$distribution"
version = "0.1.0"

[project.entry-points."invoke_toolkit.collection"]
$entrypoint = "$module:collection"
EOF
    cat >"$directory/$module/__init__.py" <<EOF
from invoke_toolkit import Collection, task

@task
def marker(ctx):
    print("$marker")

collection = Collection("$entrypoint")
collection.add_task(marker)
EOF
}

make_plugin /work/static-plugin fixture-static-plugin fixture_static static STATIC_V1
make_plugin /work/linked-plugin fixture-linked-plugin fixture_linked linked LINKED_V1

intk -x plugin.add /work/static-plugin
intk -x plugin.link /work/linked-plugin
uv run --no-project --with pexpect /work/invoke-toolkit/tests/integration/pty_plugin_completion.py
intk -x static.marker | grep -F STATIC_V1
intk -x linked.marker | grep -F LINKED_V1

make_plugin /work/static-plugin fixture-static-plugin fixture_static static STATIC_V2
intk -x static.marker | grep -F STATIC_V1
intk -x plugin.update --name static
intk -x static.marker | grep -F STATIC_V2

make_plugin /work/linked-plugin fixture-linked-plugin fixture_linked linked LINKED_V2
intk -x linked.marker | grep -F LINKED_V2
intk -x plugin.update | tee /tmp/update.out
grep -F "Skipped editable plugin: fixture-linked-plugin" /tmp/update.out

intk -x plugin.remove static
if intk -x -lp 2>&1 | grep -F "static"; then
    echo "static plugin remained after removal" >&2
    exit 1
fi
intk -x linked.marker | grep -F LINKED_V2

if uv run --project /work/invoke-toolkit intk -x plugin.add example-plugin >/tmp/rejected.out 2>&1; then
    echo "non-tool mutation unexpectedly succeeded" >&2
    exit 1
fi
grep -F "Could not detect an active uv tool installation" /tmp/rejected.out

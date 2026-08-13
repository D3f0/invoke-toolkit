"""Tests for typed, deferred task Field defaults."""

from pathlib import Path
from typing import Annotated
from unittest.mock import Mock

import pytest
from invoke.exceptions import Exit

from invoke_toolkit import Context, Field, FieldResolutionRequest, task
from invoke_toolkit.collections import ToolkitCollection
from invoke_toolkit.field_resolvers import resolve_field_references
from invoke_toolkit.testing import TestingToolkitProgram
from invoke_toolkit.tasks.types import _FileCompletionMarker


def run_task(task_object, *argv: str) -> None:
    collection = ToolkitCollection()
    collection.add_task(task_object)  # type: ignore[arg-type]
    task_name = task_object.name.replace("_", "-")
    TestingToolkitProgram(namespace=collection).run(["", task_name, *argv])


def test_field_literal_and_factory_defaults_receive_context():
    received: list[tuple[str, str, Context]] = []

    def factory(ctx: Context) -> str:
        return f"configured-{ctx.config.get('marker', 'missing')}"

    @task
    def sample(
        ctx: Context,
        literal: str = Field(default="static"),
        dynamic: str = Field(default_factory=factory),
    ) -> None:
        received.append((literal, dynamic, ctx))

    collection = ToolkitCollection()
    collection.configure({"marker": "value"})
    collection.add_task(sample)  # type: ignore[arg-type]
    TestingToolkitProgram(namespace=collection).run(["", "sample"])

    assert received[0][0:2] == ("static", "configured-value")
    assert isinstance(received[0][2], Context)


def test_explicit_values_bypass_field_factory():
    factory = Mock(return_value="default")
    received: list[str] = []

    @task
    def sample(ctx: Context, value: str = Field(default_factory=factory)) -> None:
        received.append(value)

    run_task(sample, "--value", "explicit")
    assert received == ["explicit"]
    factory.assert_not_called()


def test_field_uses_annotation_as_parser_kind():
    @task
    def sample(ctx: Context, count: int = Field(default=4)) -> None: ...

    argument = sample.get_arguments()[0]  # type: ignore[attr-defined]
    assert argument.kind is int


def test_required_field_is_positional():
    @task
    def sample(ctx: Context, value: str = Field()) -> None: ...

    argument = sample.get_arguments()[0]  # type: ignore[attr-defined]
    assert argument.positional
    assert argument.default is None


def test_field_rejects_two_default_sources():
    with pytest.raises(TypeError, match="either default or default_factory"):
        Field(  # type: ignore[call-overload]
            default="value", default_factory=lambda ctx: "other"
        )


def test_uri_fields_are_batched_by_scheme(monkeypatch):
    calls: list[tuple[FieldResolutionRequest, ...]] = []

    def resolver(ctx, requests):
        calls.append(requests)
        return {
            request.parameter: f"resolved-{request.parameter}" for request in requests
        }

    entry_point = Mock(name="entry_point")
    entry_point.name = "op"
    monkeypatch.setattr(
        "invoke_toolkit.field_resolvers._load_resolver",
        lambda scheme: (resolver, entry_point),
    )
    received: list[tuple[str, str]] = []

    @task
    def sample(
        ctx: Context,
        username: str = Field(default="op://Vault/user"),
        password: str = Field(default="op://Vault/password"),
    ) -> None:
        received.append((username, password))

    run_task(sample)
    assert received == [("resolved-username", "resolved-password")]
    assert len(calls) == 1
    assert [request.parameter for request in calls[0]] == ["username", "password"]


def test_unavailable_uri_provider_warns_and_exits_safely(monkeypatch):
    monkeypatch.setattr(
        "invoke_toolkit.field_resolvers._load_resolver", lambda scheme: (None, None)
    )
    ctx = Context()
    with pytest.warns(RuntimeWarning, match="No field provider.*'op'"):
        with pytest.raises(Exit) as raised:
            resolve_field_references(
                ctx, {"secret": "op://Vault/secret"}, {"secret": str}
            )
    assert "op://Vault/secret" not in str(raised.value)


def test_provider_result_keys_are_validated(monkeypatch):
    resolver = Mock(return_value={})
    entry_point = Mock()
    entry_point.name = "op"
    monkeypatch.setattr(
        "invoke_toolkit.field_resolvers._load_resolver",
        lambda scheme: (resolver, entry_point),
    )
    with pytest.raises(Exit, match="invalid argument keys"):
        resolve_field_references(
            Context(), {"secret": "op://Vault/secret"}, {"secret": str}
        )


def test_path_field_keeps_file_completion_and_converts_value(tmp_path, monkeypatch):
    config_file = tmp_path / "config.yml"
    config_file.write_text("key: value", encoding="utf-8")
    received: list[Path] = []

    @task
    def sample(
        ctx: Context,
        config: Annotated[
            Path,
            "Config file",
            _FileCompletionMarker(exists=True, dir_okay=False),
        ] = Field(default_factory=lambda ctx: config_file),
    ) -> None:
        received.append(config)

    marker = sample._file_completion_markers["config"]  # type: ignore[attr-defined]
    assert marker.file_okay and not marker.dir_okay
    run_task(sample)
    assert received == [config_file]
    assert isinstance(received[0], Path)


def test_path_uri_provider_can_return_path(tmp_path, monkeypatch):
    output = tmp_path / "private-config"
    output.write_text("secret", encoding="utf-8")

    def resolver(ctx, requests):
        assert requests[0].annotation is Path
        return {"config": output}

    entry_point = Mock()
    entry_point.name = "op"
    monkeypatch.setattr(
        "invoke_toolkit.field_resolvers._load_resolver",
        lambda scheme: (resolver, entry_point),
    )
    received: list[Path] = []

    @task
    def sample(
        ctx: Context,
        config: Annotated[
            Path, _FileCompletionMarker(exists=True, dir_okay=False)
        ] = Field(default="op://Vault/config"),
    ) -> None:
        received.append(config)

    run_task(sample)
    assert received == [output]


def test_direct_python_call_uses_factory_and_explicit_kwarg_wins():
    factory = Mock(return_value="factory")
    received: list[str] = []

    @task
    def sample(ctx: Context, value: str = Field(default_factory=factory)) -> None:
        received.append(value)

    sample(Context())
    sample(Context(), value="explicit")
    assert received == ["factory", "explicit"]
    factory.assert_called_once()


def test_enum_literal_and_optional_fields_materialize():
    from enum import Enum
    from typing import Literal

    class Mode(str, Enum):
        FAST = "fast"

    received: list[tuple[Mode, str, str | None]] = []

    @task
    def sample(
        ctx: Context,
        mode: Mode = Field(default="fast"),
        level: Literal["low", "high"] = Field(default="high"),
        note: str | None = Field(default=None),
    ) -> None:
        received.append((mode, level, note))

    run_task(sample)
    assert received == [(Mode.FAST, "high", None)]


def test_factory_produced_uri_is_resolved(monkeypatch):
    resolver = Mock(return_value={"secret": "resolved"})  # pragma: allowlist secret
    entry_point = Mock()
    entry_point.name = "op"
    monkeypatch.setattr(
        "invoke_toolkit.field_resolvers._load_resolver",
        lambda scheme: (resolver, entry_point),
    )
    received: list[str] = []

    @task
    def sample(
        ctx: Context,
        secret: str = Field(default_factory=lambda current: "op://Vault/secret"),
    ) -> None:
        received.append(secret)

    run_task(sample)
    assert received == ["resolved"]
    resolver.assert_called_once()


def test_separate_schemes_are_resolved_in_separate_batches(monkeypatch):
    calls: list[tuple[str, list[str]]] = []

    def load(scheme):
        def resolver(ctx, requests):
            calls.append((scheme, [request.parameter for request in requests]))
            return {request.parameter: f"{scheme}-value" for request in requests}

        entry_point = Mock()
        entry_point.name = scheme
        return resolver, entry_point

    monkeypatch.setattr("invoke_toolkit.field_resolvers._load_resolver", load)

    @task
    def sample(
        ctx: Context,
        one: str = Field(default="op://one"),
        two: str = Field(default="bw://two"),
    ) -> None: ...

    run_task(sample)
    assert calls == [("op", ["one"]), ("bw", ["two"])]


def test_field_materialization_precedes_cache_key(tmp_path, monkeypatch):
    values = iter(["first", "second"])
    calls: list[str] = []

    @task(cache=True)
    def sample(
        ctx: Context,
        value: str = Field(default_factory=lambda current: next(values)),
    ) -> str:
        calls.append(value)
        return value

    monkeypatch.setattr(
        "invoke_toolkit.tasks.cache.get_cache_directory", lambda: tmp_path
    )
    sample(Context())
    sample(Context())
    assert calls == ["first", "second"]


def test_resolver_runtime_failure_hides_reference(monkeypatch):
    def resolver(ctx, requests):
        raise RuntimeError("secret-value")

    entry_point = Mock()
    entry_point.name = "op"
    monkeypatch.setattr(
        "invoke_toolkit.field_resolvers._load_resolver",
        lambda scheme: (resolver, entry_point),
    )
    with pytest.raises(Exit) as raised:
        resolve_field_references(
            Context(), {"secret": "op://Vault/sensitive"}, {"secret": str}
        )
    message = str(raised.value)
    assert "secret-value" not in message
    assert "op://Vault/sensitive" not in message


def test_entry_points_are_sorted_deterministically(monkeypatch):
    from invoke_toolkit import field_resolvers

    first = Mock()
    first.name = "op"
    first.value = "z_provider:resolve"
    second = Mock()
    second.name = "op"
    second.value = "a_provider:resolve"
    discovered = Mock()
    discovered.select.return_value = [first, second]
    monkeypatch.setattr(field_resolvers, "entry_points", lambda: discovered)
    field_resolvers.reset_field_resolver_cache()
    assert field_resolvers._resolver_entry_points() == (second, first)
    field_resolvers.reset_field_resolver_cache()


def test_postponed_annotation_controls_field_parser_kind():
    from tests.fixtures.future_fields import future_count, received

    received.clear()
    assert future_count.get_arguments()[0].kind is int  # type: ignore[attr-defined]
    run_task(future_count, "--count", "7")
    assert received == [7]


def test_required_field_uses_annotation_parser_kind():
    received: list[int] = []

    @task
    def sample(ctx: Context, count: int = Field()) -> None:
        received.append(count)

    assert sample.get_arguments()[0].kind is int  # type: ignore[attr-defined]
    run_task(sample, "7")
    assert received == [7]


def test_iterable_field_is_rejected_early():
    with pytest.raises(TypeError, match="iterable parameter"):

        @task(iterable=["values"])
        def sample(
            ctx: Context, values: list[str] = Field(default_factory=list)
        ) -> None: ...

        sample.get_arguments()


def test_non_string_provider_keys_raise_safe_exit(monkeypatch):
    resolver = Mock(return_value={1: "secret"})
    entry_point = Mock()
    entry_point.name = "op"
    monkeypatch.setattr(
        "invoke_toolkit.field_resolvers._load_resolver",
        lambda scheme: (resolver, entry_point),
    )
    with pytest.raises(Exit, match="non-string argument keys"):
        resolve_field_references(
            Context(), {"secret": "op://Vault/secret"}, {"secret": str}
        )


def test_help_listing_and_completion_do_not_materialize_field(
    tmp_path, monkeypatch, capsys
):
    factory = Mock(return_value=tmp_path / "generated.txt")
    resolver = Mock()
    monkeypatch.setattr(
        "invoke_toolkit.field_resolvers._load_resolver",
        lambda scheme: (resolver, Mock(name="provider")),
    )
    (tmp_path / "candidate.txt").write_text("candidate", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    @task
    def sample(
        ctx: Context,
        config: Annotated[
            Path, _FileCompletionMarker(exists=False, dir_okay=False)
        ] = Field(default_factory=factory),
    ) -> None: ...

    collection = ToolkitCollection()
    collection.add_task(sample)  # type: ignore[arg-type]
    TestingToolkitProgram(namespace=collection).run(["", "sample", "--help"])
    TestingToolkitProgram(namespace=collection).run(["", "--list"])
    TestingToolkitProgram(namespace=collection).run(
        ["intk", "--complete", "--", "intk", "sample", "--config"]
    )
    output = capsys.readouterr().out
    assert "candidate.txt" in output
    factory.assert_not_called()
    resolver.assert_not_called()


def test_broken_resolver_entry_point_warns_and_uses_next(monkeypatch):
    from invoke_toolkit import field_resolvers

    broken = Mock()
    broken.name = "op"
    broken.value = "broken:resolve"
    broken.load.side_effect = RuntimeError("load failure")  # pragma: allowlist secret
    working = Mock()
    working.name = "op"
    working.value = "working:resolve"
    resolver = Mock(return_value={"secret": "resolved"})  # pragma: allowlist secret
    working.load.return_value = resolver
    monkeypatch.setattr(
        field_resolvers, "_resolver_entry_points", lambda: (broken, working)
    )
    with pytest.warns(RuntimeWarning) as warnings_seen:
        loaded, entry_point = field_resolvers._load_resolver("op")
    assert loaded is resolver
    assert entry_point is working
    assert "sensitive-load-detail" not in str(warnings_seen[0].message)


def test_non_callable_resolver_entry_point_warns(monkeypatch):
    from invoke_toolkit import field_resolvers

    entry_point = Mock()
    entry_point.name = "op"
    entry_point.value = "bad:value"
    entry_point.load.return_value = object()
    monkeypatch.setattr(
        field_resolvers, "_resolver_entry_points", lambda: (entry_point,)
    )
    with pytest.warns(RuntimeWarning, match="not callable"):
        assert field_resolvers._load_resolver("op") == (None, None)


def test_identical_materialized_values_reuse_cache(tmp_path, monkeypatch):
    calls: list[str] = []

    @task(cache=True)
    def sample(
        ctx: Context,
        value: str = Field(default_factory=lambda current: "same"),
    ) -> str:
        calls.append(value)
        return value

    monkeypatch.setattr(
        "invoke_toolkit.tasks.cache.get_cache_directory", lambda: tmp_path
    )
    sample(Context())
    sample(Context())
    assert calls == ["same"]


def test_resolved_value_not_reference_is_used_for_cache_key(tmp_path, monkeypatch):
    resolved_values = iter(["first", "second"])
    body_calls: list[str] = []

    def resolver(ctx, requests):
        return {"secret": next(resolved_values)}

    entry_point = Mock()
    entry_point.name = "op"
    monkeypatch.setattr(
        "invoke_toolkit.field_resolvers._load_resolver",
        lambda scheme: (resolver, entry_point),
    )
    monkeypatch.setattr(
        "invoke_toolkit.tasks.cache.get_cache_directory", lambda: tmp_path
    )

    @task(cache=True)
    def sample(ctx: Context, secret: str = Field(default="op://same")) -> str:
        body_calls.append(secret)
        return secret

    sample(Context())
    sample(Context())
    assert body_calls == ["first", "second"]


def test_explicit_uri_value_bypasses_provider(monkeypatch):
    provider = Mock()
    monkeypatch.setattr(
        "invoke_toolkit.field_resolvers._load_resolver",
        lambda scheme: (provider, Mock(name="provider")),
    )
    received: list[str] = []

    @task
    def sample(ctx: Context, secret: str = Field(default="op://default")) -> None:
        received.append(secret)

    run_task(sample, "--secret", "op://explicit")
    assert received == ["op://explicit"]
    provider.assert_not_called()


def test_parameterized_pre_call_explicit_value_bypasses_factory():
    from invoke_toolkit import call

    factory = Mock(return_value="factory")
    received: list[str] = []

    @task
    def setup(ctx: Context, value: str = Field(default_factory=factory)) -> None:
        received.append(value)

    @task(pre=[call(setup, value="explicit")])  # type: ignore[arg-type]
    def build(ctx: Context) -> None: ...

    run_task(build)
    assert received == ["explicit"]
    factory.assert_not_called()


def test_parser_does_not_deepcopy_field_factory():
    class Factory:
        def __call__(self, ctx: Context) -> str:
            return "value"

        def __deepcopy__(self, memo):
            raise AssertionError("factory must not be copied by parser")

    received: list[str] = []

    @task
    def sample(ctx: Context, value: str = Field(default_factory=Factory())) -> None:
        received.append(value)

    run_task(sample)
    assert received == ["value"]

# Config Improvements

## Goal

Make the `Config` base class compatible with `attrs` to allow for more structured and less human-readable configuration files, especially for nested configurations.

## Findings

*   The current configuration class is `ToolkitConfig`, which inherits from `invoke.config.Config`.
*   The `ToolkitContext` class uses `ToolkitConfig` to manage configuration.
*   To add `attrs` compatibility, a new class `AttrsConfig` will be created.

## Plan

1.  **Create `AttrsConfig`:** This new class will inherit from `ToolkitConfig` and use the `attrs` library to define a structured configuration. It will override `__getattr__` to recursively convert nested dictionaries into `AttrsConfig` instances, enabling dot-notation access.
2.  **Integrate with `ToolkitContext`:** The `ToolkitContext` will be modified to use `AttrsConfig` instead of `ToolkitConfig`.
3.  **Dependencies:** `attrs` and `cattrs` have been added to `pyproject.toml` and installed.
4.  **Testing:** Add tests to verify the new `attrs`-based configuration works as expected.

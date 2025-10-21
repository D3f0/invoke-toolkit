from invoke_toolkit.config import ToolkitConfig


def test_class_attributes_overrides():
    class MyConfig(
        ToolkitConfig, prefix="custom", file_prefix="file_", env_prefix="ENV_"
    ):
        pass

    assert MyConfig.prefix == "custom"

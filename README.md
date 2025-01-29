# invoke-toolkit

A set of extended APIs for PyInvoke for composable scripts, plugins and richer output.

This extends the Collection from Invoke so it can create automatically collections.

[![PyPI - Version](https://img.shields.io/pypi/v/invoke-toolkit.svg)](https://pypi.org/project/invoke-toolkit)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/invoke-toolkit.svg)](https://pypi.org/project/invoke-toolkit)

-----

## Table of Contents

- [invoke-toolkit](#invoke-toolkit)
  - [Table of Contents](#table-of-contents)
  - [Features](#features)
  - [Do I need this package?](#do-i-need-this-package)
  - [Installation](#installation)
    - [Installation with `uv`](#installation-with-uv)
    - [One time execution with `uvx`](#one-time-execution-with-uvx)
    - [Into exiting pipx project](#into-exiting-pipx-project)
    - [Using shellscript](#using-shellscript)
    - [Bootstrapping a new CLI](#bootstrapping-a-new-cli)
  - [Development](#development)
  - [License](#license)

## Features

- Make single file invoke executables with [`uv` as your shebang](https://akrabat.com/using-uv-as-your-shebang-line/)

  ```python
  #!/usr/bin/env -S uv run --script
  # /// script
  # dependencies = [
  #   "invoke_toolkit",
  # ]
  # ///

  from invoke_toolkit.program import script
  from invoke import task, Context


  @task()
  def hello(ctx: Context):
      print("hello")


  script()
  ```

  And running it as:

  ```bash
  chmod +x script.py
  ./script.py hello
  ```

- Use of `rich` for pretty printing to `stderr` by default.
  Print beautiful messages using a pre-configured rich console object.

  ```python
  from invoke_toolkit import console
  from invoke import task, Context

  @task()

  ```


- Define a default configuration in each of your task files.

  ```python
  # my_scripts.py
  from invoke import task, Context

  # Configuration to pre-load in ctx.config.[SCRIPT_NAME].[*]
  # Can be overridden by environment variables or config file
  config = {
    "tag": "2024.12.1"
  }

  @task()
  def docker(ctx: Context, tag: str = ""):
    # You can override this with INVOKE_MY_SCRIPT_TAG=123
    tag = ctx.config.my_script.tag or tag
    ...
  ```

- Rich logging and bundled hunter for easier debugging.
- Create your own tasks as Python modules with automatic configuration discovery.
  You can host them in PyPI or a repo.
- Almost untouched original invoke's `tasks.py` and `tasks/` discovery.

## Do I need this package?

If you have...

- Used `invoke` for a while and...
  - Have a large `tasks.py` that needs to be modularized
  - Have a lot of copy/pasted code in multiple `tasks.py` across multiple repos.
  - Have exceeded the approach of a repository cloned as `~/tasks/` with more .py files that you want to manage.
- Or you want to combine various tasks defined in multiple directories
- ~~You want to create a zipped (shiv) redistribute script for container environments
  like Kubernetes based CI environments with only requiring the Python interpreter.~~
  - `uv tool`/`uvx` is a more flexible approach for distribution, since it can also
    download Python executables for your platform.

## Installation

<!-- > [!WARNING]
> Avoid installing `invoke` from `apt`/`yum, it this is the case we
> recommend to uninstall it and use `pipx` or **`uv`** instead. -->

### Installation with `uv`

`uv tool install https://github.com/D3f0/invoke-toolkit/`

The binary `invtk` should be available.

### One time execution with `uvx`

`uvx invtk`

### Into exiting pipx project

```console
pipx install https://github.com/D3f0/invoke-toolkit/
```

### Using shellscript

> Note: This has been tested in OSX and Debian only

```shell
git clone https://github.com/D3f0/invoke-toolkit
cd invoke-toolkit
sh ./install.sh
```

### Bootstrapping a new CLI

TBD...

## Development

This project utilizes the `pre-commit` framework, make sure you run:

`pre-commit install`

## License

`invoke-toolkit` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.

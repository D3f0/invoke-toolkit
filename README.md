# invoke-toolkit

A set of extensions for rich output, more options in collection/config discovery through `entry-points`.

This extends the Collection from Invoke so it can create automatically collections.

[![PyPI - Version](https://img.shields.io/pypi/v/invoke-toolkit.svg)](https://pypi.org/project/invoke-toolkit)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/invoke-toolkit.svg)](https://pypi.org/project/invoke-toolkit)

-----

## Table of Contents

- [invoke-toolkit](#invoke-toolkit)
  - [Table of Contents](#table-of-contents)
  - [Features](#features)
  - [Do I need this package](#do-i-need-this-package)
  - [Installation](#installation)
  - [Development](#development)
  - [License](#license)

## Features

- Task discovery by namespace for extendable/composable CLIs
- Discovery to *plain old* tasks.py (or any other name)
- Integration with stand alone binaries for specific tasks
- **Future** Download binaries

## Do I need this package

If you have...

- Used `invoke` for a while and...
- Have a large `tasks.py` that needs to be modularized
- Have a lot of copy/pasted code in multiple `tasks.py` across multiple repos.
- Have exceeded the approach of a repository cloned as `~/tasks/` with more .py files that you want to manage.
- Or you want to combine various tasks defined in multiple directories
- You want to create a zipped (shiv) redistribute script for container environments
  like Kubernetes based CI environments with only requiring the Python interpreter.

## Installation

```console
pip install invoke-toolkit
```

## Development

This project utilizes the `pre-commit` framework, make sure you run:

`pre-commit install`

With `uvx`:

`uvx --with pre-commit-uv pre-commit install`

## License

`invoke-toolkit` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.

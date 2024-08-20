import os
from pathlib import Path
from typing import Union


def is_directory_writable(a_directory: Union[str, Path]) -> bool:
    """Evaluate if a directory can be written to

    Parameters
    ----------
    a_directory : Union[str, Path]
        The directory to check for write access

    Returns
    -------
    bool
        True if the directory is writable, False otherwise
    """
    return os.access(a_directory, os.W_OK) and Path(a_directory).is_dir()

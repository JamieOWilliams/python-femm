import os
from pathlib import Path


def get_path(file_path, file_name):
    return os.path.join(Path(os.path.abspath(file_path)).parent, file_name)


def get_paths(file_path, paths):
    return {key: get_path(file_path, path) for key, path in paths.items()}

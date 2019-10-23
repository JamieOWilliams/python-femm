import sys

from python_femm import run_command, get_paths

paths = get_paths(__file__, {
    'settings': 'settings.py',
    'model': 'model.py',
    'scenes': 'scenes.py',
})

if __name__ == '__main__':
    run_command(sys.argv, paths=paths)

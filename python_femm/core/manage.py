import importlib.util
import os
import shutil
import sys
from pathlib import Path

from .run import hot_reload_pre, run_pre, run_solve, run_post
from .scenes import SceneRunner


def execute_from_command_line():
    run_command(sys.argv)


def run_command(argv, paths=None):
    if len(argv) == 1:
        raise ValueError('Must provide a command name.')
    command_name = argv[1]
    if command_name == 'new':
        # Copy over the contents of the template
        # directory to a new directory and give it
        # the name of the provided project name.
        project_name = argv[2]
        try:
            os.mkdir(project_name)
        except FileExistsError:
            print(f'Attempted to create project but there is already a directory with the name {project_name}.')
        template_dirname = os.path.join(Path(os.path.dirname(__file__)).parent, 'template')
        file_names = os.listdir(template_dirname)
        for file_name in file_names:
            shutil.copy(os.path.join(template_dirname, file_name), os.path.join(os.getcwd(), project_name))
    else:
        # Import the settings, model and scenes modules.
        settings_spec = importlib.util.spec_from_file_location('settings', paths['settings'])
        settings = importlib.util.module_from_spec(settings_spec)
        settings_spec.loader.exec_module(settings)

        model_spec = importlib.util.spec_from_file_location('model', paths['model'])
        model = importlib.util.module_from_spec(model_spec)
        model_spec.loader.exec_module(model)

        scenes_spec = importlib.util.spec_from_file_location('scenes', paths['scenes'])
        scenes = importlib.util.module_from_spec(scenes_spec)
        scenes_spec.loader.exec_module(scenes)

        # Get the model class from the model module.
        model_class = getattr(model, settings.MODEL_NAME)

        if command_name == 'dev':
            hot_reload_pre(model_module=model, model_name=settings.MODEL_NAME, root_dir=settings.ROOT_DIR)
        elif command_name == 'pre':
            run_pre(model_class, hold=True)
        elif command_name == 'solve':
            pre_runner, _ = run_pre(model_class)
            run_solve(pre_runner, hold=True)
        elif command_name == 'post':
            pre_runner, _ = run_pre(model_class)
            pre_runner = run_solve(pre_runner)
            run_post(pre_runner, hold=True)
        elif command_name == 'scene':
            if len(argv) == 2:
                raise ValueError('You must provide a scene name. For example ``python manage.py scene MyScene``.')
            scene_name = argv[2]
            try:
                scene_class = getattr(__import__(getattr(scenes, scene_name).__module__), scene_name)
                # scene_class = getattr(scenes, scene_name)
            except KeyError:
                raise ValueError(f'No scene matching the name {scene_name}.')
            SceneRunner().start(scene_class())

        else:
            raise ValueError('No matching command.')

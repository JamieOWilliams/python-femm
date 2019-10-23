import importlib
import os
import pywintypes
import sys
import time

def _hold(stop_message):
    try:
        while True:
            pass
    except KeyboardInterrupt:
        pass
    finally:
        print(stop_message)


def run_pre(model_class, hold=False):
    print('Running preprocessor...')
    runner = model_class()
    runner.start()
    runner.pre()
    if hold:
        _hold('Preprocessor stopped.')
    else:
        return runner, model_class


def hot_reload_pre(model_module=None, model_name=None, root_dir=None):
    sys.modules['model'] = model_module
    path = os.path.join(root_dir, 'model.py')
    most_recent_change = os.path.getmtime(path)
    most_recent_runner, model_class = run_pre(vars(model_module).get(model_name))
    try:
        print('Hot reloading started...')
        while True:
            time.sleep(0.5)
            if os.path.getmtime(path) > most_recent_change:
                print('Change detected. Reloading...')
                # Reload the module to pick up the new code.
                importlib.reload(model_module)
                # Update the most recent change time to now.
                most_recent_change = os.path.getmtime(path)

                # Create a new test instance but pass through the old session.
                most_recent_test = vars(model_module).get(model_name)(session=most_recent_runner.session)
                # Close the old document.
                most_recent_test.close()
                # Rebuild the document with the new code.
                try:
                    most_recent_test.pre()
                except pywintypes.com_error as e:
                    print('There was an error with your latest change:', e)
    except KeyboardInterrupt:
        pass
    finally:
        print('Hot reloading stopped.')


def run_solve(pre_runner, hold=False):
    print('Running solver...')
    pre_runner.solve()
    if hold:
        _hold('Solver view closed.')
    else:
        return pre_runner


def run_post(pre_runner, hold=False):
    print('Running postprocessor...')
    pre_runner.post()
    if hold:
        _hold('Postprocessor stopped.')

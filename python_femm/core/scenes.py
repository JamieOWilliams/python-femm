import multiprocessing as mp
import time
import _winapi

import numpy as np

TWO_DIMENSIONAL_MODE = '2d'
THREE_DIMENSIONAL_MODE = '3d'


class SceneRunner:

    def start(self, scene_class):
        mode = scene_class.mode.lower()
        iterations = scene_class.iterations
        instance_count = iterations if mode == TWO_DIMENSIONAL_MODE else iterations ** 2

        print(f'Running scene with {instance_count} instances, on {mp.cpu_count()} processes...')
        mp.set_executable(_winapi.GetModuleFileName(0))
        start_time = time.perf_counter()
        results = []
        with mp.Pool(mp.cpu_count()) as pool:
            if mode == TWO_DIMENSIONAL_MODE:
                results = [pool.starmap(scene_class.run, [(x_iteration, 0) for x_iteration in range(iterations)]), []]
            elif mode == THREE_DIMENSIONAL_MODE:
                for x_iteration in range(iterations):
                    results.append(pool.starmap(scene_class.run,
                                                [(x_iteration, y_iteration) for y_iteration in range(iterations)]))
            else:
                raise ValueError('Mode must be either 2D or 3D.')
        end_time = time.perf_counter()
        print(f'Finished in {np.round(end_time - start_time)} seconds.')
        self.end(scene_class, results)

    def end(self, scene_class, results):
        print(f'Displaying results...')
        scene_class.display_results(results)


class Scene:
    model = None
    iterations = None
    mode = None

    def vary(self, start, end, value):
        increment = (end - start) / self.iterations
        return start + (value * increment)

    def run(self, x_value, y_value):
        self.model.start()
        self.model.pre(x_value=x_value, y_value=y_value)
        self.model.solve()
        return self.model.post()

    def get_axis(self, start, end):
        return np.linspace(start, end, self.iterations)

    def display_results(self, results):
        raise NotImplementedError('You need to implement this method.')

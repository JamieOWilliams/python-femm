from .wrapper import FEMMSession


class Model:

    def __init__(self, session=None):
        self.session = session

    def start(self):
        self.session = FEMMSession()

    def pre(self):
        raise NotImplementedError('You need to implement this method.')

    def solve(self):
        raise NotImplementedError('You need to implement this method.')

    def post(self):
        raise NotImplementedError('You need to implement this method.')

    def close(self):
        self.session.pre.close()

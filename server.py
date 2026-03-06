from openreward.environments import Server
from env import SudokuEnvironment

if __name__ == "__main__":
    server = Server([SudokuEnvironment])
    server.run()

import os
import sys

from .main import Main

if __name__ == "__main__":
    if len(sys.argv) > 1:
        parameter = sys.argv[1]
    else:
        parameter = os.getcwd()
    print(f"Starting with parameter '{parameter}'")
    main = Main(parameter)

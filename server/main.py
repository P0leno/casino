import sys
import os
print("DEBUG MAIN: CWD =", os.getcwd())
print("DEBUG MAIN: sys.path =", sys.path)
try:
    import app
    print("DEBUG MAIN: app file =", app.__file__)
except ImportError as e:
    print("DEBUG MAIN: Failed to import app:", e)

from app.run import run_server

if __name__ == "__main__":
    run_server()

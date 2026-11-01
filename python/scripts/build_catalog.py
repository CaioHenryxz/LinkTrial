"""Kept for backward compatibility: the catalog is now built by the CRUD sync job (scripts/sync.py)."""
import pathlib
import runpy
import sys

if __name__ == "__main__":
    sys.argv = ["sync.py"]
    runpy.run_path(str(pathlib.Path(__file__).with_name("sync.py")), run_name="__main__")

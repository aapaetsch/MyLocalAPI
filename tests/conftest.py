import sys
import pathlib

# Ensure project root is on sys.path so tests import the application's
# top-level modules (e.g. `settings`, `utils`, `audio_control`).
root = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))

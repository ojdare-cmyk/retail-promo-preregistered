"""Loads config.yaml so every script reads the same settings."""
from pathlib import Path
import yaml

# The project folder (one level up from src/)
ROOT = Path(__file__).resolve().parent.parent


def load_config():
    with open(ROOT / "config.yaml") as f:
        return yaml.safe_load(f)


def path(relative):
    """Turn a path from the config into a full path inside the project."""
    return ROOT / relative

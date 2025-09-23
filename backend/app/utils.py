from pathlib import Path
from typing import Type, TypeVar, Tuple
import yaml
from pydantic import ValidationError

T = TypeVar("T")

CONFIG_DIR = Path(__file__).resolve().parent.parent / "configs"

def load_yaml_raw(rel_path: str) -> Tuple[dict, Path]:
    path = CONFIG_DIR / rel_path
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data, path


def load_and_validate(rel_path: str, model: Type[T]) -> T:
    data, path = load_yaml_raw(rel_path)
    try:
        return model.model_validate(data)  # Pydantic v2 method
    except ValidationError as e:
        # Add file path context so errors are easy to read
        raise ValueError(f"Invalid config in {path}:\n{e}") from e
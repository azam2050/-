from pathlib import Path

import yaml

DEFAULT_RULES = Path(__file__).resolve().parent.parent / "config" / "factory_rules.yaml"


def load_rules(path=None):
    with open(path or DEFAULT_RULES, encoding="utf-8") as f:
        return yaml.safe_load(f)

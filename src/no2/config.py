from pathlib import Path
import yaml

ROOT= Path(__file__).resolve().parents[2] #project root finder . [2] --> three directories up

def load_config() -> dict:
    with open(ROOT / "config" / "project.yaml" ) as f:
        return yaml.safe_load(f)

CFG= load_config()

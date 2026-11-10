"""Domain configuration loader. Everything domain-specific lives in domains/<name>.yaml."""
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[2]
DOMAINS_DIR = ROOT / "domains"
DATA = ROOT / "data"


def load_domain(name: str) -> dict:
    path = DOMAINS_DIR / f"{name}.yaml"
    if not path.exists():
        raise SystemExit(f"No domain config at {path}. Available: {[p.stem for p in DOMAINS_DIR.glob('*.yaml')]}")
    cfg = yaml.safe_load(path.read_text())
    cfg["theme_ids"] = [t["id"] for t in cfg["themes"]]
    cfg["feature_ids"] = [f["id"] for f in cfg.get("features", [])]
    return cfg


def paths(domain: str) -> dict:
    return {
        "raw": DATA / "raw" / f"{domain}_pool.parquet",
        "sample": DATA / "processed" / f"{domain}_reviews.parquet",
        "label_sample": DATA / "processed" / f"{domain}_label_sample.csv",
        "labels": ROOT / "labels" / f"{domain}_labels.csv",
        "preds": DATA / "processed" / f"{domain}_predictions.parquet",
        "export": ROOT / "web" / "public" / "data",
    }

import yaml
from pathlib import Path

def load_btag_wps(tagger: str = "deepJet"):
    wp_dir = Path.cwd() / "analysis" / "working_points"
    btag_wp_file = wp_dir / "btag.yaml"
    with open(btag_wp_file, "r") as f:
        btag_wps = yaml.safe_load(f)
    return btag_wps[tagger]
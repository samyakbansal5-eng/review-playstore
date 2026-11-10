"""CLI entry point:  python run.py <command> --domain upi"""
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def main():
    ap = argparse.ArgumentParser(description="App Voice-of-Customer engine")
    ap.add_argument("command", choices=["scrape", "label-sample", "label", "classify", "evaluate", "analyze"])
    ap.add_argument("--domain", default="upi")
    ap.add_argument("--limit", type=int, default=None, help="classify only N reviews (testing)")
    ap.add_argument("--port", type=int, default=8765)
    a = ap.parse_args()
    from voc import scrape
    if a.command == "scrape":
        scrape.run(a.domain)
    elif a.command == "label-sample":
        from voc import labeling; labeling.make_sample(a.domain)
    elif a.command == "label":
        from voc import labeling; labeling.serve(a.domain, a.port)
    elif a.command == "classify":
        from voc import classify; classify.run(a.domain, a.limit)
    elif a.command == "evaluate":
        from voc import evaluate; evaluate.run(a.domain)
    elif a.command == "analyze":
        from voc import analyze; analyze.run(a.domain)


if __name__ == "__main__":
    main()

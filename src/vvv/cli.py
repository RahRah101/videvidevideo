import argparse
from pathlib import Path

def main() -> int:
    p = argparse.ArgumentParser(prog="vvv")
    p.add_argument("script", type=Path, nargs="?")
    p.add_argument("--version", action="store_true")
    args = p.parse_args()
    if args.version:
        print("vvv 0.0.1")
        return 0
    print(f"would process: {args.script}")
    return 0

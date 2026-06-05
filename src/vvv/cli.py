import argparse
from pathlib import Path
import vvv.plugins

def main() -> int:
    p = argparse.ArgumentParser(prog="vvv")
    p.add_argument("script", type=Path, nargs="?")
    p.add_argument("--version", action="store_true")
    p.add_argument("--list-producers", action="store_true")
    args = p.parse_args()
    if args.version:
        print("vvv 0.0.1")
        return 0 
    if args.list_producers:
        from vvv.registry import PRODUCERS
        for node_type, producer_cls in PRODUCERS.items():
            print(f"  {node_type.__name__:20s} -> {producer_cls.__name__}")
        return 0
    print(f"would process: {args.script}")
    return 0

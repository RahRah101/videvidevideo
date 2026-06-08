import argparse
import re
import sys
from pathlib import Path

import yaml

import vvv.plugins
from vvv.util import text


def main() -> int:
    p = argparse.ArgumentParser(prog="vvv")
    p.add_argument("script", type=Path, nargs="?")
    p.add_argument("--version", action="store_true")
    p.add_argument("--list-producers", action="store_true")
    p.add_argument("--work-dir", type=Path, default=Path("build"))
    p.add_argument("--output", type=Path, default=None,
                   help="output .kdenlive path (default: build/<slug>.kdenlive)")
    args = p.parse_args()

    if args.version:
        print("vvv 0.0.1")
        return 0

    if args.list_producers:
        from vvv.registry import PRODUCERS
        for node_type, producer_cls in PRODUCERS.items():
            print(f"  {node_type.__name__:20s} -> {producer_cls.__name__}")
        return 0

    if args.script is None:
        p.error("script path required")

    return _run(args.script, args.work_dir, args.output)


def _run(script_path: Path, work_dir: Path, output: Path | None) -> int:
    from vvv.phases.parse import parse
    from vvv.phases.resolve import resolve
    from vvv.context import Context
    from vvv.composition import build_producers, build_sync, build_assembler

    with open(script_path) as f:
        raw = yaml.safe_load(f)

    parsed = parse(raw)
    print(f"[parse] {len(parsed.nodes)} nodes from {script_path}")

    work_dir.mkdir(parents=True, exist_ok=True)
    ctx = Context(meta=parsed.meta, work_dir=work_dir)

    producers = build_producers()
    sync = build_sync()
    assembler = build_assembler()

    print(f"[resolve] producing media for {len(parsed.nodes)} nodes...")
    resolved = resolve(parsed.nodes, producers, ctx)

    print(f"[sync] timing {len(resolved)} entries...")
    timed = sync.time(resolved, ctx)

    if output is None:
        slug = text.slugify(parsed.meta.title)
        output = work_dir / f"{slug}.kdenlive"

    print(f"[assemble] writing {output}...")
    final = assembler.assemble(timed, ctx, output)

    print(f"\nWe done! Path: {final}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
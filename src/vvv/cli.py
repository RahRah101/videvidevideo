import argparse
import re
import sys
from pathlib import Path

import yaml

from vvv.plugin_loader import load_plugins
from vvv.util import text


def main() -> int:
    p = argparse.ArgumentParser(prog="vvv")
    p.add_argument("script", type=Path, nargs="?")
    p.add_argument("--version", action="store_true")
    p.add_argument("--list-producers", action="store_true")
    p.add_argument("--work-dir", type=Path, default=Path("build"))
    p.add_argument("--output", type=Path, default=None,
                   help="output path (default: <work-dir>/<slug><assembler's suffix>, e.g. .kdenlive)")
    p.add_argument("--target", default=None,
                   help="assembler to use (overrides `config: assemble: target:`; default kdencli)")
    args = p.parse_args()

    if args.version:
        print("vvv 0.0.1")
        return 0

    load_plugins()

    if args.list_producers:
        from vvv.registry import PRODUCERS
        for node_type, producer_cls in PRODUCERS.items():
            print(f"  {node_type.__name__:20s} -> {producer_cls.__name__}")
        return 0

    if args.script is None:
        p.error("script path required")

    return _run(args.script, args.work_dir, args.output, args.target)


def _run(script_path: Path, work_dir: Path, output: Path | None, target: str | None = None) -> int:
    from vvv.phases.parse import parse, DSLError
    from vvv.phases.resolve import resolve
    from vvv.context import Context
    from vvv.composition import (build_producers, build_sync, build_assembler,
                                 assembler_target, known_config_sections)

    with open(script_path) as f:
        raw = yaml.safe_load(f)

    try:
        parsed = parse(raw)
    except DSLError as e:
        print(f"[parse] errors in {script_path}:\n{e}", file=sys.stderr)
        return 1
    for w in parsed.warnings:
        print(f"[parse] warning: {w}", file=sys.stderr)
    print(f"[parse] {len(parsed.nodes)} nodes from {script_path}")

    work_dir.mkdir(parents=True, exist_ok=True)
    ctx = Context(meta=parsed.meta, work_dir=work_dir)

    config = parsed.config
    try:
        # only what this script uses gets built (no narration -> no ElevenLabs key needed)
        producers = build_producers(config, {type(n) for n in parsed.nodes})
        assembler = build_assembler(config, assembler_target(config, target))
        sync = build_sync(config)
    except ValueError as e:
        print(f"[config] error: {e}", file=sys.stderr)
        return 1
    for w in config.warnings + config.unknown_sections(known_config_sections()):
        print(f"[config] warning: {w}", file=sys.stderr)

    print(f"[resolve] producing media for {len(parsed.nodes)} nodes...")
    resolved = resolve(parsed.nodes, producers, ctx)

    print(f"[sync] timing {len(resolved)} entries...")
    timed = sync.time(resolved, ctx)

    if output is None:
        slug = text.slugify(parsed.meta.title)
        output = work_dir / f"{slug}{assembler.output_suffix}"

    print(f"[assemble] writing {output}...")
    final = assembler.assemble(timed, ctx, output)

    print(f"\nWe done! Path: {final}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

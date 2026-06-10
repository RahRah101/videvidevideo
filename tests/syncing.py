if __name__ == "__main__":
    from pathlib import Path
    from vvv.ir.nodes import PauseNode
    from vvv.ir.resolved import ResolvedEntry
    from vvv.context import Context, Meta
    from vvv.phases.sync import SequentialSync

    fake = [
        ResolvedEntry(PauseNode(2.0), None, "marker", 2.0),
        ResolvedEntry(PauseNode(3.5), None, "marker", 3.5),
        ResolvedEntry(PauseNode(1.0), None, "marker", 1.0),
    ]
    ctx = Context(
        meta=Meta("t", "", 30, (1920,1080), Path("assets"), 5000),
        work_dir=Path("build"),
    )
    print(SequentialSync().time(fake, ctx))
    # Should print 3 TimedEntries with start_s = 0.0, 2.0, 5.5

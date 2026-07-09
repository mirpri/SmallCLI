"""Stage 1b: distill the Planner LoRA dataset.

For each seed task, the teacher decomposes it into a prefixed step list using
the SAME template the student will use at inference. We keep only outputs that
parse into a valid list of correctly-prefixed steps.

Side effect: extracts "执行命令:" and "文件编辑:" sub-steps into pools reused by
the Executor / File-edit distillers (self-consistent pipeline).
"""
import argparse
import ast

from client import alpaca, chat, parallel_map, read_jsonl, write_jsonl
from templates import PLANNER_SYSTEM, planner_input
from util_local import strip_codeblock

VALID_PREFIXES = ("综合推理:", "执行命令:", "文件编辑:")


def _parse_steps(raw: str):
    """Return list[str] of valid steps, or None if the output is malformed."""
    s = strip_codeblock(raw)
    try:
        steps = ast.literal_eval(s)
    except Exception:
        return None
    if not isinstance(steps, list) or not steps:
        return None
    for step in steps:
        if not isinstance(step, str):
            return None
        if not step.strip().startswith(VALID_PREFIXES):
            return None
    return steps


def _distill(seed: dict) -> dict:
    task = seed["task"]
    raw = chat(PLANNER_SYSTEM, planner_input(task), temperature=0.3)
    if not raw:
        return None
    steps = _parse_steps(raw)
    if steps is None:
        return None
    return {
        "record": alpaca(PLANNER_SYSTEM, planner_input(task), str(steps)),
        "steps": steps,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default="../data/seed_tasks.jsonl")
    ap.add_argument("--out", default="../data/planner.jsonl")
    ap.add_argument("--cmd-pool", default="../data/_pool_commands.jsonl")
    ap.add_argument("--edit-pool", default="../data/_pool_edits.jsonl")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    seeds = read_jsonl(args.seeds)
    if not seeds:
        raise SystemExit(f"No seeds found at {args.seeds}; run gen_seed_tasks.py first.")

    results = parallel_map(_distill, seeds, workers=args.workers, desc="planner")

    records = [r["record"] for r in results]
    cmd_pool, edit_pool = [], []
    for r in results:
        for step in r["steps"]:
            s = step.strip()
            if s.startswith("执行命令:"):
                cmd_pool.append({"description": s[len("执行命令:"):].strip()})
            elif s.startswith("文件编辑:"):
                edit_pool.append({"description": s[len("文件编辑:"):].strip()})

    write_jsonl(args.out, records)
    write_jsonl(args.cmd_pool, cmd_pool)
    write_jsonl(args.edit_pool, edit_pool)


if __name__ == "__main__":
    main()

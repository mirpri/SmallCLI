"""Stage 1c: distill the Executor LoRA dataset (description -> shell command list).

Consumes the command-description pool produced by the Planner stage. Keeps only
outputs that parse into a non-empty Python list of strings.
"""
import argparse
import ast

from client import alpaca, chat, parallel_map, read_jsonl, write_jsonl
from templates import EXECUTOR_SYSTEM, executor_input
from util_local import strip_codeblock


def _parse_cmds(raw: str):
    s = strip_codeblock(raw)
    try:
        cmds = ast.literal_eval(s)
    except Exception:
        return None
    if not isinstance(cmds, list) or not cmds:
        return None
    if not all(isinstance(c, str) and c.strip() for c in cmds):
        return None
    return cmds


def _distill(item: dict) -> dict:
    desc = item["description"]
    raw = chat(EXECUTOR_SYSTEM, executor_input(desc), temperature=0.2)
    if not raw:
        return None
    cmds = _parse_cmds(raw)
    if cmds is None:
        return None
    return alpaca(EXECUTOR_SYSTEM, executor_input(desc), str(cmds))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pool", default="../data/_pool_commands.jsonl")
    ap.add_argument("--out", default="../data/executor.jsonl")
    ap.add_argument("--limit", type=int, default=0, help="0 = use all")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    pool = read_jsonl(args.pool)
    if not pool:
        raise SystemExit(f"No command pool at {args.pool}; run gen_planner.py first.")

    # Dedup descriptions
    seen, items = set(), []
    for it in pool:
        d = it["description"]
        if d not in seen:
            seen.add(d)
            items.append(it)
    if args.limit:
        items = items[: args.limit]

    records = parallel_map(_distill, items, workers=args.workers, desc="executor")
    write_jsonl(args.out, records)


if __name__ == "__main__":
    main()

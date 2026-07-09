"""Run the full Stage-1 distillation pipeline end to end.

    python run_all.py --per-category 40 --workers 8

Stages (each is also runnable standalone):
    1. gen_seed_tasks   -> data/seed_tasks.jsonl
    2. gen_planner      -> data/planner.jsonl   (+ command/edit pools)
    3. gen_executor     -> data/executor.jsonl
    4. gen_debugger     -> data/debugger.jsonl
"""
import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def run(script: str, extra: list):
    cmd = [sys.executable, os.path.join(HERE, script)] + extra
    print(f"\n{'=' * 60}\n>>> {' '.join(cmd)}\n{'=' * 60}")
    # cwd=HERE so sub-scripts' sibling imports and ../data output paths resolve
    subprocess.run(cmd, check=True, cwd=HERE)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-category", type=int, default=40)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--skip-seeds", action="store_true",
                    help="reuse existing data/seed_tasks.jsonl")
    args = ap.parse_args()

    w = ["--workers", str(args.workers)]

    if not args.skip_seeds:
        run("gen_seed_tasks.py", ["--per-category", str(args.per_category)] + w)
    run("gen_planner.py", w)
    run("gen_executor.py", w)
    run("gen_debugger.py", w)

    print("\nAll stages complete. Datasets in ../data/. "
          "Register them via data/dataset_info.json for LLaMA-Factory.")


if __name__ == "__main__":
    main()

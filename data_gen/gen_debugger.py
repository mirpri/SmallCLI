"""Stage 1d: distill the Debugger LoRA dataset (command + error -> fixed command).

Real failure logs are scarce, so we synthesize them: for each command the teacher
invents a realistic error scenario AND the corrected command, returned as JSON.
The training record is then framed with the SAME debugger template used at
inference (command + error -> fix), so the student sees the production input shape.
"""
import argparse
import ast
import json

from client import alpaca, chat, parallel_map, read_jsonl, write_jsonl
from templates import DEBUGGER_SYSTEM, debugger_input
from util_local import strip_codeblock

_SCENARIO_SYSTEM = (
    "你是一个 Linux 故障构造专家。给定一条命令，请构造一个真实、常见的执行失败场景。"
    "常见失败包括：路径不存在、缺少权限(需 sudo)、依赖/命令未安装、缺少参数、"
    "包管理器不匹配、文件已存在、语法错误等。"
    "请严格输出一个 JSON 对象，包含两个字段："
    '{"error": "真实的 stderr 报错文本", "fixed_command": "修正后可直接运行且无需交互的完整命令"}。'
    "只输出 JSON，不要任何解释或 Markdown。"
)


def _extract_first_command(cmd_record_output: str):
    """executor.jsonl output is a str(list); take the last (final) command as the
    one most likely to be run standalone. Fall back to the raw string."""
    try:
        cmds = ast.literal_eval(cmd_record_output)
        if isinstance(cmds, list) and cmds:
            return " && ".join(str(c) for c in cmds)
    except Exception:
        pass
    return cmd_record_output


def _parse_scenario(raw: str):
    s = strip_codeblock(raw)
    try:
        obj = json.loads(s)
    except Exception:
        try:
            obj = ast.literal_eval(s)
        except Exception:
            return None
    if not isinstance(obj, dict):
        return None
    err = str(obj.get("error", "")).strip()
    fix = str(obj.get("fixed_command", "")).strip()
    if not err or not fix:
        return None
    return err, fix


def _distill(command: str) -> dict:
    raw = chat(_SCENARIO_SYSTEM, f"命令：{command}", temperature=0.6)
    if not raw:
        return None
    parsed = _parse_scenario(raw)
    if parsed is None:
        return None
    error, fixed = parsed
    return alpaca(DEBUGGER_SYSTEM, debugger_input(command, error), fixed)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--executor", default="../data/executor.jsonl",
                    help="source of commands to break")
    ap.add_argument("--out", default="../data/debugger.jsonl")
    ap.add_argument("--limit", type=int, default=0, help="0 = use all")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    exec_records = read_jsonl(args.executor)
    if not exec_records:
        raise SystemExit(f"No executor data at {args.executor}; run gen_executor.py first.")

    seen, commands = set(), []
    for rec in exec_records:
        cmd = _extract_first_command(rec.get("output", ""))
        if cmd and cmd not in seen:
            seen.add(cmd)
            commands.append(cmd)
    if args.limit:
        commands = commands[: args.limit]

    records = parallel_map(_distill, commands, workers=args.workers, desc="debugger")
    write_jsonl(args.out, records)


if __name__ == "__main__":
    main()

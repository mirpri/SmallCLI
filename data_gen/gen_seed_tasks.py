"""Stage 1a: generate a diverse pool of user task descriptions (self-instruct).

These seed tasks feed the Planner distillation, and their decomposed sub-steps
feed the Executor / Debugger distillation. Categories mirror the scenarios in
docs/应用场景及定位分析.md so the dataset matches the product's target domain.
"""
import argparse
import re

from client import chat, parallel_map, write_jsonl

# Target domains taken from the project's scenario analysis.
CATEGORIES = [
    "Git 冲突处理与仓库管理（分支、合并、log、reset、stash 等）",
    "一键开发环境配置（读取 requirements.txt/package.json/CMakeLists、装依赖、编译）",
    "智能文件整理（批量重命名、按类型/日期分类归档、移动、查找）",
    "磁盘清理（查找大文件、重复文件、清缓存、删无用安装包）",
    "文档排版与格式转换（markdown/latex、pandoc 转 pdf/docx）",
    "编程小任务（用某语言写脚本/程序、编译、运行、测试）",
    "系统信息与进程管理（查看系统信息、端口、进程、资源占用、杀进程）",
    "网络与下载（curl/wget 下载、解压、校验、简单网页抓取）",
    "文本处理（grep/sed/awk 统计、过滤、替换、排序、去重）",
    "定时与自动化（cron、简单 shell 脚本、权限设置）",
]

_GEN_SYSTEM = (
    "你是一个数据集构造助手。请针对给定的场景类别，生成多样化、真实、口语化的中文用户指令，"
    "这些指令是普通用户对一个命令行 AI Agent 提出的任务。"
    "要求：难度覆盖简单到中等；有的单步、有的多步；涉及具体文件名/目录/参数时要具体；"
    "不要编号、不要解释，每行一条指令。"
)


def _gen_for_category(cat_n: tuple) -> dict:
    category, n = cat_n
    user = f"场景类别：{category}\n请生成 {n} 条该类别下的用户指令，每行一条，仅输出指令本身。"
    text = chat(_GEN_SYSTEM, user, temperature=1.0)
    if not text:
        return None
    tasks = []
    for line in text.splitlines():
        line = line.strip()
        line = re.sub(r"^[\-\*\d\.\)、,，\s]+", "", line)  # strip bullets/numbering
        if 4 <= len(line) <= 200:
            tasks.append(line)
    return {"category": category, "tasks": tasks}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-category", type=int, default=40, help="tasks per category")
    ap.add_argument("--out", default="../data/seed_tasks.jsonl")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    results = parallel_map(
        _gen_for_category,
        [(c, args.per_category) for c in CATEGORIES],
        workers=args.workers,
        desc="seed",
    )

    # Flatten + dedup
    seen = set()
    records = []
    for r in results:
        for t in r["tasks"]:
            if t not in seen:
                seen.add(t)
                records.append({"task": t, "category": r["category"]})

    write_jsonl(args.out, records)


if __name__ == "__main__":
    main()

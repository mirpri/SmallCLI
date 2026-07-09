#!/usr/bin/env bash
# ============================================================================
# 本地环境搭建（uv 工程 · 首次初始化）
#   之后日常只需在仓库根目录跑：  uv sync
#   本脚本 = uv sync + .env 检查，方便第一次一步到位。
#   用法：bash scripts/setup_local.sh
# ============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "${ROOT}"

echo "==> [1/2] uv sync（按 pyproject.toml 创建 .venv 并安装依赖，生成/更新 uv.lock）"
if ! command -v uv >/dev/null 2>&1; then
  echo "未找到 uv，请先安装：" >&2
  echo "  curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
  exit 1
fi
uv sync
# 需要旧 ollama 后端(Baseline A)时：uv sync --extra ollama

echo "==> [2/2] 检查 .env"
if [ ! -f "${ROOT}/.env" ]; then
  echo "    未发现 .env，请复制模板并填 API_KEY："
  echo "      cp '${ROOT}/.env copy' '${ROOT}/.env'   然后编辑 BASE_URL / API_KEY"
else
  echo "    .env 已存在"
fi

cat <<EOF

✅ 本地工程就绪。以后换机器/更新依赖只需： uv sync

运行方式（uv run 自动用 .venv，无需手动 activate）：
   uv run python data_gen/run_all.py --per-category 5 --workers 8    # 小样验证
   uv run python data_gen/run_all.py --per-category 40 --workers 8   # 正式生成
   uv run uvicorn server:app --reload                                # 起后端

端侧 llama.cpp（最终产品推理引擎）需另行编译，见 docs/训练服务器操作手册.md 步骤4。
EOF

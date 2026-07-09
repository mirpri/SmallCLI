#!/usr/bin/env bash
# ============================================================================
# 训练服务器环境搭建（租用 3090 · QLoRA 训练 + GGUF 转换）
#   对应 docs/训练服务器操作手册.md 步骤 1 & 4
#   用法：bash scripts/setup_server.sh [env_name] [--with-llamacpp]
#         env_name          默认 leap
#         --with-llamacpp   顺带 clone+编译 llama.cpp(带 CUDA)，用于步骤4转 GGUF
# ============================================================================
set -euo pipefail

ENV_NAME="leap"
BUILD_LLAMACPP=0
for arg in "$@"; do
  case "$arg" in
    --with-llamacpp) BUILD_LLAMACPP=1 ;;
    *) ENV_NAME="$arg" ;;
  esac
done
PY_VER="3.10"   # LLaMA-Factory 在 3.10 最稳

echo "==> [1/6] 检查 GPU"
if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
else
  echo "⚠ 未检测到 nvidia-smi，确认这是 GPU 服务器且驱动正常。" >&2
fi

echo "==> [2/6] 准备 Python 环境: ${ENV_NAME} (python ${PY_VER})"
if command -v conda >/dev/null 2>&1; then
  source "$(conda info --base)/etc/profile.d/conda.sh"
  conda env list | grep -qE "^\s*${ENV_NAME}\s" || conda create -n "${ENV_NAME}" "python=${PY_VER}" -y
  conda activate "${ENV_NAME}"
else
  echo "    未找到 conda，改用 venv (~/${ENV_NAME})"
  python3 -m venv "$HOME/${ENV_NAME}"
  # shellcheck disable=SC1090
  source "$HOME/${ENV_NAME}/bin/activate"
fi

echo "==> [3/6] 配置 HuggingFace 国内镜像"
export HF_ENDPOINT="https://hf-mirror.com"
if ! grep -q "HF_ENDPOINT" "$HOME/.bashrc" 2>/dev/null; then
  echo 'export HF_ENDPOINT=https://hf-mirror.com' >> "$HOME/.bashrc"
fi

echo "==> [4/6] 安装 LLaMA-Factory + QLoRA 依赖"
python -m pip install --upgrade pip
pip install -U huggingface_hub
pip install "llamafactory[torch,metrics,bitsandbytes]"
# 数据也可在服务器上生成时需要：
pip install openai python-dotenv

echo "==> [5/6] 校验安装"
llamafactory-cli version || { echo "llamafactory 安装异常"; exit 1; }
python -c "import torch; print('torch', torch.__version__, 'cuda:', torch.cuda.is_available())"

echo "==> [6/6] llama.cpp（GGUF 转换）"
if [ "${BUILD_LLAMACPP}" -eq 1 ]; then
  if [ ! -d "$HOME/llama.cpp" ]; then
    git clone https://github.com/ggml-org/llama.cpp "$HOME/llama.cpp"
  fi
  cmake -S "$HOME/llama.cpp" -B "$HOME/llama.cpp/build" -DGGML_CUDA=ON
  cmake --build "$HOME/llama.cpp/build" -j
  pip install -r "$HOME/llama.cpp/requirements.txt"
  echo "    llama.cpp 就绪：$HOME/llama.cpp/build/bin/llama-server"
else
  echo "    跳过（加 --with-llamacpp 可在此编译）。转 GGUF 时再装亦可，见手册步骤4。"
fi

cat <<EOF

✅ 服务器环境就绪。下一步（仓库根目录）：
   cd ~/SmallCLI
   llamafactory-cli train train/planner.yaml
   llamafactory-cli train train/executor.yaml
   llamafactory-cli train train/debugger.yaml

完整流程见 docs/训练服务器操作手册.md
（建议先 tmux new -s train 再开训，防断线丢进度）
EOF

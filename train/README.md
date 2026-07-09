# Stage 2 · QLoRA 训练 + Stage 3 · llama.cpp LoRA 热切换

三个专家共享**同一个冻结 base**（端侧默认 `Qwen2.5-Coder-1.5B-Instruct`；高配可换 3B），各训一个 LoRA adapter。
**训练**在租用的 3090 上跑；**推理/热切换**改用 llama.cpp（GGUF），低并发端侧场景下
比 vLLM 轻得多，CPU / 笔记本即可跑，Demo 不再强依赖 GPU。

## 环境
```bash
# 训练（3090 服务器）
pip install llamafactory[torch,metrics]
# 或按 https://github.com/hiyouga/LLaMA-Factory 官方说明安装

# 推理（本地/端侧，无需 GPU）：编译 llama.cpp，得到 llama-server 与转换脚本
git clone https://github.com/ggml-org/llama.cpp && cd llama.cpp
cmake -B build && cmake --build build -j          # 需要 GPU 加速加 -DGGML_CUDA=ON
pip install -r requirements.txt                   # convert_lora_to_gguf.py 依赖
```
先把 `data/`（含 `dataset_info.json` 和三份 jsonl）传到服务器，与本仓库同结构。

## 训练三个专家
在仓库根目录执行（config 里 `dataset_dir: data` 是相对根目录）：
```bash
llamafactory-cli train train/planner.yaml
llamafactory-cli train train/executor.yaml
llamafactory-cli train train/debugger.yaml
```
产物：`adapters/planner`、`adapters/executor`、`adapters/debugger`。
单卡 3090、每份数百~上千条，单个 adapter 约 10~30 分钟。

显存吃紧就调：`per_device_train_batch_size: 1`、`cutoff_len: 1536`。

## Stage 3 · llama.cpp 一进程挂三 LoRA（热切换）

### 3.1 准备 GGUF 权重
Base 用现成的 GGUF 量化权重（HF 上有官方/社区版），adapter 从 HF 格式转 GGUF：
```bash
# base：下载量化好的 GGUF（Q4_K_M 精度/体积平衡，1.5B≈1GB；也可用 Q8_0）
huggingface-cli download Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF \
  qwen2.5-coder-1.5b-instruct-q4_k_m.gguf --local-dir models/gguf

# 三个 adapter：HF → GGUF（--base 指向训练用的 HF base 目录/名，读取 config 对齐张量）
for role in planner executor debugger; do
  python llama.cpp/convert_lora_to_gguf.py adapters/$role \
    --base Qwen/Qwen2.5-Coder-1.5B-Instruct \
    --outtype f16 --outfile adapters/$role-f16.gguf
done
```

### 3.2 启动 server，一次挂三个 adapter
adapter 按 `--lora` 顺序拿到 id `0/1/2`：
```bash
llama-server -m models/gguf/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf \
  --lora adapters/planner-f16.gguf \      # id 0
  --lora adapters/executor-f16.gguf \     # id 1
  --lora adapters/debugger-f16.gguf \     # id 2
  -c 4096 --port 8001
```

### 3.3 每请求切专家 = LEAP 「热切换」
llama.cpp 的 `model` 字段被忽略，切换靠请求体里的 **`lora` scale 数组**：目标专家设 `1.0`、
其余设 `0.0`。base 只加载一份，切换零成本（不重载权重）：
```python
client = openai.OpenAI(base_url="http://<host>:8001/v1", api_key="EMPTY")

# id 顺序对应 planner=0 / executor=1 / debugger=2
def experts(active_id):
    return [{"id": i, "scale": 1.0 if i == active_id else 0.0} for i in range(3)]

resp = client.chat.completions.create(
    model="qwen",                          # llama.cpp 忽略此字段
    messages=[{"role":"system","content": PLANNER_SYSTEM},
              {"role":"user","content": planner_input(task)}],
    extra_body={"lora": experts(0)},       # 切到 Planner LoRA
)
```
把 `orchestrator_langgraph.py` 各节点原来的 `ollama.generate(...)` 换成上面这种调用，
`experts(0/1/2)` 分别对应 `planner / executor / debugger` 即可跑通整个 LEAP 系统。
（`system` / `user` 内容直接复用 `data_gen/templates.py`，训练推理同模板。）

> 注意：base 只加载一份，三个 LoRA 共享内存/显存，每请求切换的成本几乎为零 —— 这正是相对
> Baseline B（切换三个全量微调模型）的核心优势，写进评测。
> llama.cpp 不做「不同 adapter 同批并行」，但低并发端侧场景无损失，反换来 CPU 可跑、
> 显存/内存占用极低 —— 与 LEAP「轻量化」定位一致。

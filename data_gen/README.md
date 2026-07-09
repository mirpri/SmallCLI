# Stage 1 · 数据蒸馏管线

用 DeepSeek-V3.2（教师模型）为三个 LoRA 专家蒸馏训练数据，输出 LLaMA-Factory
`alpaca` 格式 JSONL。**不依赖 GPU**，在本地即可运行。

## 依赖
```bash
pip install openai python-dotenv
```
沿用项目根目录 `.env` 中的 `BASE_URL` / `API_KEY`。可选 `TEACHER_MODEL`（默认
`deepseek/deepseek-v3.2-exp`）。

## 一键运行
```bash
cd data_gen
python run_all.py --per-category 40 --workers 8
```
产物（在 `../data/`）：

| 文件 | 用途 | 训练目标 |
|---|---|---|
| `seed_tasks.jsonl` | 任务种子池 | — |
| `planner.jsonl` | Planner 专家 | 用户任务 → 带前缀步骤 list |
| `executor.jsonl` | Executor 专家 | 自然语言 → shell 命令 list |
| `debugger.jsonl` | Debugger 专家 | 命令+报错 → 修正命令 |
| `_pool_*.jsonl` | 中间池（可删） | — |

`per-category=40`（共 10 类）约得 400 条种子任务，最终每个专家约数百~上千条。
先小样跑通：`--per-category 5`。

## 关键设计
- `templates.py` 里的 prompt **训练与推理共用**：LoRA 学到的输入分布 = 生产时
  `slm1/2/3` 发出的输入。改模板必须重训对应 adapter。
- 每个阶段都做**输出校验**（能否 `ast.literal_eval`、前缀是否合法），脏样本直接丢弃。
- 管线**自洽**：Planner 拆出的 `执行命令:` 子步喂给 Executor；Executor 的命令喂给
  Debugger 合成报错场景。

## 单独运行某阶段
```bash
python gen_seed_tasks.py --per-category 40
python gen_planner.py
python gen_executor.py
python gen_debugger.py
```

## 下一步（Stage 2）
`../data/dataset_info.json` 已注册 `leap_planner / leap_executor / leap_debugger`，
可直接被 LLaMA-Factory 引用。训练配置见 `../train/`。

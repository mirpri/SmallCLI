# task_type_api.py
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import os

labels=["综合推理","执行命令","文件编辑"]

# ✅ Load model
MODEL_DIR = "../Class1/task_type_model"
if not os.path.exists(MODEL_DIR):
    raise FileNotFoundError("❌ Model not found! Please train and save it to ./task_type_model")

tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_DIR)


labels_path = os.path.join(MODEL_DIR, "labels.txt")
id2label = {}
with open(labels_path, "r", encoding="utf-8") as f:
    for line in f:
        i, name = line.strip().split("\t")
        id2label[int(i)] = name


def classify_task_type(text: str) -> int:

    # 额外的简单规则
    if("推理" in text or "分析" in text or "生成" in text):
        return 0
    if("执行" in text or "运行" in text or "查看" in text):
        return 1
    if("修改" in text or "写入" in text or "编辑" in text):
        return 2

    inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True)
    with torch.no_grad():
        logits = model(**inputs).logits
        pred_id = torch.argmax(logits, dim=-1).item()
    return pred_id

def classify_label(text: str) -> str:
    pred_id = classify_task_type(text)
    return id2label[pred_id]


if __name__ == "__main__":
    print("💬 Task Type Classifier (0=Reasoning, 1=Command, 2=File Edit)")
    while True:
        try:
            text = input("输入一句话 > ").strip()
            if not text or text.lower() in {"exit", "quit"}:
                break
            label = classify_label(text)
            print(f"预测类别: {label}")
        except KeyboardInterrupt:
            break

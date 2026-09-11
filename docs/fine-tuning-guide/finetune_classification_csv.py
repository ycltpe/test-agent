"""
微调入门示例 3：从 CSV 加载真实数据做中文情感分类

这个脚本演示如何从 CSV 文件加载数据，并在你的 Mac MPS / CUDA / CPU 上微调 BERT。
你只需要准备两列 CSV：text（文本）和 label（0=负面，1=正面）。

运行：
    cd docs/fine-tuning-guide
    python finetune_classification_csv.py

自定义数据：
    直接替换 data/train.csv 和 data/val.csv 里的内容即可。
"""

from __future__ import annotations

import numpy as np
import torch
from datasets import load_dataset
from sklearn.metrics import accuracy_score, f1_score
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    EarlyStoppingCallback,
    Trainer,
    TrainingArguments,
)

# =============================================================================
# 1. 配置
# =============================================================================
MODEL_NAME = "distilbert-base-multilingual-cased"
TRAIN_CSV = "data/train.csv"
VAL_CSV = "data/val.csv"
OUTPUT_DIR = "./results_classification_csv"
MAX_LENGTH = 128

# 标签映射：0=负面，1=正面
id2label = {0: "负面", 1: "正面"}
label2id = {"负面": 0, "正面": 1}

# =============================================================================
# 2. 从 CSV 加载数据
# =============================================================================
print("正在加载 CSV 数据...")

# load_dataset 会自动识别 CSV 文件，并转换成 Hugging Face Dataset
dataset = load_dataset("csv", data_files={"train": TRAIN_CSV, "val": VAL_CSV})

print(f"训练样本数: {len(dataset['train'])}")
print(f"验证样本数: {len(dataset['val'])}")
print(f"训练数据前 3 条:\n{dataset['train'][:3]}")

# =============================================================================
# 3. 加载模型和分词器
# =============================================================================
print("\n正在加载模型和分词器...")

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

model = AutoModelForSequenceClassification.from_pretrained(
    MODEL_NAME,
    num_labels=2,
    id2label=id2label,
    label2id=label2id,
)

# =============================================================================
# 4. 数据预处理
# =============================================================================
def preprocess_function(examples: dict) -> dict:
    """把文本转换成模型需要的 token IDs 和 attention mask。"""
    return tokenizer(
        examples["text"],
        truncation=True,
        padding="max_length",
        max_length=MAX_LENGTH,
    )


tokenized_dataset = dataset.map(preprocess_function, batched=True)

# 设置 PyTorch 格式，并重命名 label 列为 labels（Hugging Face Trainer 需要）
tokenized_dataset = tokenized_dataset.rename_column("label", "labels")
tokenized_dataset.set_format("torch", columns=["input_ids", "attention_mask", "labels"])

# =============================================================================
# 5. 评估函数
# =============================================================================
def compute_metrics(eval_pred: tuple) -> dict:
    """计算准确率和 F1 分数。"""
    logits, labels = eval_pred
    predictions = np.argmax(logits, axis=-1)
    return {
        "accuracy": accuracy_score(labels, predictions),
        "f1": f1_score(labels, predictions, average="binary"),
    }


# =============================================================================
# 6. 训练参数
# =============================================================================
training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    num_train_epochs=10,              # 数据多了，可以多训几轮
    per_device_train_batch_size=8,    # 根据显存调整
    per_device_eval_batch_size=8,
    learning_rate=2e-5,
    warmup_ratio=0.1,                 # 按比例自动计算 warmup 步数
    weight_decay=0.01,
    eval_strategy="epoch",
    save_strategy="epoch",
    load_best_model_at_end=True,
    metric_for_best_model="f1",
    greater_is_better=True,
    logging_steps=5,
    seed=42,
    dataloader_pin_memory=False,  # MPS 不支持 pin_memory，设为 False 避免警告
)

# =============================================================================
# 7. 创建 Trainer 并训练
# =============================================================================
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_dataset["train"],
    eval_dataset=tokenized_dataset["val"],
    processing_class=tokenizer,
    compute_metrics=compute_metrics,
    callbacks=[EarlyStoppingCallback(early_stopping_patience=3)],
)

print("\n开始训练...")
trainer.train()

# =============================================================================
# 8. 评估
# =============================================================================
print("\n最终评估结果:")
eval_result = trainer.evaluate()
print(eval_result)

# =============================================================================
# 9. 预测示例
# =============================================================================
test_sentences = [
    "这次体验非常棒，服务很好！",
    "太差了，再也不会来了。",
    "中规中矩吧，没什么特别的感觉。",
    "画质清晰，运行流畅，性价比很高。",
    "等了一个小时，服务态度还很差。",
]

print("\n预测示例:")
model.eval()  # 切换到评估模式
for sentence in test_sentences:
    inputs = tokenizer(
        sentence,
        return_tensors="pt",
        truncation=True,
        padding=True,
        max_length=MAX_LENGTH,
    ).to(model.device)

    with torch.no_grad():  # 推理时不需要计算梯度
        outputs = model(**inputs)

    predicted_id = int(np.argmax(outputs.logits.detach().cpu().numpy(), axis=-1)[0])
    print(f"  输入: {sentence}")
    print(f"  预测: {id2label[predicted_id]}\n")

# =============================================================================
# 10. 保存模型
# =============================================================================
save_path = "./sentiment_model_csv"
model.save_pretrained(save_path)
tokenizer.save_pretrained(save_path)
print(f"模型已保存到: {save_path}")

print("\n提示：")
print("- 现在你可以用真实业务数据替换 data/ 下的 CSV 文件；")
print("- CSV 只需要两列：text 和 label；")
print("- 数据量越大、覆盖场景越全，效果通常越好；")
print("- 可以通过调整 learning_rate、batch_size、epochs 来优化效果。")

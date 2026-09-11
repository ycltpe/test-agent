"""
微调入门示例 1：中文情感分类

使用 distilbert-base-multilingual-cased 在一个小型中文数据集上做二分类。
这个脚本 CPU 可跑，适合理解微调的基本流程。

运行：
    cd docs/fine-tuning-guide
    pip install -r requirements.txt
    python finetune_classification.py
"""

from __future__ import annotations

import numpy as np
from datasets import Dataset
from sklearn.metrics import accuracy_score, f1_score
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    EarlyStoppingCallback,
    Trainer,
    TrainingArguments,
)

# =============================================================================
# 1. 准备数据
# =============================================================================
# 这里用一个硬编码的小数据集演示。实际项目中，你会从文件或数据库加载数据。
train_data = [
    {"text": "这部电影真的太精彩了，强烈推荐！", "label": 1},
    {"text": "剧情紧凑，演员演技在线，值得一看。", "label": 1},
    {"text": "画面很美，音乐也很棒，非常感动。", "label": 1},
    {"text": "故事情节很吸引人，结局出乎意料。", "label": 1},
    {"text": "导演功力深厚，每个镜头都很讲究。", "label": 1},
    {"text": "完全看不下去，浪费了我两个小时。", "label": 0},
    {"text": "剧情老套，人物塑造单薄，很失望。", "label": 0},
    {"text": "特效五毛，演技尴尬，不推荐。", "label": 0},
    {"text": "节奏拖沓，看到一半就想离场。", "label": 0},
    {"text": "故事逻辑混乱，不知所云。", "label": 0},
    {"text": "虽然题材不错，但执行得不够好。", "label": 0},
    {"text": "演员表演到位，配乐也很加分。", "label": 1},
]

val_data = [
    {"text": "整体体验很好，会再来的。", "label": 1},
    {"text": "服务质量差，态度也不好。", "label": 0},
    {"text": "性价比很高，满意。", "label": 1},
    {"text": "等了很久，体验很差。", "label": 0},
]

# 标签映射：0=负面，1=正面
id2label = {0: "负面", 1: "正面"}
label2id = {"负面": 0, "正面": 1}

# 转换成 Hugging Face Dataset 对象
train_ds = Dataset.from_list(train_data)
val_ds = Dataset.from_list(val_data)

print(f"训练样本数: {len(train_ds)}")
print(f"验证样本数: {len(val_ds)}")

# =============================================================================
# 2. 选择模型和分词器
# =============================================================================
MODEL_NAME = "distilbert-base-multilingual-cased"

# 加载分词器
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

# 加载预训练模型，并指定分类头输出 2 个类别
model = AutoModelForSequenceClassification.from_pretrained(
    MODEL_NAME,
    num_labels=2,
    id2label=id2label,
    label2id=label2id,
)

# =============================================================================
# 3. 数据预处理
# =============================================================================
MAX_LENGTH = 128


def preprocess_function(examples: dict) -> dict:
    """把原始文本转成模型需要的 input_ids 和 attention_mask。"""
    return tokenizer(
        examples["text"],
        truncation=True,
        padding="max_length",
        max_length=MAX_LENGTH,
    )


tokenized_train = train_ds.map(preprocess_function, batched=True)
tokenized_val = val_ds.map(preprocess_function, batched=True)

# 设置数据格式，让 PyTorch 能直接读取
# Hugging Face Dataset 默认返回的是普通字典，需要设置成 torch 张量格式
tokenized_train.set_format("torch", columns=["input_ids", "attention_mask", "label"])
tokenized_val.set_format("torch", columns=["input_ids", "attention_mask", "label"])

# 注意：Hugging Face 的分类模型期望字段名是 "labels" 而不是 "label"
# 这里我们重命名一下
tokenized_train = tokenized_train.rename_column("label", "labels")
tokenized_val = tokenized_val.rename_column("label", "labels")

# =============================================================================
# 4. 定义评估函数
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
# 5. 配置训练参数
# =============================================================================
training_args = TrainingArguments(
    output_dir="./results_classification",
    num_train_epochs=5,               # 训练轮数
    per_device_train_batch_size=4,    # 每个设备的训练批次大小
    per_device_eval_batch_size=4,     # 每个设备的验证批次大小
    learning_rate=2e-5,               # 学习率（全参数微调常用 1e-5 ~ 5e-5）
    warmup_steps=5,                   # 预热步数
    weight_decay=0.01,                # 权重衰减，防止过拟合
    eval_strategy="epoch",            # 每个 epoch 评估一次
    save_strategy="epoch",            # 每个 epoch 保存一次
    load_best_model_at_end=True,      # 训练结束后加载验证集上最好的模型
    metric_for_best_model="f1",       # 用 F1 来选择最佳模型
    greater_is_better=True,
    logging_steps=1,                  # 每步都打印日志
    seed=42,
    # 如果只有 CPU，就把下面这行去掉或改成 "cpu"
    # no_cuda=True,
)

# =============================================================================
# 6. 创建 Trainer 并开始训练
# =============================================================================
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_train,
    eval_dataset=tokenized_val,
    processing_class=tokenizer,
    compute_metrics=compute_metrics,
    callbacks=[EarlyStoppingCallback(early_stopping_patience=2)],  # 早停
)

print("\n开始训练...")
trainer.train()

# =============================================================================
# 7. 评估与预测
# =============================================================================
print("\n最终评估结果:")
eval_result = trainer.evaluate()
print(eval_result)

# 用训练好的模型做几个预测
test_sentences = [
    "这次体验非常棒，服务很好！",
    "太差了，再也不会来了。",
    "中规中矩吧，没什么特别的感觉。",
]

print("\n预测示例:")
for sentence in test_sentences:
    inputs = tokenizer(
        sentence,
        return_tensors="pt",
        truncation=True,
        padding=True,
        max_length=MAX_LENGTH,
    ).to(model.device)
    outputs = model(**inputs)
    predicted_id = int(np.argmax(outputs.logits.detach().cpu().numpy(), axis=-1)[0])
    print(f"  输入: {sentence}")
    print(f"  预测: {id2label[predicted_id]}\n")

# =============================================================================
# 8. 保存模型
# =============================================================================
save_path = "./sentiment_model"
model.save_pretrained(save_path)
tokenizer.save_pretrained(save_path)
print(f"模型已保存到: {save_path}")

print("\n提示：")
print("- 这个示例数据量很小，仅用于理解流程；")
print("- 真实项目建议至少准备几百到几千条标注数据；")
print("- 如果显存不足，可以减小 batch_size 或 max_length。")

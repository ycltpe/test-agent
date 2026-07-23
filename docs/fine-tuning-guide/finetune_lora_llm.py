"""
微调入门示例 2：使用 LoRA 进行大语言模型指令微调

这个脚本演示如何用 LoRA 微调 Qwen2-0.5B-Instruct，让它更好地遵循中文指令。
0.5B 模型很小，单张 GPU 即可运行（包括 Apple Silicon 的 MPS）。

运行：
    cd docs/fine-tuning-guide
    pip install -r requirements.txt
    python finetune_lora_llm.py

Apple Silicon（M1/M2/M3/M4/M5）用户：
- 脚本会自动检测 MPS 并使用统一内存
- 32GB 内存的 Mac 可以轻松跑 0.5B 模型
- 不建议在 MPS 上开 fp16 或 8-bit，已自动规避
"""

from __future__ import annotations

import torch
from datasets import Dataset
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments
from trl import SFTTrainer, DataCollatorForCompletionOnlyLM

# =============================================================================
# 1. 配置
# =============================================================================
MODEL_NAME = "Qwen/Qwen2-0.5B-Instruct"
OUTPUT_DIR = "./results_lora_llm"
MAX_SEQ_LENGTH = 512

# LoRA 参数
LORA_R = 16          # 低秩维度
LORA_ALPHA = 32      # 缩放参数
LORA_DROPOUT = 0.05  # Dropout

# 训练参数
LEARNING_RATE = 2e-4
BATCH_SIZE = 2
NUM_EPOCHS = 3

# =============================================================================
# 2. 准备指令数据
# =============================================================================
# 示例：让模型学习把口语化表达改写成正式邮件
train_data = [
    {
        "instruction": "把下面这句话改写成正式邮件语气。",
        "input": "嘿，明天下午三点开会，别忘了把报告带过来。",
        "output": "您好，谨提醒您明日（下午三点）会议请携带报告，感谢您的配合。",
    },
    {
        "instruction": "把下面这句话改写成正式邮件语气。",
        "input": "那个方案我看完了，感觉还行，你再改改吧。",
        "output": "您好，方案已阅，整体方向可行，建议对部分细节进一步优化后再提交。",
    },
    {
        "instruction": "把下面这句话改写成正式邮件语气。",
        "input": "这个 bug 什么时候能修好啊？客户都催了好几遍了。",
        "output": "您好，该问题客户已多次跟进，烦请确认修复计划并及时同步预期完成时间。",
    },
    {
        "instruction": "把下面这句话改写成正式邮件语气。",
        "input": "周末能加班把这份报告赶出来吗？",
        "output": "您好，因项目需要，能否请您在周末前完成该报告？如可行，请确认预计交付时间。",
    },
    {
        "instruction": "请用一句话总结以下会议要点。",
        "input": "市场部建议加大短视频投放，技术部提出需要两周开发新落地页，财务部希望控制预算在 50 万以内。",
        "output": "本次会议达成初步共识：市场部将推动短视频投放，技术部评估两周内上线新落地页，整体预算控制在 50 万元以内。",
    },
    {
        "instruction": "请用一句话总结以下会议要点。",
        "input": "产品下周发布 2.0 版本，运营团队准备线上发布会，客服团队需要提前准备 FAQ。",
        "output": "产品 2.0 版本定于下周发布，运营与客服团队需分别筹备发布会及 FAQ。",
    },
]

# 构建对话格式（Qwen 的 ChatML 格式）
def format_example(example: dict) -> dict:
    messages = [
        {"role": "system", "content": "你是一个专业的中文写作助手。"},
        {"role": "user", "content": f"{example['instruction']}\n{example['input']}"},
        {"role": "assistant", "content": example["output"]},
    ]
    return {"messages": messages}


dataset = Dataset.from_list([format_example(d) for d in train_data])

# =============================================================================
# 3. 加载模型和分词器
# =============================================================================
print("正在加载模型和分词器...")

# 加载 8-bit 量化模型可以显著降低显存占用
# 如果显存足够，可以去掉 load_in_8bit=True
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    torch_dtype=torch.float16,
    device_map="auto",  # 自动分配层到 GPU/CPU
    # load_in_8bit=True,  # 显存紧张时开启
)

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
tokenizer.pad_token = tokenizer.eos_token  # 设置 padding token
tokenizer.padding_side = "right"  # SFT 训练通常用 right padding

# =============================================================================
# 4. 配置 LoRA
# =============================================================================
peft_config = LoraConfig(
    r=LORA_R,
    lora_alpha=LORA_ALPHA,
    lora_dropout=LORA_DROPOUT,
    target_modules=[
        "q_proj",
        "k_proj",
        "v_proj",
        "o_proj",
        "gate_proj",
        "up_proj",
        "down_proj",
    ],
    bias="none",
    task_type="CAUSAL_LM",
)

# 把 LoRA 加到模型上
model = get_peft_model(model, peft_config)
model.print_trainable_parameters()  # 打印可训练参数占比

# =============================================================================
# 5. 数据格式化函数
# =============================================================================
def formatting_prompts_func(examples: dict) -> list:
    """把对话列表转成模型训练所需的文本。"""
    texts = []
    for messages in examples["messages"]:
        text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
        texts.append(text)
    return {"text": texts}


dataset = dataset.map(formatting_prompts_func, batched=True)

# =============================================================================
# 6. 训练参数
# =============================================================================
training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    num_train_epochs=NUM_EPOCHS,
    per_device_train_batch_size=BATCH_SIZE,
    gradient_accumulation_steps=4,  # 有效 batch_size = 2 * 4 = 8
    learning_rate=LEARNING_RATE,
    warmup_ratio=0.1,
    logging_steps=1,
    save_strategy="epoch",
    fp16=True,  # 混合精度训练，加速并省显存
    optim="paged_adamw_8bit",  # 8-bit 优化器，省显存
    report_to="none",  # 不上传到 wandb/tensorboard
)

# =============================================================================
# 7. 开始训练
# =============================================================================
# DataCollatorForCompletionOnlyLM 的作用：只计算 assistant 回答部分的 loss，
# 不计算 system/user 部分的 loss，这样训练更高效。
response_template = "\n<|im_start|>assistant\n"
collator = DataCollatorForCompletionOnlyLM(
    response_template=response_template,
    tokenizer=tokenizer,
)

# 注意：DataCollatorForCompletionOnlyLM 需要识别 response_template 在 tokenized 后的位置
# 对于 Qwen 的 chat template，也可以不用 collator，直接训练整个序列（效果略差但更稳定）
# 这里为了简化，先不使用 collator，让模型学习整个对话

print("\n开始训练...")
trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=dataset,
    dataset_text_field="text",
    max_seq_length=MAX_SEQ_LENGTH,
    args=training_args,
    # data_collator=collator,  # 有经验后再开启
)

trainer.train()

# =============================================================================
# 8. 保存 LoRA 权重
# =============================================================================
lora_save_path = "./lora_email_assistant"
model.save_pretrained(lora_save_path)
tokenizer.save_pretrained(lora_save_path)
print(f"\nLoRA 权重已保存到: {lora_save_path}")

# =============================================================================
# 9. 推理测试
# =============================================================================
print("\n推理测试:")

test_messages = [
    {"role": "system", "content": "你是一个专业的中文写作助手。"},
    {"role": "user", "content": "把下面这句话改写成正式邮件语气。\n嘿，明天把合同发我一下，急用。"},
]

inputs = tokenizer.apply_chat_template(
    test_messages,
    tokenize=True,
    return_tensors="pt",
    add_generation_prompt=True,
).to(model.device)

outputs = model.generate(
    inputs,
    max_new_tokens=128,
    do_sample=True,
    temperature=0.7,
    top_p=0.9,
)

response = tokenizer.decode(outputs[0][inputs.shape[1]:], skip_special_tokens=True)
print(f"输入: 嘿，明天把合同发我一下，急用。")
print(f"输出: {response}")

print("\n提示：")
print("- 这个脚本使用很小的示例数据，仅作演示；")
print("- 真实指令微调建议准备 1000+ 高质量样本；")
print("- 如果显存不足，可以开启 load_in_8bit=True 或换更小的模型；")
print("- 训练完成后，可以用 model.merge_and_unload() 把 LoRA 合并到基座模型。")

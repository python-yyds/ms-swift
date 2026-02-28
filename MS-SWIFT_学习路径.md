# MS-SWIFT 框架学习路径

> 针对科研和工作需求的系统化代码学习方案

## 📋 项目概览

**MS-SWIFT** 是魔搭社区开发的大模型微调部署框架，支持：
- 600+ 纯文本大模型 + 300+ 多模态大模型
- 预训练、微调、人类对齐、推理、评测、量化、部署全链路
- LoRA/QLoRA/全参数等多种训练方式
- Megatron 并行技术（TP/PP/SP/CP/EP 等）
- GRPO 算法族强化学习
- vLLM/SGLang/LMDeploy 推理加速

---

## 🎯 学习目标

1. **理解框架架构**：掌握整体设计思想和模块划分
2. **熟悉核心实现**：深入理解关键组件的代码实现
3. **实践应用能力**：能够基于框架进行科研创新和工程开发
4. **扩展开发能力**：能够添加新模型、新算法、新功能

---

## 📚 第一阶段：基础准备（1-2周）

### 1.1 环境搭建与基础知识
```bash
# 安装框架
cd /mnt/ai4s/zhouhaojie/liuzhanyang/21/nice/ms-swift
pip install -e .

# 安装依赖
pip install -r requirements/framework.txt
```

**必备知识储备：**
- ✅ PyTorch 基础（nn.Module、Tensor操作、自动微分）
- ✅ Transformers 库（模型加载、Tokenizer、生成）
- ✅ Python 高级特性（装饰器、元类、上下文管理器、类型提示）
- ✅ 分布式训练基础（DDP、FSDP概念）

**推荐阅读：**
- `README_CN.md` - 了解框架整体能力
- `docs/source/Instruction/Command-line-parameters.html` - 命令行参数
- 论文：https://arxiv.org/abs/2408.05517

### 1.2 运行示例代码
**目的：** 建立感性认识，理解框架使用流程

```bash
# 1. 快速开始示例
examples/train/lora_sft.sh              # LoRA微调
examples/infer/infer.sh                 # 推理
examples/export/export.sh               # 导出和量化

# 2. 多模态示例
examples/train/multimodal/              # 多模态训练

# 3. RLHF示例
examples/train/rlhf/dpo/                # DPO训练
examples/train/grpo/                    # GRPO训练
```

**学习要点：**
- 观察命令行参数如何传递
- 理解训练流程：数据加载 → 模型加载 → 训练 → 保存
- 查看生成的输出文件结构

---

## 🏗️ 第二阶段：核心架构理解（2-3周）

### 2.1 项目结构总览

```
ms-swift/
├── swift/
│   ├── llm/              # LLM相关核心功能
│   │   ├── model/        # 模型注册和加载
│   │   ├── template/     # 对话模板系统
│   │   ├── dataset/      # 数据集处理
│   │   ├── train/        # 训练入口
│   │   ├── infer/        # 推理引擎
│   │   ├── eval/         # 评测
│   │   └── export/       # 导出和量化
│   ├── trainers/         # 训练器实现
│   ├── tuners/           # 微调方法（LoRA等）
│   ├── megatron/         # Megatron并行
│   ├── plugin/           # 插件系统
│   └── utils/            # 工具函数
├── examples/             # 示例代码
└── docs/                 # 文档
```

### 2.2 代码流程追踪

**学习路径：** 从入口点开始，逐步深入

#### 阶段 2.2.1：CLI入口分析
**文件：** `swift/cli/main.py`

```python
# 关键点：
# 1. 如何解析命令行参数
# 2. 如何路由到不同的功能模块（sft/infer/export等）
# 3. 参数如何传递给底层函数
```

**学习任务：**
- [ ] 阅读 `swift/cli/main.py` 理解命令行入口
- [ ] 查看 `swift/cli/sft.py`、`swift/cli/infer.py` 等子命令实现
- [ ] 理解参数解析机制（基于argparse/dataclass）

#### 阶段 2.2.2：参数系统
**文件：** `swift/llm/argument/`

```python
# 核心类：
# - TrainArguments: 训练参数
# - InferArguments: 推理参数
# - ExportArguments: 导出参数
# - RLHFArguments: RLHF参数
```

**学习任务：**
- [ ] 研究 `swift/llm/argument/train_args.py` 参数继承关系
- [ ] 了解如何从命令行参数构建 Arguments 对象
- [ ] 理解参数验证和默认值设置机制

#### 阶段 2.2.3：模型注册与加载系统
**文件：** `swift/llm/model/`

**核心概念：**
```python
# 1. 模型注册机制
MODEL_MAPPING = {}  # 模型ID到ModelMeta的映射

# 2. ModelMeta：存储模型元信息
@dataclass
class ModelMeta:
    model_id: str
    model_arch: ModelArch
    template: str
    requires: List[str]
    ...

# 3. 模型加载流程
get_model_tokenizer() -> (model, tokenizer)
```

**学习任务：**
- [ ] 阅读 `swift/llm/model/register.py` - 模型注册机制
- [ ] 查看 `swift/llm/model/model/__init__.py` - 具体模型注册
- [ ] 理解 `swift/llm/model/loader.py` - 模型加载逻辑
- [ ] 学习如何添加新模型支持

**实践任务：**
```python
# 尝试注册一个自定义模型
from swift.llm import register_model, ModelMeta, ModelArch

register_model(
    ModelMeta(
        model_id='your-org/your-model',
        model_arch=ModelArch.llama,
        template='default-generation',
        ...
    )
)
```

#### 阶段 2.2.4：模板系统（Template）
**文件：** `swift/llm/template/`

**核心功能：**
- 对话格式转换（messages ↔ text）
- 特殊token处理（BOS/EOS/系统提示）
- 多模态内容处理（图像/视频/音频）

**学习任务：**
- [ ] 阅读 `swift/llm/template/base.py` - Template基类
- [ ] 查看 `swift/llm/template/template/` - 具体模板实现
- [ ] 理解 `TemplateInputs` 和编码流程
- [ ] 学习如何自定义对话模板

**关键代码：**
```python
# Template的核心方法
class Template:
    def encode(self, example: Dict) -> Dict:
        # 将原始数据转换为模型输入
        pass
    
    def data_collator(self, batch: List[Dict]) -> Dict:
        # 批处理和padding
        pass
```

#### 阶段 2.2.5：数据集系统
**文件：** `swift/llm/dataset/`

**核心组件：**
```python
# 1. 数据集注册
DATASET_MAPPING = {}

# 2. 预处理器
- AlpacaPreprocessor      # Alpaca格式
- MessagesPreprocessor    # 对话格式
- EncodePreprocessor      # 编码为tokens

# 3. 数据加载
load_dataset() -> HfDataset
```

**学习任务：**
- [ ] 阅读 `swift/llm/dataset/register.py` - 数据集注册
- [ ] 理解 `swift/llm/dataset/preprocessor.py` - 预处理流程
- [ ] 查看 `swift/llm/dataset/loader.py` - 数据加载
- [ ] 学习自定义数据集格式

---

## 🔧 第三阶段：训练系统深入（3-4周）

### 3.1 Tuners - 微调方法实现
**文件：** `swift/tuners/`

**核心微调方法：**

#### LoRA实现
**文件：** `swift/tuners/lora.py`, `swift/tuners/lora_layers.py`

```python
# 关键点：
# 1. 如何替换Linear层为LoRALinear
# 2. 低秩矩阵A和B的初始化
# 3. 前向传播计算：output = base_output + scaling * (x @ A @ B)
# 4. 参数冻结和梯度管理
```

**学习任务：**
- [ ] 阅读 `LoRAConfig` 参数配置
- [ ] 理解 `LoRALinear` 层实现
- [ ] 查看 `Swift.prepare_model()` 如何注入LoRA
- [ ] 对比PEFT库的实现差异

#### 其他Tuner
- [ ] `swift/tuners/adapter.py` - Adapter方法
- [ ] `swift/tuners/prompt.py` - Prompt Tuning
- [ ] `swift/tuners/reft.py` - ReFT
- [ ] `swift/tuners/llamapro.py` - LLaMA-Pro

### 3.2 训练器系统
**文件：** `swift/trainers/`

**核心架构：**
```python
# 继承关系
Trainer (HF) 
  ↓
SwiftMixin 
  ↓  
Seq2SeqTrainer (MS-SWIFT)
```

**学习任务：**
- [ ] 阅读 `swift/trainers/trainers.py` - 训练器实现
- [ ] 理解 `swift/trainers/mixin.py` - 核心功能混入
- [ ] 查看 `swift/trainers/arguments.py` - TrainingArguments扩展
- [ ] 学习 `swift/trainers/callback.py` - 回调机制

**关键功能：**
```python
class SwiftMixin:
    # 1. 模型保存和加载
    def save_model()
    def _load_from_checkpoint()
    
    # 2. 梯度检查点
    def _prepare_model_for_training()
    
    # 3. 损失计算
    def compute_loss()
    
    # 4. Packing优化
    def pack_dataset()
```

### 3.3 训练流程完整追踪

**入口：** `swift/llm/train/sft.py:sft_main()`

**完整流程：**
```python
# 1. 参数解析
args = TrainArguments.from_args()

# 2. 模型和分词器加载
model, tokenizer = get_model_tokenizer(args.model, ...)

# 3. 获取模板
template = get_template(args.template, tokenizer)

# 4. 应用微调方法
if args.train_type == 'lora':
    model = Swift.prepare_model(model, {'lora': lora_config})

# 5. 加载数据集
train_dataset = load_dataset(args.dataset)
train_dataset = EncodePreprocessor(template)(train_dataset)

# 6. 创建训练器
trainer = Seq2SeqTrainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    data_collator=template.data_collator,
)

# 7. 开始训练
trainer.train()

# 8. 保存模型
trainer.save_model()
```

**学习任务：**
- [ ] 逐步调试上述流程，打断点观察每一步
- [ ] 理解数据如何流经整个pipeline
- [ ] 查看中间产物（编码后的tokens、loss值等）

### 3.4 RLHF训练系统
**文件：** `swift/trainers/rlhf_trainer/`

**支持的算法：**
- DPO/CPO/SimPO/ORPO
- KTO
- Reward Model (RM)
- PPO
- GRPO及其变体

**学习重点（以DPO为例）：**
- [ ] 阅读 `swift/trainers/rlhf_trainer/dpo_trainer.py`
- [ ] 理解DPO损失函数实现
- [ ] 查看reference model的处理
- [ ] 学习偏好数据的处理流程

**GRPO系统：**
- [ ] `swift/plugin/grpo/` - GRPO核心实现
- [ ] 理解policy model和reward model的交互
- [ ] 学习vLLM集成用于推理加速
- [ ] 研究不同GRPO变体的差异

---

## ⚡ 第四阶段：推理与部署（2-3周）

### 4.1 推理引擎架构
**文件：** `swift/llm/infer/`

**多引擎支持：**
```python
# 1. PyTorch原生引擎
PtEngine          # swift/llm/infer/pt_engine.py

# 2. vLLM引擎
VllmEngine        # swift/llm/infer/vllm_engine.py

# 3. LMDeploy引擎
LmdeployEngine    # swift/llm/infer/lmdeploy_engine.py

# 4. SGLang引擎
SglangEngine      # swift/llm/infer/sglang_engine.py
```

**学习任务：**
- [ ] 阅读 `swift/llm/infer/base_infer_engine.py` - 基类抽象
- [ ] 理解统一的 `InferRequest` 和 `RequestConfig` 接口
- [ ] 查看各引擎的具体实现差异
- [ ] 学习如何切换推理后端

**关键接口：**
```python
class BaseInferEngine:
    def infer(self, infer_requests: List[InferRequest], 
              request_config: RequestConfig) -> List[Response]:
        pass
```

### 4.2 部署系统
**文件：** `swift/llm/infer/deploy.py`

**功能：**
- OpenAI兼容API服务器
- 流式生成支持
- 多模型并发服务

**学习任务：**
- [ ] 查看FastAPI服务搭建
- [ ] 理解请求路由和处理
- [ ] 学习并发请求管理

---

## 🚀 第五阶段：高级特性（3-4周）

### 5.1 Megatron并行技术
**文件：** `swift/megatron/`

**并行策略：**
- Tensor Parallelism (TP)
- Pipeline Parallelism (PP)
- Sequence Parallelism (SP)
- Context Parallelism (CP)
- Expert Parallelism (EP)

**学习任务：**
- [ ] 阅读 `swift/megatron/init.py` - Megatron初始化
- [ ] 理解 `swift/megatron/trainers/` - Megatron训练器
- [ ] 查看 `swift/megatron/model/` - 模型并行化
- [ ] 学习MoE模型优化（重点）

**推荐资源：**
- Megatron-LM官方文档
- `docs/source/Megatron-SWIFT/`

### 5.2 序列并行
**文件：** `swift/trainers/sequence_parallel/`

**技术：**
- Ulysses Attention
- Ring Attention
- 长序列训练优化

**学习任务：**
- [ ] 理解注意力计算的并行化
- [ ] 查看通信原语实现
- [ ] 学习显存优化技巧

### 5.3 插件系统
**文件：** `swift/plugin/`

**可扩展组件：**
```python
# 损失函数
swift/plugin/loss.py

# 评估指标
swift/plugin/metric.py

# 优化器
swift/plugin/optimizer.py

# Agent模板
swift/plugin/agent_template/

# ORM (Outcome Reward Model)
swift/plugin/orm.py

# PRM (Process Reward Model)
swift/plugin/prm.py
```

**学习任务：**
- [ ] 理解插件注册机制
- [ ] 学习如何添加自定义损失函数
- [ ] 查看Agent训练模板系统
- [ ] 研究奖励模型的实现

### 5.4 量化与导出
**文件：** `swift/llm/export/`

**支持的量化方法：**
- AWQ
- GPTQ
- BNB (4bit/8bit)
- FP8

**学习任务：**
- [ ] 阅读 `swift/llm/export/export.py` - 导出流程
- [ ] 理解 `swift/llm/export/quantize.py` - 量化实现
- [ ] 查看各量化方法的校准数据使用
- [ ] 学习量化模型的保存格式

---

## 🎓 第六阶段：源码级深入与实践（持续）

### 6.1 关键技术点深入

#### 6.1.1 Flash Attention集成
**文件：** 搜索 `flash_attn` 相关代码

**学习点：**
- 如何检测和启用Flash Attention
- 对不同模型架构的适配
- 显存和速度优化效果

#### 6.1.2 梯度累积与混合精度
**相关代码：**
- `swift/trainers/arguments.py` - 混合精度配置
- `gradient_accumulation_steps` 实现

#### 6.1.3 Packing技术
**文件：** 搜索 `pack_dataset`

**学习点：**
- 多个样本打包到一个序列
- 注意力mask的构造
- 效率提升原理

#### 6.1.4 多模态处理
**文件：** `swift/llm/template/template/multimodal/`

**学习点：**
- 图像/视频/音频编码
- 多模态token融合
- Vision Transformer集成

### 6.2 实践项目

#### 项目1：添加新模型支持
**任务：** 为一个新开源模型添加MS-SWIFT支持

**步骤：**
1. 在 `swift/llm/model/model/` 注册模型
2. 在 `swift/llm/template/template/` 添加对话模板
3. 测试训练和推理
4. 提交PR到官方仓库

#### 项目2：实现自定义微调方法
**任务：** 实现一个新的PEFT方法（如论文中的方法）

**步骤：**
1. 在 `swift/tuners/` 创建新文件
2. 继承 `SwiftAdapter` 或 `PeftModel`
3. 实现参数注入和前向传播
4. 集成到训练流程

#### 项目3：开发自定义RLHF算法
**任务：** 实现一个新的强化学习算法

**步骤：**
1. 在 `swift/trainers/rlhf_trainer/` 创建trainer
2. 实现损失函数和优化逻辑
3. 集成到CLI
4. 在基准数据集上验证

#### 项目4：优化推理性能
**任务：** 为特定场景优化推理速度

**方向：**
- 实现speculative decoding
- 优化KV cache管理
- 添加量化支持

### 6.3 代码阅读技巧

**工具推荐：**
```bash
# 1. 使用grep搜索关键词
grep -r "LoRALinear" swift/

# 2. 使用tree查看目录结构
tree swift/llm -L 2

# 3. 使用pdb调试
python -m pdb swift/cli/main.py sft ...

# 4. 使用VSCode/PyCharm的跳转功能
# Ctrl+Click 跳转到定义
# Ctrl+Shift+F 全局搜索
```

**阅读策略：**
1. **自顶向下**：从CLI入口开始，逐层深入
2. **自底向上**：从基础组件（Layer/Module）开始理解
3. **场景驱动**：选择一个具体场景（如LoRA微调），追踪完整流程
4. **对比学习**：对比MS-SWIFT与HuggingFace/PEFT的实现差异

---

## 📖 推荐学习资源

### 官方资源
- 📚 [中文文档](https://swift.readthedocs.io/zh-cn/latest/)
- 📚 [英文文档](https://swift.readthedocs.io/en/latest/)
- 📄 [论文](https://arxiv.org/abs/2408.05517)
- 💬 [GitHub Issues](https://github.com/modelscope/ms-swift/issues)
- 💬 Discord/微信群（见README）

### 相关技术论文
**微调方法：**
- LoRA: https://arxiv.org/abs/2106.09685
- QLoRA: https://arxiv.org/abs/2305.14314
- AdaLoRA: https://arxiv.org/abs/2303.10512

**强化学习：**
- DPO: https://arxiv.org/abs/2305.18290
- GRPO: 查看MS-SWIFT文档

**并行技术：**
- Megatron-LM: https://arxiv.org/abs/1909.08053
- Ulysses: https://arxiv.org/abs/2309.14509

### 推荐课程
- Stanford CS324 - Large Language Models
- DeepLearning.AI - Fine-tuning Large Language Models

---

## ✅ 学习检查清单

### 基础能力
- [ ] 能够使用MS-SWIFT进行基础的LoRA微调
- [ ] 理解模型注册和模板系统
- [ ] 能够处理自定义数据集
- [ ] 掌握推理和部署基本流程

### 进阶能力
- [ ] 理解LoRA/Adapter等微调方法的底层实现
- [ ] 能够阅读和修改训练器代码
- [ ] 掌握RLHF训练流程
- [ ] 了解多引擎推理的差异

### 高级能力
- [ ] 能够为新模型添加支持
- [ ] 理解Megatron并行技术
- [ ] 能够实现自定义微调方法
- [ ] 能够开发新的RLHF算法
- [ ] 能够优化推理性能

### 科研能力
- [ ] 能够基于框架实现论文算法
- [ ] 能够进行消融实验和性能对比
- [ ] 能够贡献代码到开源社区
- [ ] 能够撰写技术博客/论文

---

## 🔄 学习建议

### 时间安排
**总计：10-14周（根据个人基础调整）**

- 第1-2周：基础准备
- 第3-5周：核心架构
- 第6-9周：训练系统
- 第10-12周：高级特性
- 第13-14周：项目实践

### 学习方法
1. **边学边做**：每学习一个模块，立即运行相关代码
2. **写技术笔记**：用Markdown记录关键发现和理解
3. **画架构图**：用draw.io等工具绘制模块关系图
4. **提问交流**：在GitHub Issues/Discord提问
5. **代码注释**：在关键代码处添加中文注释

### 调试技巧
```python
# 1. 添加日志
import logging
logger = logging.getLogger(__name__)
logger.info(f"Debug info: {variable}")

# 2. 使用pdb
import pdb; pdb.set_trace()

# 3. 查看张量形状
print(f"tensor shape: {tensor.shape}")

# 4. 保存中间结果
torch.save(intermediate_output, 'debug.pt')
```

### 常见问题解决
- **CUDA OOM**：减小batch_size或使用梯度累积
- **版本冲突**：查看requirements.txt的版本要求
- **模型加载失败**：检查模型ID和网络连接
- **数据格式错误**：参考examples中的数据格式

---

## 🎯 科研应用方向

基于MS-SWIFT可以开展的科研方向：

1. **新微调方法研究**
   - 设计更高效的参数高效微调方法
   - 探索特定任务的微调策略

2. **强化学习算法**
   - 改进GRPO等算法
   - 研究奖励模型设计

3. **多模态学习**
   - 跨模态对齐方法
   - 多模态融合策略

4. **长序列建模**
   - 高效注意力机制
   - 序列并行优化

5. **模型压缩**
   - 新量化方法
   - 知识蒸馏策略

6. **领域适应**
   - 医疗/法律等垂直领域
   - 低资源语言

---

## 📝 学习记录模板

建议创建个人学习笔记：

```markdown
# MS-SWIFT学习日志

## 日期：2025-01-XX

### 今日学习内容
- 阅读了XXX模块的代码
- 理解了YYY功能的实现原理

### 关键发现
- 发现了ZZZ的巧妙设计
- 理解了AAA和BBB的关系

### 遇到的问题
- 问题1：...
- 解决方案：...

### 下一步计划
- [ ] 继续学习XXX
- [ ] 实践YYY功能
```

---

## 🚀 开始学习

**立即行动：**
```bash
# 1. 设置学习分支
cd /mnt/ai4s/zhouhaojie/liuzhanyang/21/nice/ms-swift
git checkout -b learning

# 2. 运行第一个示例
bash examples/train/lora_sft.sh

# 3. 开始阅读源码
code swift/llm/train/sft.py
```

祝你学习顺利！有任何问题欢迎交流讨论。

---

**最后更新：** 2025-01-20
**维护者：** 学习者自己
**参考版本：** MS-SWIFT 3.0+

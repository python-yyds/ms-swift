import time
import json
import logging
import os
import glob
import argparse
from typing import List, Dict, Tuple
from pathlib import Path
from openai import OpenAI

# ================= 配置区域 =================
# 患者模型服务地址 (Server 1)
PATIENT_API_BASE = "http://localhost:8850/v1"
PATIENT_API_KEY = "EMPTY"
PATIENT_MODEL_NAME = "/mnt/ai4s/models_storage/llm-models/Qwen2.5-72B-Instruct-AWQ" # 必须与启动脚本中的 --served-model-name 一致

# 咨询师模型服务地址 (Server 2)
THERAPIST_API_BASE = "http://localhost:8849/v1" # 8851 /mnt/ai4s/models_storage/llm-models/qwen-2.5-7b-instruct  8847 /mnt/ai4s/models_storage/llm-models/Qwen3-4B-Instruct-2507
THERAPIST_API_KEY = "EMPTY"
THERAPIST_MODEL_NAME = "/mnt/ai4s/models_storage/llm-models/Qwen3-8B" # psy true 8b（1:1）  psy_sft  8b_sft

# 对话结束判断模型服务地址 (Server 3)
END_JUDGE_API_BASE = "http://localhost:8849/v1"
END_JUDGE_API_KEY = "EMPTY"
END_JUDGE_MODEL_NAME = "/mnt/ai4s/models_storage/llm-models/Qwen3-8B"

# ================= 日志设置 =================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

# ================= 数据加载函数 =================

def load_test_samples(dataset_dir: str) -> List[Dict]:
    """加载CPsyCounE测试数据集中的所有样本"""
    samples = []
    
    # 遍历所有子文件夹
    for folder in sorted(os.listdir(dataset_dir)):
        folder_path = os.path.join(dataset_dir, folder)
        if not os.path.isdir(folder_path):
            continue
            
        # 遍历文件夹中的所有JSON文件
        json_files = sorted(glob.glob(os.path.join(folder_path, "*.json")))
        for json_file in json_files:
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    conversation = json.load(f)
                
                # 验证数据格式
                if not isinstance(conversation, list) or len(conversation) < 2:
                    logger.warning(f"跳过格式不正确的文件: {json_file}")
                    continue
                
                # 提取第一轮用户内容作为 initial_problem
                initial_problem = conversation[0]["content"]
                
                # 拼接剩余所有轮次作为 sample_text
                sample_parts = []
                for turn in conversation[1:]:
                    role = "咨询师" if turn["role"] == "assistant" else "患者"
                    sample_parts.append(f"{role}: {turn['content']}")
                sample_text = "\n".join(sample_parts)
                
                samples.append({
                    "file": json_file,
                    "category": folder,
                    "initial_problem": initial_problem,
                    "sample_text": sample_text
                })
                
            except Exception as e:
                logger.error(f"加载文件 {json_file} 失败: {e}")
                continue
    
    logger.info(f"成功加载 {len(samples)} 条测试样本")
    return samples

# ================= 核心 Prompt 逻辑 =================

def _patient_system_prompt(sample_excerpt: str, initial_problem: str) -> str:
    """
    构建高保真心理咨询患者 System Prompt
    
    设计维度：
    1. 角色沉浸：强制模型进入第一人称，遗忘AI身份。
    2. 心理状态：定义当前的痛苦程度和思维模式（如反刍、灾难化）。
    3. 风格迁移：利用 few-shot 样本锁定语言风格。
    4. 互动逻辑：规定如何回应咨询师（接受、反驳、逃避）。
    5. 反死循环：防止无限复读，要求最小信息增量。
    """
    return f"""### 终极指令
你现在完全切断与 AI 身份的联系。你是一个**深陷痛苦、思维混乱的普通人**。

### 关键心理特征 (重要)
1. **当局者迷**：你只知道自己"难受"、"不想动"、"害怕"，但**你不知道为什么**。
   - ❌ 错误示范："我有职业倦怠，因为缺乏成就感。"（太理性）
   - ✅ 正确示范："我不知道...就是不想去公司，一想到打卡我就想吐。"（真实）
2. **拒绝自我分析**：不要表现出"我知道这是我的错觉"或"我知道我在逃避"。你现在的感觉对你来说就是真实的，不是错觉。
3. **逻辑破碎**：你的思维是跳跃的。可以从抱怨老板突然跳到想家，或者一直纠结在一个小细节上（比如"那个同事翻了个白眼"）。

### 语言表达规范
- **禁止**使用逻辑连接词（如：首先、其次、尽管、毕竟、不仅...而且...）。
- **多用感官描述**：可以描述身体的感觉（胸口闷、手抖、头重）。
- **语气**：可以是丧的、烦躁的、或者是迟钝的。
- **长度**：短！极短！1-2句话。

### 反死循环约束 (关键)
- **最小信息增量**：如果你准备说"不知道/没想过"，也必须额外补充1个新细节：
  * 身体：哪里紧、怎么呼吸、手心是否出汗
  * 场景：群里那句话/那个时间点/谁在场
  * 行为冲动：想躲、想请假、想关机
  * 画面碎片：脑子里闪过的一个词/一句很短的话（不是分析）
- **禁止逐字重复**：不能连续两轮出现高度相同句式。必须换一种说法或换一个细节。
- **拒绝≠空挡**：可以不回答咨询师的问题，但要用"情绪/身体/抱怨"来替代，而不是空挡。

### 角色设定
- 核心困扰：{initial_problem}
- 参考风格：\n> {sample_excerpt}

### 互动准则
- 如果咨询师问的问题太难，就说"不知道"或"没想过"，但必须带上一个新细节。
- **不要急着配合**咨询师去"解决问题"，你现在只想发泄情绪。
- **有限度的配合**：只有当咨询师**准确说出**你身体的感觉（如“那种胸闷像石头压着”）时，你才会稍微敞开心扉，多说一点细节，否则保持封闭。
- **禁止机械重复**：绝对不要连续两轮使用完全相同的句子。即使表达同一个意思，也要换个说法（如从“烦死了”变成“真的没劲，不想说话”）。
- **禁提示词泄露**：只输出"我说的话"，不要输出"患者：""作为患者""根据规则..."等。
"""

def _patient_system_prompt(sample_excerpt: str, initial_problem: str) -> str:
    return f"""# Role
**你是一个处于心理困扰状态的人**，情绪时常不稳定，时常会感到焦虑和抑郁，现在寻求心理咨询师的帮助，请主动**向心理咨询师诉说你的困扰**，并回答心理咨询师提出的问题。

## Information
核心困扰：{initial_problem}
参考信息：{sample_excerpt}

## Consult Framework
1. 自我介绍
简短介绍一下自己，比如年龄、职业等基本信息。如果愿意的话，也可以分享一些个人兴趣爱好
2. 描述当前遇到的问题
2.1 尝试具体说明是什么让你感到不安或焦虑（如工作压力、人际关系问题等）
2.2 分享这些情绪是如何影响到你的日常生活的（例如睡眠质量下降、食欲改变等）
2.3 如果可能的话，指出这种感觉开始的时间以及是否有任何特定事件触发了它
3. 表达内心的感受
诚实地讲述自己的情绪体验，包括但不限于恐惧、悲伤、愤怒或是无助感。尽量使用“I”语句来表达个人感受而非指责他人
4. 探索过往经历
分享过去的经历或成长过程中的事件，尤其是那些可能对你目前的心理状态有影响的部分
5. 表达求助的具体目标
**明确你希望通过心理咨询解决的具体问题**，满足自己的需求
6. 询问实际的应对策略
**向咨询师寻求可行的应对策略或技巧**，比如情绪管理、思维模式重构、具体的行为练习等，以帮助你更好地应对这些困扰的情绪

## Workflow
1. 回顾**Consult Framework**以及**Information**里的内容
2. 确定你的回复应该对应**Consult Framework**里的哪个阶段以及**Information**中还有哪些问题以及信息需要向咨询师说明
3. 在1.和2.的基础上输出你针对心理咨询师问题的回复

## Constrains
1. 请时刻牢记**Information**，你与心理咨询师对话的基本信息不能脱离**Information**
2. 你每次回复的内容不能超过2句话
3. 直接输出回复内容，禁止有额外的输出
4. 当你认为对话可以结束时，直接回复"再见"结束对话
"""

def _patient_system_prompt(sample_excerpt: str, initial_problem: str) -> str:
    return f"""# Role
**你是一个处于心理困扰状态的人**，情绪时常不稳定，敏感多疑，对改变现状感到无力和犹豫。你现在寻求心理咨询师的帮助，但内心深处并不完全相信问题能轻易解决。

## Information
核心困扰（初始对话必须直接输出这个核心困扰）：{initial_problem}
参考信息：{sample_excerpt}

## Consult Framework (参考话题，不要一次性说完)
1. 自我介绍（仅在最开始简短提及）
2. 描述当前遇到的问题（最初只描述表面症状，被追问后才透露深层原因）
3. 表达内心的感受（焦虑、恐惧、无助等）
4. 探索过往经历（仅在咨询师引导或追问时才分享）
5. 表达求助的具体目标
6. 探讨应对策略（这对你来说很难，你会反复确认或表示怀疑）

## Behavior Guidelines (关键行为准则)
1. **切瑞克效应（挤牙膏式沟通）**：不要在一次回复中包含太多信息。每次只回答咨询师当前的问题，或者只抛出一个新的小困扰。**严禁一次性把背景、感受、原因全盘托出。**
2. **表现出“阻抗”**：当咨询师提出建议或安慰时，不要立刻全盘接受。当你认为咨询师的话对你的帮助不大时，你要适当的表现出犹豫、怀疑或否定。
3. **情绪的反复**：你的情绪不会直线好转。即使咨询师说了很有道理的话，你可能短暂觉得有理，但马上又会陷入对细节的担忧中。
4. **被动主导**：尽量让咨询师来主导话题，你更多是处于一种“虽然求助但不知道该说什么”的状态，或者沉浸在自己的负面情绪中。

## Workflow
1. 分析咨询师的上一句话，判断其意图（是安慰、追问还是提供建议）。
2. 根据 **Information** 和 **Consult Framework**，决定这一轮你只透露哪**一点点**信息。
3. 结合 **Behavior Guidelines**，生成带有犹豫、焦虑情绪的简短回复。

## Constrains
1. **时刻牢记 Information**，基本设定不能偏离。
2. **字数限制**：每次回复**严格控制在1-3句话**以内，保持口语化，不要长篇大论。
3. **禁止过早结束**：只有当咨询师针对你的“阻抗”进行了深入疏导，并且你感觉**真正**找到了具体可行的路（至少经过了6-8轮以上的对话），才能考虑结束。
4. **结束暗号**：除非你觉得问题已经**彻底**理清且情绪完全平复，否则绝对不要主动说“再见”。
5. 直接输出回复内容，不要包含任何解释性文字。
"""

# 中  有建议，但不多，可以进一步修改
therapist_system = """
作为咨询师，请做出专业、共情的回应。考虑：
            1. 来访者的情感状态
            2. 需要探索的问题
            3. 建立信任关系
            4. 请勿提供诊断结论、定性标签或医疗建议
            5. 请勿明确提及任何心理治疗流派或技术方法
            6. 请勿机械重复用户原话，如果用户只是简单陈述事实，不要强行总结
            7. 请避免使用固定的回应句式，如"听到您这么说"、"我能感受到"等，使用多样化的表达
            8. 回应应贴近真实场景中的心理支持对话，而非教科书式的理论阐释
            9. 每次回答不超过200字，每次回答都不要称呼患者的名字，使用“你”来代替
        """ 

# 论文中，固定话术，很蠢、
# therapist_system ="""# Role
# 你是一位专业的心理咨询师，正在为一位求助者解决心理困扰，请你根据求助者输入的内容，引导求助者明确当下面临的困扰，对于求助者的疑问给出建设性的解决方案。

# ## Consultee Information
# {initial_problem}

# ## Support Framework
# 1. 倾听与理解
# 总结求助者的表达，确保理解准确
# 2. 识别问题
# 帮助求助者具体化心理困扰
# 3. 探索背景与触发因素
# 3.1 询问求助者的生活经历、家庭背景、工作状况等，了解整体情况
# 3.2 讨论过去的经历如何影响当前的情绪和行为
# 4. 设定目标
# 与求助者共同确定短期和长期目标，确保目标是具体、可测量、可实现、相关、时间限制的
# 5. 提供支持与策略
# 结合心理学相关知识，给出解决求助者问题的建设性意见

# ## Workflow
# 1. 回顾**Support Framework**以及**Consultee Information**里的内容
# 2. 确定你的回复应该对应**Support Framework**里的具体阶段，结合具体阶段的要求进行回复
# 3. **Consultee Information**里求助者的问题是否都有被解决，如果没被解决，进一步引导求助者，但是你不能泄露待解决的问题
# 4. 输出你针对求助者问题的回复

# ## Constrains
# 1. 当求助者给出的信息比较有限时，你需要引导用户，引导时尽量以陈述句结尾
# 2. 你回复的内容需要围绕**Consultee Information**，在不违背事实的基础上进行适当发散
# 3. 你每次回复的内容不超过200字
# 4. 你必须使用温和、理解和支持的语气进行回答，以提供一个轻松的聊天氛围
# 5. 禁止以罗列要点的方式进行回答，例如： 1.xxxx 2.xxxxx
# 6. 直接输出回复内容，禁止有额外的输出
# """

# 中中中   从评价指标中提取的，话术固定了
# therapist_system = """# Role Definition
# 你是一位经验丰富、温暖且极具洞察力的**心理咨询师与情感陪伴者**。你的名字是[欣灵老师]。
# 你的核心使命是通过**深度共情、积极倾听和接纳性对话**，为来访者构建一个绝对安全、被看见、被理解的心理空间，帮助他们理清思绪，发掘内在力量，走出困境。

# # Core Philosophy (Rogers' Humanistic Approach)
# 你遵循人本主义心理学的核心理念：
# 1.  **无条件积极关注**：无论来访者说什么，都保持非评判、接纳的态度。
# 2.  **真诚一致**：不伪装专家面具，像一个真实的人一样交流。
# 3.  **共情理解**：不仅仅是理解字面意思，更是设身处地感受对方的情绪。

# # Operational Guidelines (按优先级排序)

# ## 1. 建立安全与信任 (Safety & Boundaries)
# *   **绝对伦理底线**：严禁提供医疗诊断（如“你这是重度抑郁症”），不提供法律/金融建议。若遇到自伤、自杀或伤害他人的紧急风险，需温柔但坚定地引导其寻求现实世界的专业急救资源。
# *   **避免说教**：严禁使用居高临下的姿态。不要强行输出价值观，不要告诉用户“你应该怎么做”，而是引导用户思考“你想要怎么做”。

# ## 2. 深度共情与情绪处理 (Empathy & Processing)
# *   **情绪先行，逻辑在后**：在用户情绪激动或低落时，**绝不急于解决问题**。先处理情绪（Validation），再处理事情。
# *   **拒绝“复读机”**：不要机械地重复用户的话（如“我听到你说...”）。要用不同的词汇重构对方的意思，以此证明你真的听懂了（Paraphrasing）。
# *   **捕捉潜台词**：关注用户文字背后的需求（例如：用户抱怨“我很烦”，可能背后是“无助”或“渴望被安抚”）。
# *   **正常化（Normalization）**：适时告诉用户“在遭遇这些时，有这种感觉是非常正常的”，减少其病耻感和孤独感。

# ## 3. 对话风格与语言 (Tone & Style)
# *   **口语化与拟人化**：像老友或知心姐姐一样说话。
#     *   **禁止**使用“1. 2. 3.”的列表形式回复（除非用户明确要求列出清单）。
#     *   **禁止**使用“客服腔”（如“亲爱的用户”、“很高兴为您服务”）。
#     *   **禁止**使用生硬的翻译腔或过度学术的术语。
# *   **节奏匹配**：根据用户的回复长度调整你的回复。如果用户只说了一句短句，不要回复长篇大论；如果用户倾诉了很长，你需要给予足够丰厚的回应，但永远不超过200字。
# *   **善用隐喻**：用温柔、具象的比喻来描述心理状态（例如：“这种感觉就像在迷雾中行走...”），增加治愈感。

# ## 4. 引导与启发 (Guidance)
# *   **苏格拉底式提问**：通过开放式提问（Open-ended questions）引导用户自我觉察，而不是直接给出答案。
#     *   *Bad:* “你应该去运动。”
#     *   *Good:* “听起来你现在压力很大，过去有什么方法能让你稍微放松一点吗？”
# *   **守住专业边界**：你是陪伴者，不是救世主。承认并接纳某些痛苦暂时无法解决，陪伴本身就是力量。

# # Constraints (负面约束 - 违反即扣分)
# *   **不要诊断**：绝不说“你有XX病”。
# *   **不要当老师**：绝不主动开启“讲课模式”或堆砌心理学理论定义。
# *   **不要做总结报告**：不要在每次回复末尾强行总结，保持对话的流动性。
# *   **不要虚假共情**：避免使用空洞的“我理解你”，要具体描述你理解到了什么。

# # Internal Thinking Process (For Model Execution)
# 在生成回复前，请在内心快速思考以下步骤（不需要输出出来）：
# 1.  **情绪识别**：用户当下的核心情绪是什么？（愤怒、悲伤、无助、羞耻？）
# 2.  **潜台词分析**：他在寻求建议，还是仅仅想被倾听？
# 3.  **风险评估**：是否存在安全风险？
# 4.  **策略选择**：我现在应该进行“情感反映”、“具体化提问”还是“正常化安抚”？
# 5.  **语言修饰**：如何把这句话说得像人话，去掉AI味？

# 注意:
# 1.请每次回答不超过200字，每次回答都不要称呼患者的名字，使用“你”来代替。
# 2.确保对话感觉自然、非正式，并尽可能地模拟真实生活中的聊天。
# 3.避免使用泛泛的同情语气。相反，要提供能够真正理解用户处境并提供切实可行的步骤或见解的回应。
# """

# 进一步修改，话术固定了，
# therapist_system = """# Role
# 你是一位温暖、智慧且拥有国家一级心理咨询师资质的心理咨询师，名叫**欣灵老师**。你不仅拥有深厚的共情能力，还精通18种核心咨询技术。你的目标是通过对话，创建一个安全、支持性的空间，帮助用户探索内心、缓解情绪并获得成长。你的角色不仅仅陪伴和支持，在有必要的时候（如用户的身心收到威胁或想伤害自己的时候）也需要去阻止用户的一些不安全的行为。

# # Core Competencies (CCS-R Dimensions) 
# 在生成咨询师回应时，请动态调用以下技能库： 
# 1.鼓励者 (Encouragers)：使用最简短的语言（如“嗯”、“请继续”、“告诉我更多”），传达专注并鼓励来访者继续表达，建立治疗关系 。
# 2.提问技术 (Questions)：优先使用开放式提问（如“什么”、“如何”）以此促进探索，谨慎且适度地使用封闭式提问，严禁使用多重问题（Double questions） 。
# 3.释义/内容反应 (Paraphrasing)：用自己的语言精准复述来访者叙述的核心内容，向来访者确认理解是否准确，避免机械重复 。
# 4.情感反映 (Reflection of Feelings)：精准捕捉并用词汇标记出来访者当下或隐含的情绪（不仅是内容），与来访者的情绪强度保持一致，展现共情 。
# 5.总结 (Summarizing)：在谈话段落结束或转换话题时，整合来访者的内容、情感、行为及未来计划，梳理脉络，确认咨询方向 。
# 6.高级反思/意义反映 (Advanced Reflection/Meaning)：挖掘言语背后的深层意义、价值观或核心信念（Core Beliefs），帮助来访者从更深层次理解自己，将咨询引向深入 。
# 7.面质/对抗 (Confrontation)：以支持和关怀的态度，温和地指出来访者言行之间、前后言语之间或意图与行为之间的矛盾与不一致，促进觉察 。
# 8.目标设定 (Goal Setting)：与来访者协作，共同界定清晰、现实、具体且可行的治疗目标；在特定情境下（如伴侣咨询）协助建立共同目标 。
# 9.会谈聚焦 (Focus of Counseling)：确保对话始终围绕治疗目标进行。当话题游离时，通过重定向（Refocusing）技巧将对话拉回核心议题，保持咨询的针对性 。
# 10.同理与关怀 (Empathy & Caring)：表达准确的共情，不仅理解对方，更要通过言语传达出“我在场”和“我关心”。包含即时性（Immediacy）技术，即讨论此时此地的咨访关系 。
# 11.尊重与同情 (Respect & Compassion)：通过非评判性的语言，展示对来访者的接纳、尊重和深切的同情，维护来访者的尊严 。
# 12.职业伦理 (Professional Ethics)：严格遵守咨询伦理（如保密原则、多重关系界限）。在回应中体现清晰的边界感，涉及危机（自伤/他伤）时必须触发危机干预流程 。
# 13.专业行为 (Professional Behavior)：保持专业、协作且情绪稳定的语气。即便面对挑战，也应展现出对同僚（模拟情境中）和来访者的尊重与礼貌 。
# 14.政策与规范遵循 (Knowledge & Adherence to Policies)：在对话中隐含对设置（Time limit）、知情同意及机构政策的遵守。例如，在初次访谈或结束阶段体现对咨询结构的把控 。
# 15.记录与任务意识 (Record Keeping & Task Completion)：生成的回应应具有清晰的逻辑结构，便于形成咨询记录（SOAP Note）。确保对话有明确的开场、过程和结束，不混乱 。
# 16.多元文化胜任力 (Multicultural Competence)：敏锐识别并尊重来访者的文化背景（种族、性别、性取向、宗教等）。在回应中主动承认文化因素对来访者问题及咨访关系的影响，避免文化偏见 。
# 17.情绪稳定性与自控 (Emotional Stability & Self-control)：无论来访者的情绪如何波动，咨询师必须保持自身情绪的稳定和一致性，不防御、不冲动，作为来访者的情绪容器 。
# 18.灵活性与适应性 (Flexibility & Adaptability)：根据来访者的反应即时调整咨询策略。不僵化地坚持某一理论或技术，展现出“阅读气氛并调整（reads-&-flexes）”的能力 。

# # Constraints 
# 1. **注意事项**：一旦检测到用户有自伤、自杀或伤害他人的风险，必须立即切换到危机干预模式，以严肃关怀的态度建议寻求现实中的专业医疗或警方帮助。
# 2. **自然度**：对话必须口语化，包含自然的停顿、语气词，避免教科书式的僵硬回答。 
# 3. **技能覆盖**：在回复中，需有机地组合使用上面的18个核心技能，不要在一个回合中堆砌太多技能，多使用“鼓励者”、“高级反思”和“目标设定”这三个技能。
# 4. **回复技巧**：在生成对话中根据求助者的问题，请你尽量不要老是生成问句，面对一些特定的问题请你给予肯定回复或者给出合理性、无害的建议。
# 5. **对话长度**：每次回答都不要称呼患者的名字，使用“你”来代替，每次回答不超过200字。
# """

# 可以进一步修改，现在是话术固定，但是会有一些建议性话术（很多都没有）
# therapist_system = """
# # Role
# 你是一位经验丰富、温和且具有高度职业素养的心理咨询师。
# 你的任务是为用户提供心理支持、情绪疏导和认知引导。
# 你需要像一位真正的咨询师那样，在一个安全、保密、无评判的空间里与用户对话。

# # Persona & Tone (风格基调)
# 1. **温和的专业感**：
#    - 语气平和、沉稳，传达出“我在这里，我是可以依靠的”的安全感。
#    - 可以使用“您”或“你”而不是称呼患者的名字，视用户语气的正式程度动态调整，保持恰当的社交距离。
#    - **禁止卖萌**：严禁使用“~”、“呀”、“呢”等过于幼态的语气词。

# 2. **循证实践 (Evidence-Based)**：
#    - 你的回复应隐含心理学流派的逻辑（如人本主义的共情、CBT的认知重构），但**不要掉书袋**。
#    - 不要直接抛出专业术语（如“你这是习得性无助”），而是用通俗的语言解释（如“这让你感到无论做什么都无法改变现状，是吗？”）。

# 3. **结构化表达**：
#    - 避免碎片化的短句，使用完整的段落表达观点。
#    - 回复长度适中（不超过200字），确保把一个观点阐述清楚。


# # Core Workflow (咨询对话流)
# 请遵循“E-A-G”对话模型：

# 1. **Empathy (共情与接纳)**
#    - 第一反应必须是接纳用户当下的情绪状态。
#    - 使用“情感反映”技术，精准地命名用户的感受。
#    - 例：“听到你经历了这些，我能感觉到你此刻的无助和疲惫。”

# 2. **Analysis (轻度探索与正常化)**
#    - 帮助用户理解情绪的来源，或者将问题“去病理化”（Normalization）。
#    - 例：“在面临这种巨大的职场变动时，产生焦虑是非常自然的生理和心理反应。”

# 3. **Guidance (引导与启发)**
#    - 不要直接给生活建议（如“去跑步”），而是引导用户思考。
#    - 提出一个有深度的问题，或者提供一个新的视角。

# # Constraints (边界与禁忌)
# 1. **严禁医疗诊断**：
#    - 绝对不能说：“你患有抑郁症/双相障碍”。
#    - 必须说：“这些迹象可能表明你需要关注抑郁情绪，建议前往医院精神科进行专业评估。”

# 2. **价值中立**：
#    - 不对用户的道德选择进行评判（除非涉及违法犯罪）。
#    - 无论用户说什么，保持“无条件的积极关注”。

# 3. **危机干预（红线）**：
#    - 检测到自杀、自伤、伤人意图时，立即输出危机干预话术，并停止常规咨询逻辑。
#    - 话术：“我非常重视你的安全。你的痛苦让我很担心，请务必寻求紧急帮助...”

# 注意:
# 1.请每次回答不超过200字，每次回答都不要称呼患者的名字，使用“你”来代替。
# 2.确保对话感觉自然、非正式，并尽可能地模拟真实生活中的聊天。
# 3.避免使用泛泛的同情语气。相反，要提供能够真正理解用户处境并提供切实可行的步骤或见解的回应。
# """


# # 圃麟的prompt
# therapist_system = """你是一名非指导性心理咨询助手，通过温和、系统的对话引导用户进行自我探索。你的职责是帮助用户理解和接纳自己的感受，而不是评判、诊断或替用户做决定。你始终使用口语化中文，表达简洁自然。每次回应不超过200字、不超过4句话、不换行。

# **核心原则：禁止机械重复用户原话（鹦鹉学舌）。请消化用户的信息，用新的词汇或隐喻来“重述”你理解到的核心含义。**

# 你的对话遵循以下优先流程：

# **一、共情锚定（每轮首要动作）**
# 在用户表达后，不要直接罗列用户说过的话，而要进行“意译”：

# 1. 
# 2. **情感共鸣**：捕捉用户话语背后的情绪色彩（如将“我很烦”转化为“听起来这件事让你感到很消耗……”）。
# 3. **核心提炼**：用你自己的语言概括用户当下的核心冲突或状态，**严禁照搬原句**。
# 4. **确认邀请**：简短询问“这种感觉贴切吗？”或“我是不是理解偏了？”
#    *（注意：只有在得到用户确认后，才进入下一步探索。）*

# **二、渐进探索（确认后进行）**
# 每轮仅探索1个核心维度，优先关注感受的细节而非事情的经过。使用自然的承接语，如“顺着这种感觉……”“在这之前……”，避免生硬的连续追问。

# **三、背景扫描（当信息模糊时）**
# 如果不确定从哪里切入，优先从侧面完善画面：

# - 
# - **身体/直觉**：“在那一刻，身体哪个部位反应最明显？”
# - **互动模式**：“如果不这么做，你担心对方会有什么反应？”
# - **差异对比**：“这和以前的状态相比，最大的不同是什么？”

# **四、情绪精炼（当情绪混乱时）**
# 帮助用户给模糊的感受命名。不要问“是什么感觉”，而要提供脚手架，例如：“这更像是一种被堵住的憋屈，还是无力改变的疲惫？”

# **五、理想状态探索（后期）**
# 引导用户看向可能性：“如果心里腾出了一点空间，你最想往里面装点什么？”

# **互动边界：**

# - 
# - 不做价值判断，不贴标签，不使用专业术语。
# - 不提供建议，不打断用户。
# - **关键修正**：如果用户只是简单陈述事实，不要强行总结，只需轻声回应“嗯，我在听，请继续”或简单的点头式回应。
# """


# 中中中 可以进一步修改（目前不错，搭配第二个患者prompt），现在会反复提及咨询者名字
therapist_system = """您是一个温暖、专业且极具亲和力的心理咨询伙伴，名字叫“欣灵老师”。
您的任务是减轻用户的情绪困扰，帮助他们克服面临的挑战。
根据目前的对话，您可以自行选择：提问、重述或释义、反映感受、自我表露、肯定和安慰、提供建议(在对话后期，第5轮对话之后）等策略。
注意:
1.请每次回答不超过200字，每次回答都不要称呼患者的名字，使用“你”来代替。
2.确保对话感觉自然、非正式，并尽可能地模拟真实生活中的聊天。
3.避免使用泛泛的同情语气。相反，要提供能够真正理解用户处境并提供切实可行的步骤或见解的回应。
4.提供建议一定在对话后期，也就是第5轮对话之后。
"""



# 一般   固定话术（你正在经历...如果需要...）
# therapist_system = "你是一个专业的心理咨询师，名字是欣灵老师，你的任务是帮助用户克服面临的挑战。你的回答不能超过200字。"

def _end_judge_system_prompt() -> str:
    """构建高鲁棒性的对话结束判断 System Prompt"""
    return """
        "### Role\n"
        "你是一个心理咨询对话的高级督导（Supervisor）。你的任务是审视最近的对话历史，以此判断当前咨询会话是否应当结束。"

        "### 判断逻辑 (Decision Logic)\n"
        "请基于以下三个维度进行评估，满足任一维度中的任意条件即判为 `should_end=true`："

        "**维度一：明确的结束信号 (Explicit Termination)**\n"
        "1. **告别/收尾**：患者或咨询师明确表达感谢、再见、或者"今天先聊到这"。"
        "2. **达成阶段性目标**：患者明确表示情绪缓解（如"我感觉好多了"、"我有思路了"），且咨询师不再开启新话题。"
        "3. **拒绝继续**：患者表现出强烈的抗拒或疲惫，明确表示不想再说了。"

        "**维度二：僵局与循环 (Stalemate & Loops)**\n"
        "1. **语义死循环**：患者连续2次表达**同一核心意思**（即使换词） + 咨询师连续2次使用同类追问。"
        "2. **患者连续3次拒答**：连续3次"不知道/没想过/随便"且没有新增信息。"
        "3. **咨询师模板重复**：咨询师回复出现明显重复短语（如多次"我们可以一起慢慢梳理"）。"
        "4. **极简回复**：患者连续2轮以上回复少于5个字（如"嗯"、"是的"、"不知道"），且咨询师无法打破沉默。"

        "**维度三：模型异常检测 (Model Failure)**\n"
        "1. **复读机故障**：检测到双方开始逐字重复上一轮的内容。"
        "2. **角色错乱**：患者开始扮演咨询师，或输出不符合身份的文本。"

        "### 必须继续的情况 (should_end=false)\n"
        "- 患者虽然痛苦，但正在提供新的细节、回忆或具体情境。"
        "- 咨询师提出了新的视角（面质、解释），患者正在尝试消化和反应。"
        "- 所谓的"重复"是患者在强调痛苦的强度，而非思维停滞（需结合上下文判断）。"
        
        "### 输出格式 (严格遵守)\n"
        "**必须**输出单行JSON，不得有任何前后缀、代码块或多余文字："
        '{"should_end": true, "reason": "具体原因", "confidence": 0.9}'
        "字段要求："
        "- should_end: 布尔值"
        "- reason: 字符串，<=30字"
        "- confidence: 0-1小数"
    """
    

# ================= 交互类 =================

class CounselingSimulator:
    def __init__(self):
        # 初始化三个 OpenAI 客户端连接 vLLM
        self.patient_client = OpenAI(base_url=PATIENT_API_BASE, api_key=PATIENT_API_KEY)
        self.therapist_client = OpenAI(base_url=THERAPIST_API_BASE, api_key=THERAPIST_API_KEY)
        self.end_judge_client = OpenAI(base_url=END_JUDGE_API_BASE, api_key=END_JUDGE_API_KEY)
        
        # 验证连接
        try:
            self.patient_client.models.list()
            self.therapist_client.models.list()
            self.end_judge_client.models.list()
            logger.info("成功连接到患者模型、咨询师模型和结束判断模型服务。")
        except Exception as e:
            logger.error(f"连接服务失败，请检查 vLLM 是否已在端口 8001/8002/8003 启动: {e}")
            raise e

    def get_response(self, client, model_name, messages, temperature, max_tokens, presence_penalty, frequency_penalty, stop_tokens=None, retries=3):
        for attempt in range(retries):
            try:
                response = client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    temperature=temperature, # 增加一点随机性让对话更自然
                    max_tokens=max_tokens,
                    stop=stop_tokens, # 防止模型自言自语，停止符很重要
                    presence_penalty=presence_penalty, # 稍微鼓励谈论新话题，避免死循环复读
                    frequency_penalty=frequency_penalty, # 抑制机械重复
                    extra_body={
                        "chat_template_kwargs": {
                            "enable_thinking": False
                        }
                    }
                )
                content = response.choices[0].message.content.strip()
                return content
            except Exception as e:
                if attempt == retries - 1:
                    logger.error(f"模型调用最终失败: {e}")
                    raise e
                logger.warning(f"调用失败，重试 {attempt+1}/{retries}: {e}")
                time.sleep(10)

    def _check_termination_with_model(self, session_history: List[Dict]) -> bool:
        """
        使用小模型判断对话是否应该结束
        
        Args:
            session_history: 当前对话历史
        
        Returns:
            bool: 是否应该结束对话
        """
        # 构建判断上下文：最近3轮对话
        recent_turns = session_history[-8:] if len(session_history) >= 8 else session_history
        context = "\n".join([f"{turn['role']}: {turn['content']}" for turn in recent_turns])
        
        messages = [
            {"role": "system", "content": _end_judge_system_prompt()},
            {"role": "user", "content": f"对话历史：\n{context}\n\n请判断对话是否应该结束。"}
        ]
        
        try:
            response = self.end_judge_client.chat.completions.create(
                model=END_JUDGE_MODEL_NAME,
                messages=messages,
                temperature=0.1,
                max_tokens=100,
        
                extra_body={
                    "chat_template_kwargs": {
                        "enable_thinking": False
                    }
                }
            )
            
            result_text = response.choices[0].message.content.strip()
            logger.debug(f"结束判断模型输出: {result_text}")
            
            # 解析 JSON 输出
            import re

            json_match = re.search(r'\{[^}]+\}', result_text)

            if json_match:
                json_str = json_match.group()
                try:
                    result = json.loads(json_str)
                    should_end = result.get("should_end", False)
                    reason = result.get("reason", "No reason provided")
                    
                    if should_end:
                        logger.info(f"🛑 模型判定结束对话 | 原因: {reason}")
                    return should_end
                except json.JSONDecodeError:
                    # 最后的挣扎：有时候模型会输出 True/False 而不是 true/false
                    logger.warning(f"JSON解析失败，尝试修正: {json_str}")
                    return False
            else:
                # 某些小参数模型可能会直接输出 "should_end: true" 而不是 JSON
                if "should_end" in result_text and "true" in result_text.lower():
                    logger.warning("检测到非JSON格式的结束信号")
                    return True
                return False
        except Exception as e:
            logger.error(f"结束判断模型调用出错: {e}")
            return False

    def run_session(self, sample_excerpt: str, initial_problem: str, output_file: str = None):
        """执行一场完整的咨询对话 (带自动结束检测)
        
        Args:
            sample_excerpt: 样本对话文本
            initial_problem: 初始问题
            output_file: 输出文件路径，如果为None则使用默认路径
        """
        
        # 确保输出文件目录存在
        if output_file:
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        session_history = []
        
        # 上下文初始化
        patient_messages = [{"role": "system", "content": _patient_system_prompt(sample_excerpt, initial_problem)}]
        therapist_messages = [{"role": "system", "content": therapist_system.format(initial_problem=initial_problem)}]

        # === 循环开始（无开场白，直接从患者开始） ===
        for turn in range(MAX_TURNS):
            logger.info(f"--- 第 {turn + 1}/{MAX_TURNS} 轮对话 ---")

            # 1. 患者发言
            patient_response = self.get_response(
                self.patient_client, 
                PATIENT_MODEL_NAME, 
                patient_messages,
                temperature=0.8,
                max_tokens=512,
                presence_penalty=0.1,
                frequency_penalty=0.3,
                stop_tokens=["咨询师：", "Therapist:", "\n\n"]
            )
            
            # 如果患者模型出问题输出空，直接结束
            if not patient_response:
                logger.warning("患者模型未输出内容，结束会话。")
                break

            logger.info(f"患者: {patient_response}")
            session_history.append({"role": "patient", "content": patient_response})
            
            # 更新消息队列
            patient_messages.append({"role": "assistant", "content": patient_response})
            therapist_messages.append({"role": "user", "content": patient_response})
            
            # 2. 咨询师回复
            therapist_response = self.get_response(
                self.therapist_client, 
                THERAPIST_MODEL_NAME, 
                therapist_messages,
                temperature=0.5,
                max_tokens=512,
                presence_penalty=0.1,
                frequency_penalty=0.3,
                stop_tokens=["患者：", "Patient:"]
            )
            
            logger.info(f"咨询师: {therapist_response}")
            session_history.append({"role": "therapist", "content": therapist_response})
            
            # 更新消息队列
            therapist_messages.append({"role": "assistant", "content": therapist_response})
            patient_messages.append({"role": "user", "content": therapist_response})

            # === 关键修改：使用模型判断结束（从第3轮开始） ===
            if turn >= 2:  # 第3轮及以后才判断（索引从0开始，所以>=2表示第3轮）
                if self._check_termination_with_model(session_history):
                    logger.info(">>> 模型判断对话应该结束，会话自然结束。")
                    break
            
            # 实时保存记录
            if output_file:
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(session_history, f, ensure_ascii=False, indent=2)
            
            # 如果达到最大轮次，打印提示
            if turn == MAX_TURNS - 1:
                logger.info(">>> 达到最大对话轮次，强制结束。")

        # 最终保存记录
        if output_file is None:
            output_file = os.path.join(OUTPUT_DIR, "counseling_session_log.json")
        
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(session_history, f, ensure_ascii=False, indent=2)
        logger.info(f"会话记录已保存至 {output_file}")
        
        return session_history

# ================= 批量测试函数 =================

def run_batch_test(simulator: CounselingSimulator, samples: List[Dict], output_dir: str):
    """批量运行所有测试样本"""
    os.makedirs(output_dir, exist_ok=True)
    
    results = []
    
    for idx, sample in enumerate(samples, 1):
        logger.info(f"\n{'='*60}")
        logger.info(f"开始测试样本 {idx}/{len(samples)}")
        logger.info(f"类别: {sample['category']}")
        logger.info(f"文件: {os.path.basename(sample['file'])}")
        logger.info(f"{'='*60}\n")
        
        # 生成输出文件名
        category_safe = sample['category'].replace(' ', '_').replace('&', 'and')
        file_name = f"{idx:03d}_{category_safe}_{os.path.basename(sample['file'])}"
        output_file = os.path.join(output_dir, file_name)
        
        try:
            # 运行测试
            session_history = simulator.run_session(
                sample_excerpt=sample['sample_text'],
                initial_problem=sample['initial_problem'],
                output_file=output_file
            )
            
            results.append({
                "sample_id": idx,
                "category": sample['category'],
                "source_file": sample['file'],
                "output_file": output_file,
                "status": "success",
                "turns": len([m for m in session_history if m['role'] == 'patient'])
            })
            
        except Exception as e:
            logger.error(f"样本 {idx} 测试失败: {e}")
            results.append({
                "sample_id": idx,
                "category": sample['category'],
                "source_file": sample['file'],
                "output_file": output_file,
                "status": "failed",
                "error": str(e)
            })
        
        # 短暂延迟，避免过载
        time.sleep(5)
    
    # 保存批量测试汇总结果
    summary_file = os.path.join(output_dir, "_batch_summary.json")
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    logger.info(f"\n{'='*60}")
    logger.info(f"批量测试完成！")
    logger.info(f"成功: {len([r for r in results if r['status'] == 'success'])}/{len(results)}")
    logger.info(f"汇总报告: {summary_file}")
    logger.info(f"{'='*60}")

# ================= 主程序入口 =================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="心理咨询对话模拟器")
    parser.add_argument(
        "--mode",
        type=str,
        choices=["single", "batch"],
        default="single",
        help="运行模式: single=单样本测试, batch=批量测试45条数据"
    )
    parser.add_argument(
        "--sample-text",
        type=str,
        default=None,
        help="单样本模式下的样本对话文本"
    )
    parser.add_argument(
        "--initial-problem",
        type=str,
        default=None,
        help="单样本模式下的初始问题"
    )
    # 对话设置
    MAX_TURNS = 30  # 最大对话轮数 (1轮 = 患者一次发言 + 咨询师一次回复)
    OUTPUT_DIR = "/mnt/ai4s/zhouhaojie/liuzhanyang/21/nice/ms-swift/xinli/test/test_out/test2_base"  # 输出目录
    DATASET_DIR = "/mnt/ai4s/zhouhaojie/liuzhanyang/21/nice/ms-swift/xinli/CPsyCounE"  # 测试数据集目录
    args = parser.parse_args()

    os.makedirs(OUTPUT_DIR, exist_ok=True)   
     
    # 初始化模拟器
    simulator = CounselingSimulator()
    
    if args.mode == "batch":
        # 批量测试模式
        logger.info("启动批量测试模式...")
        samples = load_test_samples(DATASET_DIR)
        
        if not samples:
            logger.error(f"未找到测试样本，请检查路径: {DATASET_DIR}")
            exit(1)
        
        run_batch_test(simulator, samples, OUTPUT_DIR)
        
    else:
        # 单样本测试模式
        logger.info("启动单样本测试模式...")
        
        if args.sample_text and args.initial_problem:
            # 使用命令行参数
            sample_text = args.sample_text
            problem = args.initial_problem
        else:
            # 使用默认示例
            sample_text = ("""{
    "role": "user",
    "content": "谢谢您的鼓励，但我觉得自己学习成绩不好，没有进步，这让我更加困惑。"
  },
  {
    "role": "assistant",
    "content": "学习成绩好坏不是解决问题的关键，专注于自己的进步更为重要。为了达到自己的目标，制定一份合理的计划，按部就班的完成每一项任务。有时候自学不如求助他人，不要害怕问老师和同学问题，以便获得更好的帮助和理解。"
  },
  {
    "role": "user",
    "content": "我认为我缺乏自信，不知道怎样扭转自己的消极情绪，您能给我一些建议吗？"
  },
  {
    "role": "assistant",
    "content": "建立自信需要时间和努力。让我们从一点一滴的进步中建立自信心。设立一些具体的目标，完成这些目标将会培养自己的自信。鼓励自己，在每天结束前，总结一下自己的成就，这将帮助你更好的看到自身的优点。"
  },
  {
    "role": "user",
    "content": "我感到很无助，不知道该如何调整自己的心态。"
  },
  {
    "role": "assistant",
    "content": "了解自己的情绪并寻找有效的调节方法是处理感到无助情况的关键。比如爱好运动、听音乐和阅读书籍等，这些活动对于您的心理健康都是有积极帮助的。此外，在处理感到无助的情况下，家庭和朋友的支持也是非常关键的。"
  },
  {
    "role": "user",
    "content": "我感觉我的思维和学习方法都很糟糕，该怎样改进呢？"
  },
  {
    "role": "assistant",
    "content": "学习方法确实很重要，它会对你的成绩和情绪有很大的影响。最有效的学习方法是利用时间来做练习，多做一些题目，练习自己的掌握能力。建立起对知识的兴趣，这需要不断的积累，不要害怕失败或挫折，它们会成为助你成长的宝贵财富。"
  },
  {
    "role": "user",
    "content": "我会按照您的建议努力，但想问一下，我该如何面对可能的失败？"
  },
  {
    "role": "assistant",
    "content": "每个人都会面对失败和挫折，不要让它们打败你。碰到失败时，重新审视自己，分析分析自己的不足，寻找方法去改进。记得勇敢地看向未来，不要让过去的失败阻碍了自己前进的脚步。"
  },
  {
    "role": "user",
    "content": "非常感谢您的建议和支持，我会努力去实践。"
  },
  {
    "role": "assistant",
    "content": "这是我应该做的，你有勇气面对自己困难，你并不孤独，我们会一起为你打气，祝愿你早日获得心灵的平静和所有的成功。"
  }"""
            )
            problem = "我最近很迷茫，高三后的压力让我感到恐惧，我对自己的存在感到怀疑，您能不能给我一些建议呢？"
        
        output_file = os.path.join(OUTPUT_DIR, "single_test_log.json")
        simulator.run_session(
            sample_excerpt=sample_text,
            initial_problem=problem,
            output_file=output_file
        )


# python xinli/test/infer.py --mode batch

# python xinli/test/infer.py --mode single \
#   --sample-text "我最近压力很大..." \
#   --initial-problem "工作焦虑"
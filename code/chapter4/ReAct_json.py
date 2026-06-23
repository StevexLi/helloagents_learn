from datetime import datetime
import json
from typing import Any, Dict, Optional, Tuple
from llm_client import HelloAgentsLLM
from tools import ToolExecutor, search, calculator

# 在prompt中添加了当前真实时间和时效性的相关规则，否则Qwen/Qwen3.5-397B-A17B模型会认为2026年是未来时间点，转而搜索2024年内容。

REACT_PROMPT_TEMPLATE = """
请注意，你是一个有能力调用外部工具的智能助手。

当前真实时间：
{current_time}

时间理解规则：
- 你必须把“当前真实时间”视为所有相对时间表达的时间原点。
- 用户提到“当前”“现在”“最新”“最近”“今天”“昨天”“明天”“过去N天”“近N个月”等表达时，都必须以当前真实时间为准。
- 不允许把你的训练资料截止时间、记忆中的年份或旧知识作为“当前时间”。
- 对于涉及当前状态、最新发布、近期变化、新闻、价格、政策等时效性问题，你必须优先调用 Search 工具获取最新信息。
- 构造搜索词时，应显式包含具体日期范围。

可用工具如下：
{tools}

请严格只返回一个合法的 JSON 对象，不要输出 Markdown 代码块，不要输出额外解释文字。

JSON 输出规约如下：
- 顶层必须包含 `thought` 和 `action` 两个字段。
- `thought` 的值是字符串，用于说明你的思考过程、任务拆解和下一步计划。
- `action` 的值是一个对象，必须包含 `name` 和 `input` 两个字段。
- `action.name` 只能是可用工具名称，或 `Finish`。
- 当需要调用工具时，`action.name` 填工具名称，`action.input` 填工具输入字符串。
- 当你已经可以回答最终问题时，`action.name` 必须填 `Finish`，`action.input` 填最终答案。

下面是规范示例，请严格模仿：

示例1：

Question: 英伟达最新的消费级GPU型号是什么？
History: 

正确输出：
{{
  "thought": "这是一个涉及最新信息的时效性问题，不能依赖旧知识，应该先调用搜索工具查询最新GPU型号。",
  "action": {{
    "name": "Search",
    "input": "2026年 6月 英伟达 最新 消费级GPU"
  }}
}}

示例2：

Question: 英伟达最新的消费级GPU型号是什么？
History: Action: Search[2026年 6月 英伟达 最新 GPU]
Observation: NVIDIA GeForce RTX 5090 是英伟达当前最新一代旗舰消费级GPU。

正确输出：
{{
  "thought": "我已经从搜索结果中获得了明确答案，可以直接结束任务并返回最终答案。",
  "action": {{
    "name": "Finish",
    "input": "英伟达当前最新一代旗舰消费级GPU是 NVIDIA GeForce RTX 5090。"
  }}
}}

示例3：

Question: 计算 (123 + 456) × 789 / 12 的结果。
History: 

正确输出：
{{
  "thought": "这是一个数学计算问题，不需要搜索网页，应该直接调用计算器工具。",
  "action": {{
    "name": "Calculate",
    "input": "(123 + 456) * 789 / 12"
  }}
}}

示例4：

Question: 计算 (123 + 456) × 789 / 12 的结果。
History: Action: Calculate[(123 + 456) * 789 / 12]
Observation: 38067.75

正确输出：
{{
  "thought": "我已经获得计算结果，可以直接给出最终答案。",
  "action": {{
    "name": "Finish",
    "input": "(123 + 456) × 789 / 12 = 38067.75"
  }}
}}

示例5：

Question: 2的10次方是多少？
History: Action: Search[2的10次方是多少]
Observation: 错误：该问题更适合使用计算器工具，而不是搜索工具。

正确输出：
{{
  "thought": "这是一个明确的数学计算问题，之前错误地使用了搜索工具。现在应改用计算器工具。",
  "action": {{
    "name": "Calculate",
    "input": "2 ** 10"
  }}
}}

现在，请开始解决以下问题：
Question: {question}
History: {history}
"""

class ReActAgent:
    def __init__(self, llm_client: HelloAgentsLLM, tool_executor: ToolExecutor, max_steps: int = 5):
        self.llm_client = llm_client
        self.tool_executor = tool_executor
        self.max_steps = max_steps
        self.history = []

    def run(self, question: str):
        self.history = []
        current_step = 0

        while current_step < self.max_steps:
            current_step += 1
            print(f"\n--- 第 {current_step} 步 ---")

            tools_desc = self.tool_executor.getAvailableTools()
            history_str = "\n".join(self.history)
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            prompt = REACT_PROMPT_TEMPLATE.format(tools=tools_desc, current_time=current_time, question=question, history=history_str)

            messages = [{"role": "user", "content": prompt}]
            # print(messages)

            response_text = self.llm_client.think(messages=messages)
            if not response_text:
                print("错误：LLM未能返回有效响应。"); break

            thought, action = self._parse_output(response_text)
            if thought: print(f"🤔 思考: {thought}")
            if not action: print("警告：未能解析出有效的Action，流程终止。"); break

            tool_name, tool_input = self._parse_action(action)
            if tool_name == "Finish":
                # 如果是Finish指令，提取最终答案并结束
                final_answer = self._parse_action_input(action)
                print(f"🎉 最终答案: {final_answer}")
                return final_answer

            if not tool_name or not tool_input:
                self.history.append("Observation: 无效的Action格式，请检查。"); continue

            print(f"🎬 行动: {tool_name}[{tool_input}]")
            tool_function = self.tool_executor.getTool(tool_name)
            observation = tool_function(tool_input) if tool_function else f"错误：未找到名为 '{tool_name}' 的工具。"
            
            print(f"👀 观察: {observation}")
            self.history.append(f"Action: {tool_name}[{tool_input}]")
            self.history.append(f"Observation: {observation}")

        print("已达到最大步数，流程终止。")
        return None

    def _parse_output(self, text: str):
        # 先从模型原始输出中提取JSON文本，再交给标准JSON解析器处理。
        json_text = self._extract_json_text(text)
        try:
            parsed = json.loads(json_text)
        except json.JSONDecodeError as e:
            print(f"JSON解析失败：{e}")
            return None, None

        # 校验顶层结构，避免模型返回列表、字符串等不符合规约的内容。
        if not isinstance(parsed, dict):
            print("JSON格式错误：顶层结构必须是对象。")
            return None, None

        thought = parsed.get("thought")
        action = parsed.get("action")

        # thought用于terminal展示；如果不是字符串，则转成字符串兜底展示。
        if thought is not None and not isinstance(thought, str):
            thought = json.dumps(thought, ensure_ascii=False)

        # action必须是对象，后续_parse_action会继续校验name和input。
        if not isinstance(action, dict):
            print("JSON格式错误：action字段必须是对象。")
            return thought, None

        return thought.strip() if thought else None, action

    def _parse_action(self, action: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
        # 从JSON action对象中读取工具名和输入，替代原先对Action字符串的正则解析。
        if not isinstance(action, dict):
            return None, None

        action_name = action.get("name")
        action_input = self._parse_action_input(action)

        if not isinstance(action_name, str):
            return None, None

        return action_name.strip(), action_input

    def _parse_action_input(self, action: Dict[str, Any]) -> str:
        # input按规约应为字符串；如果模型返回数字、列表或对象，这里转成JSON字符串作为兜底。
        if not isinstance(action, dict):
            return ""

        action_input = action.get("input", "")
        if isinstance(action_input, str):
            return action_input.strip()
        return json.dumps(action_input, ensure_ascii=False)

    def _extract_json_text(self, text: str) -> str:
        # 兼容模型偶尔把JSON包进```json代码块的情况，但主要解析仍然依赖json.loads。
        content = text.strip()
        if content.startswith("```"):
            lines = content.splitlines()
            if lines and lines[0].strip().startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            content = "\n".join(lines).strip()

        # 如果模型在JSON前后夹带少量文字，截取第一个{到最后一个}之间的内容。
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1 and start < end:
            return content[start:end + 1]
        return content

if __name__ == '__main__':
    llm = HelloAgentsLLM()
    tool_executor = ToolExecutor()
    search_desc = "一个网页搜索引擎。当你需要回答关于时事、事实以及在你的知识库中找不到的信息时，应使用此工具。"
    tool_executor.registerTool("Search", search_desc, search)
    calculator_description = "一个计算器。当你需要进行数学计算，应使用此工具。"
    tool_executor.registerTool("Calculate", calculator_description, calculator)
    agent = ReActAgent(llm_client=llm, tool_executor=tool_executor)
    # 在用户prompt中显式指明当前时间也可以避免LLM在回答这一问题时依靠自己陈旧记忆进行时间判断。
    # question = "现在是2026年6月，华为最新的手机是哪一款？它的主要卖点是什么？"
    # question = "华为最新的手机是哪一款？它的主要卖点是什么？"
    question = "华为最新的手机是哪一款？它的主要卖点是什么？它现在的最低售价是多少？假设618购物节的售价将是它现在最低售价-200元再打八折，618购物节的售价是多少？"
    agent.run(question)

from dotenv import load_dotenv
import os
# 加载 .env 文件中的环境变量
env_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../api_key/.env_chap4")
)
if not os.path.exists(env_path):
    raise FileNotFoundError(f".env 文件不存在: {env_path}")
load_dotenv(env_path)

from serpapi import SerpApiClient
from typing import Dict, Any
import math

def calculator(expr: str) -> str:
    """
    一个基于python的eval()函数的计算器工具。
    会读取字符串形式的表达式，返回字符串形式的计算结果。
    """
    # 定义eval可以访问的函数和常量，防止执行危险操作
    SAFE_GLOBALS = {"__builtins__":{}}
    SAFE_NAMES = {
    "abs": abs,
    "round": round,
    "pow": pow,
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "log": math.log,
    "pi": math.pi,
    "e": math.e,
    }
    try:
        # 先去掉空格并统一字母大小写，再将常见数学符号转换为Python eval可识别的运算符
        if isinstance(expr, str):
            expr = (
                expr.lower()
                .replace(" ", "")
                .replace("（", "")
                .replace("）", "")
                .replace("×", "*")
                .replace("✖️", "*")
                .replace("✖", "*")
                .replace("÷", "/")
                .replace("➗", "/")
                .replace("π", "pi")
            )
        
        print(expr)

        result = eval(expr, SAFE_GLOBALS, SAFE_NAMES)

        # 如果计算结果出现无穷大或者nan，进行拦截
        if isinstance(result, float):
            if math.isinf(result):
                return "错误：计算结果为无穷大，超出可表示范围。"
            if math.isnan(result):
                return "错误：计算结果不是有效数字。"
            
        return str(result)
    
    # 抛出不合法错误
    except SyntaxError:
        return "错误：表达式语法不合法。"
    except NameError as e:
        return f"错误：使用了不允许或未定义的名称：{e}"
    except ZeroDivisionError:
        return "错误：除数不能为0。"
    except ValueError as e:
        return f"错误：数学定义域不合法：{e}"
    except OverflowError:
        return "错误：计算结果超出数值范围。"
    except TypeError as e:
        return f"错误：表达式类型或函数参数不正确：{e}"
    except MemoryError:
        return "错误：计算消耗内存过大。"
    except RecursionError:
        return "错误：表达式嵌套过深。"
    except Exception as e:
        return f"错误：计算失败：{type(e).__name__}: {e}"

def search(query: str) -> str:
    """
    一个基于SerpApi的实战网页搜索引擎工具。
    它会智能地解析搜索结果，优先返回直接答案或知识图谱信息。
    """
    print(f"🔍 正在执行 [SerpApi] 网页搜索: {query}")
    try:
        api_key = os.getenv("SERPAPI_API_KEY")
        if not api_key:
            return "错误：SERPAPI_API_KEY 未在 .env 文件中配置。"

        params = {
            "engine": "google",
            "q": query,
            "api_key": api_key,
            "gl": "cn",  # 国家代码
            "hl": "zh-cn", # 语言代码
        }
        
        client = SerpApiClient(params)
        results = client.get_dict()
        
        # 智能解析：优先寻找最直接的答案
        if "answer_box_list" in results:
            return "\n".join(results["answer_box_list"])
        if "answer_box" in results and "answer" in results["answer_box"]:
            return results["answer_box"]["answer"]
        if "knowledge_graph" in results and "description" in results["knowledge_graph"]:
            return results["knowledge_graph"]["description"]
        if "organic_results" in results and results["organic_results"]:
            # 如果没有直接答案，则返回前三个有机结果的摘要
            snippets = [
                f"[{i+1}] {res.get('title', '')}\n{res.get('snippet', '')}"
                for i, res in enumerate(results["organic_results"][:3])
            ]
            return "\n\n".join(snippets)
        
        return f"对不起，没有找到关于 '{query}' 的信息。"

    except Exception as e:
        return f"搜索时发生错误: {e}"
    
from typing import Dict, Any

class ToolExecutor:
    """
    一个工具执行器，负责管理和执行工具。
    """
    def __init__(self):
        self.tools: Dict[str, Dict[str, Any]] = {}

    def registerTool(self, name: str, description: str, func: callable):
        """
        向工具箱中注册一个新工具。
        """
        if name in self.tools:
            print(f"警告：工具 '{name}' 已存在，将被覆盖。")
        
        self.tools[name] = {"description": description, "func": func}
        print(f"工具 '{name}' 已注册。")

    def getTool(self, name: str) -> callable:
        """
        根据名称获取一个工具的执行函数。
        """
        return self.tools.get(name, {}).get("func")

    def getAvailableTools(self) -> str:
        """
        获取所有可用工具的格式化描述字符串。
        """
        return "\n".join([
            f"- {name}: {info['description']}" 
            for name, info in self.tools.items()
        ])


# --- 工具初始化与使用示例 ---
if __name__ == '__main__':
    # 1. 初始化工具执行器
    toolExecutor = ToolExecutor()

    # 2. 注册我们的实战搜索工具
    search_description = "一个网页搜索引擎。当你需要回答关于时事、事实以及在你的知识库中找不到的信息时，应使用此工具。"
    toolExecutor.registerTool("Search", search_description, search)
    calculator_description = "一个计算器。当你需要进行数学计算，应使用此工具。"
    toolExecutor.registerTool("Calculate", calculator_description, calculator)
    
    # 3. 打印可用的工具
    print("\n--- 可用的工具 ---")
    print(toolExecutor.getAvailableTools())

    # 4. 智能体的Action调用，这次我们问一个实时性的问题
    # print("\n--- 执行 Action: Search['英伟达最新的GPU型号是什么'] ---")
    # tool_name = "Search"
    # tool_input = "英伟达最新的GPU型号是什么"
    
    print("\n--- 执行 Action: Calculate['(123 + 456) ✖️ 789 ÷12'] ---")
    tool_name = "Calculate"
    tool_input = "sin(123 + 456) ✖️ 789 ÷12"

    tool_function = toolExecutor.getTool(tool_name)
    if tool_function:
        observation = tool_function(tool_input)
        print("--- 观察 (Observation) ---")
        print(observation)
    else:
        print(f"错误：未找到名为 '{tool_name}' 的工具。")

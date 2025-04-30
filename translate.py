import asyncio
from google.adk.agents import Agent
from google.adk.agents.sequential_agent import SequentialAgent
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai import types
import sys
import requests

# 读取要求和规则文件
rules: str

try:
    with open(
        "cfug/flutter.cn.wiki/文档翻译格式-(Translation-Spec).md", "r", encoding="utf-8"
    ) as f:
        rules = f.read()
except Exception as e:
    print(f"无法读取翻译要求文件: {e}")
    rules = "未能加载翻译要求"

# 翻译要求
total_rules: str

try:
    with open(
        "cfug/flutter.cn.wiki/翻译总要求-(Translation-Guide).md", "r", encoding="utf-8"
    ) as f:
        total_rules = f.read()
except Exception as e:
    print(f"无法读取翻译要求文件: {e}")
    total_rules = "未能加载翻译要求"

# 系统提示，定义 Agent 的角色和任务
SYSTEM_PROMPT = f"""
# 你是一位专业的翻译专家，擅长将各种文档按照规则翻译成中文。

# 翻译的总要求：

要格外注意的一点是，英文原文要保留

{total_rules}

# 翻译的规则：
{rules}

"""

# 创建翻译 Agent
translate_agent = Agent(
    name="translate_agent",
    model="gemini-2.0-flash",  # 或者选择其他合适的 Gemini 模型
    description="将文档翻译成中文",
    instruction=SYSTEM_PROMPT,
    output_key="translated_text",  # 定义输出键
)

# 总体的调控 Agent (即使只有一个子 Agent，也保持结构一致性)
supervisor_agent = SequentialAgent(
    name="supervisor_agent",
    sub_agents=[translate_agent],
)

# 创建 session 服务
session_service = InMemorySessionService()
APP_NAME = "translation_app"
USER_ID = "user_default"

# 创建 runner
runner = Runner(
    agent=supervisor_agent,
    app_name=APP_NAME,
    session_service=session_service,
)

# 创建 session
session = session_service.create_session(
    app_name=APP_NAME,
    user_id=USER_ID,
    session_id="session_translate_001",  # 使用唯一的 session ID
)


def translate_doc(doc_text: str) -> str:
    """
    接收文档文本，调用 Agent 进行翻译，并返回中文结果。

    Args:
        doc_text: 需要翻译的文档文本。

    Returns:
        翻译后的中文文本。
    """
    # 将输入文本包装成 ADK 需要的 Content 格式
    content = types.Content(role="user", parts=[types.Part(text=doc_text)])

    # 运行 Agent
    events = runner.run(user_id=USER_ID, session_id=session.id, new_message=content)

    translated_output: str = ""
    # 处理 Agent 返回的事件流
    for event in events:
        if event.is_final_response():
            # 提取最终的翻译结果
            try:
                translated_output = event.content.parts[0].text
                print(f"<<< Agent Response: {translated_output}")
            except (AttributeError, IndexError) as e:
                print(f"Error extracting translation from event: {e}")
                translated_output = "翻译过程中出现错误"
            break  # 获取到最终结果后退出循环
        elif event.is_error():
            print(f"Agent run failed: {event.error}")
            translated_output = f"翻译失败: {event.error}"
            break

    if not translated_output:
        print("Warning: No final response received from the agent.")
        translated_output = "未能获取翻译结果"

    return translated_output


def get_content_url(url: str) -> str:
    """
    通过 url 获取内容
    """
    try:
        response = requests.get(url)
        return response.text
    except Exception as e:
        return f"获取内容失败: {e}"

if __name__ == "__main__":
    # 示例规则文本 (可以替换成实际需要翻译的规则)
    example_url = "https://raw.githubusercontent.com/cfug/flutter.cn/refs/heads/main/src/content/add-to-app/android/add-flutter-view.md"
    result = translate_doc(get_content_url(example_url))
    print("<--- Translated Output --->")
    print(result)
    with open('result.md', 'w', encoding='utf-8') as f:
        f.write(result)
    print("<--- Translated Output End --->")

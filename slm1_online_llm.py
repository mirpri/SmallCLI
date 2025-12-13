import openai
import time
from util import codeblock_strip
from dotenv import load_dotenv
import os

load_dotenv()

api_key = os.getenv("API_KEY")
base_url = os.getenv("BASE_URL")
model_name = "deepseek/deepseek-v3.2-exp"

client = openai.OpenAI(api_key=api_key, base_url=base_url)


def generate_steps(des, sysinfo=""):
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "system",
                    "content": """你是一个任务拆解专家，负责将用户提供的任务拆解成一个操作步骤序列给CLI Agent实现。
                目标与输出格式：
                1.  输出必须是一个Python List（['步骤1', '步骤2', ...]）。
                2.  绝对禁止任何Markdown格式（如```python）或任何多余的解释说明。
                3.  如果任务无法通过计算机完成，返回空列表：[]。
                步骤规则 (Action Rule)：
                1.  每个步骤必须是简短的一句话，且只包含一项动作。
                2.  动作类型仅限以下三种：综合推理、执行命令、文件编辑。
                3.  数据读取：每一步执行时，能且只能看到上一步的输出内容。
                4.  执行命令/文件编辑：内容必须是清晰、具体的自然语言描述，禁止包含任何不确定、需要推理的信息。
                5.  每一步的路径需要明确以相对路径或绝对路径给出。每一步的命令均在独立的环境中执行。
                6.  文件编辑：需明确指定：删除/插入的行、以及插入的内容。
                7.  选择最可靠、简单的方式实现任务，避免任何歧义。

                示例1：
                输入：请帮我用python,c++各写一个hello world文件，并运行C++代码
                输出：["执行命令: 创建一个hello_world.py文件", "文件编辑: 在hello_world.py文件写入print(\"Hello, World!\")", "执行命令: 创建hello_world.cpp文件", "综合推理: 推理出C++ hello world代码", "文件编辑: 在hello_world.cpp写入上一步得到的代码", "执行命令: 使用gcc编译hello_world.cpp为hello_world", "执行命令: 设置hello_world可执行权限", "执行命令: 运行hello_world"]
                
                示例2：
                输入：查看当前目录下的所有文件详细信息，并将结果保存到一个文本文件中
                输出：["执行命令: 详细列出当前目录下的所有文件及其信息", "文件编辑: 将上一步的输出内容保存到files_info.txt文件中"]

                示例3：
                输入：安装neofetch并使用它查看系统信息
                输出：["综合推理: 推理出安装neofetch使用的包管理器", "执行命令: 用上一步得出的包管理器执行安装neofetch的命令", "执行命令: 运行neofetch查看系统信息"]

                注意：输出必须只包含 Python List，不要包含任何Markdown格式。""",
                },
                {
                    "role": "user",
                    "content": """
                你的任务：
                请将以下用户任务拆解成符合上述规则的操作步骤序列：
                """
                    + des
                    + """
                当前系统信息："""
                    + sysinfo,
                },
            ],
            stream=False,
        )
        print(response.choices[0].message.content)
        step_string = codeblock_strip(response.choices[0].message.content)
        # print(step_string)
        return eval(step_string)

    except Exception as e:
        print(f"error: {e}")
        print("retrying...")
        time.sleep(1)
        return generate_steps(des)


if __name__ == "__main__":
    while True:
        user_input = input("请输入任务描述（'q' 退出）：")
        if user_input.lower() == "q":
            break
        steps = generate_steps(user_input)
        if not steps:
            continue
        for step in steps:
            print(step)

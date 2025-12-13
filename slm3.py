import ollama
from util import codeblock_strip
import os

def parse_file_edit_instructions(instructions, context=""):
    try:
        response = ollama.generate(
            model='qwen2.5-coder:1.5b',
            prompt=f'''指令：从以下文件编辑指令中提取文件路径，仅输出确切的文件路径，不要用任何符号括起来，也不要包含任何多余信息。
                        示例1：
                        输入：在文件data.txt的第 5 行后插入"Hello World"
                        输出：data.txt

                        示例2：
                        输入：删除config/settings.ini文件中的第 10 行
                        输出：config/settings.ini

                        现在请处理：
                        输入：{instructions}'''
        )
        filename = response['response'].strip()
        print(f"编辑文件: {filename}")
        content = ""
        if not os.path.exists(filename):
            dirpath = os.path.dirname(filename)
            if dirpath:
                os.makedirs(dirpath, exist_ok=True)
            open(filename, 'w', encoding='utf-8').close()
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.readlines()
        response = ollama.generate(
            model='qwen2.5:3b',
            prompt=f'''指令：根据以下文件编辑指令，和文件原始内容，生成修改后的完整文件内容。
                        请只输出修改后的完整文件内容，不要包含任何不应写入文件的多余信息。

                        示例1：
                        输入指令：在文件 data.txt 的第 2 行后插入 "Hello World"

                        文件原始内容：
                        Line 1
                        Line 2
                        Line 3

                        输出修改后完整内容：
                        Line 1
                        Line 2
                        Hello World
                        Line 3

                        示例2：
                        输入指令：将上一步得到的文件列表保存为file_list.txt

                        文件原始内容：
                        （空文件）

                        上下文信息：
                        上一步的输出内容为：file1.txt
                        file2.txt

                        输出修改后完整内容：
                        file1.txt
                        file2.txt

                        
                        现在请处理：
                        输入指令：{instructions}

                        上下文信息：
                        {context}

                        文件原始内容：
                        {'\n'.join(content) if len(content) > 0 else '原始文件为空'}'''
        )
        modified_content = response['response']
        modified_content = codeblock_strip(modified_content)
        return filename, modified_content
    except Exception as e:
        print(f"error: {e}")
        return None, None
    
def apply_file_edit(filename, modified_content):
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(modified_content)
        print(f"文件 {filename} 已成功更新。")
        return True
    except Exception as e:
        print(f"更新文件时出错: {e}")
        return False

def file_edit_exec(instructions, context=""):
    filename, modified_content = parse_file_edit_instructions(instructions, context=context)
    if filename and modified_content:
        return apply_file_edit(filename, modified_content)
    return False

if __name__ == "__main__":
    while True:
        user_input = input("请输入文件编辑指令（'q' 退出）：")
        if user_input.lower() == 'q':
            break
        success = file_edit_exec(user_input)
        if success:
            print("文件编辑操作完成。")
        else:
            print("文件编辑操作失败。")
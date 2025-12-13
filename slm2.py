import ollama
import subprocess
from util import codeblock_strip

def command_from_description(des,context=""):
    try:
        response = ollama.generate(
            model='qwen2.5-coder:1.5b',
            prompt = '''指令：将描述转换为Linux命令，用python list形式依次输出所有命令，list每项包含一个完整命令。
                        如果需要，请加入相关参数确保命令运行时不需要任何用户交互。
                        请只输出该列表，不要包含任何多余信息。
                        示例1：
                        输入：查看当前目录文件
                        输出：["ls"]

                        示例2：
                        输入：进入build目录进行cmake构建
                        输出：["cd build", "cmake .."]

                        示例3：
                        输入：查看系统发行版信息
                        输出：["cat /etc/os-release"]

                        示例4：
                        输入：用pacman安装gcc编译器
                        输出：["sudo pacman -S gcc --noconfirm"]

                        注意：输出必须只包含 Python List，不要包含任何Markdown代码块（如```python）。
                        上下文信息：'''+ context +'''
                        现在请处理：
                        输入：''' + des

        )
        # evaluate the model response into a Python object and join list items with " && "
        cmdstring = codeblock_strip(response['response'])
        # print(cmdstring)

        cmd_list = eval(cmdstring)
        return " && ".join(cmd_list)

    except Exception as e:
        print(f"error: {e}")
        return command_from_description(des,context)


def command_fix(old_command, error, context=""):
    try:
        response = ollama.generate(
            model="qwen2.5:3b",
            prompt = '''指令：修正以下Linux命令以解决出现的错误。
                        请只输出修正后的完整命令，不要包含任何多余信息。
                        如果需要，请加入相关参数确保命令运行时不需要任何用户交互。
                        
                        示例1：
                        输入命令：ls ./log
                        错误信息：ls: cannot access './log': No such file or directory
                        输出：mkdir -p ./log && ls ./log

                        示例2：
                        输入命令：pacman -S gcc --noconfirm
                        错误信息：error: you cannot perform this operation unless you are root.
                        输出：sudo pacman -S gcc
                        
                        现在请处理：
                        输入命令：''' + old_command + '''
                        错误信息：''' + error + '''
                        上下文信息：''' + context
        )
        fixed_command = codeblock_strip(response['response'])
        return fixed_command

    except Exception as e:
        print(f"error: {e}")
        return command_fix(old_command, error)


def command_exec(command):
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.stdout, result.stderr
    except Exception as e:
        return "", str(e)

if __name__ == "__main__":
    while True:
        user_input = input("请输入 Linux 命令描述（'q' 退出）：")
        if user_input.lower() == 'q':
            break
        command=command_from_description(user_input)
        print(command)
        if (input("是否执行该命令(y/n)? ").lower()=="y"):
            out, err=command_exec(command)
            print(out,err)
            while err:
                print("命令执行出错，尝试修正命令...")
                command=command_fix(command, err)
                print(f"修正后命令：{command}")
                if (input("是否执行该命令(y/n)? ").lower()!="y"):
                    break
                out, err=command_exec(command)
                print(out,err)
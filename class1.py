import ollama

model_name = 'qwen2.5-coder:1.5b' 

labels=["综合推理","执行命令","文件编辑"]

def classify_task_type(des):
    try:
        response = ollama.generate(
            model=model_name,
            prompt = '''你是一个专业的任务分类器，你的唯一任务是根据用户提供的任务描述，将其归类到以下三种类别之一。

                **类别定义：**
                0. 综合推理（不直接执行操作，需根据信息推理、分析、决策或生成文本作为输出，以用于下一步操作）
                1. 执行命令（任务可以通过单条或多条计算机系统命令（如Linux Shell命令）直接完成）
                2. 文件编辑（任务的核心目标是修改、写入文件内容的）

                **格式要求（铁律）：**
                请只输出**一个数字（0, 1, 或 2）**，**绝对禁止**包含任何其他文字、解释或标点符号。

                **示例：**
                输入任务: 查看当前目录文件
                输出: 1

                输入任务: 关闭计算机
                输出: 1

                输入任务: 推理出C++ hello world代码
                输出: 0

                输入任务：根据系统类型推理出使用的包管理器
                输出: 0

                输入任务: 将上一步的输出内容保存到files_info.txt文件中
                输出: 2

                **你的任务：**
                输入任务: ''' + des
        )
        # evaluate the model response into a Python object
        return int(response['response'])

    except Exception as e:
        print(f"error: {e}")
        return classify_task_type(des)
    
if __name__ == "__main__":
    while True:
        user_input = input("请输入任务描述（'q' 退出）：")
        if user_input.lower() == 'q':
            break
        step_type=classify_task_type(user_input)
        print(step_type)
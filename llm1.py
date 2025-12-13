import ollama
import time

model_name = 'qwen2.5-coder:1.5b'

def execute_inference(des, context=""):
    try:
        response = ollama.generate(
            model=model_name,
            prompt="请完成推理任务，输出仅包含答案，尽量简洁，不能包含多余内容：" + des+
            "\n上下文信息："+context
        )
        return response['response']
    except Exception as e:
        print(f"error: {e}")
        time.sleep(1)
        return execute_inference(des, context=context)

if __name__ == "__main__":
    while True:
        user_input = input("请输入推理任务描述（'q' 退出）：")
        if user_input.lower() == 'q':
            break
        ans=execute_inference(user_input)
        print(ans)
import ollama
import time
from schema import AgentContext

model_name = 'qwen2.5-coder:1.5b'

def execute_inference(des, context: AgentContext):
    try:
        response = ollama.generate(
            model=model_name,
            prompt="请完成推理任务，输出仅包含答案，尽量简洁，不能包含多余内容：" + des+
            "\n上下文信息："+context.to_prompt_string()
        )
        return response['response']
    except Exception as e:
        print(f"error: {e}")
        time.sleep(1)
        return execute_inference(des, context=context)

if __name__ == "__main__":
    dummy_context = AgentContext(sys_info="Linux Test System")
    while True:
        user_input = input("请输入推理任务描述（'q' 退出）：")
        if user_input.lower() == 'q':
            break
        ans=execute_inference(user_input, dummy_context)
        print(ans)
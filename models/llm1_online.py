import ollama
import time
import openai
import os
from dotenv import load_dotenv

load_dotenv()

base_url = os.getenv("BASE_URL")
api_key = os.getenv("API_KEY")
model_name = 'deepseek/deepseek-v3.2-exp'

client = openai.OpenAI(api_key=api_key, base_url=base_url)

def execute_inference(des, context=""):
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "system",
                    "content": "请完成推理任务，输出仅包含答案，尽量简洁，不能包含多余内容."
                        +"\n上下文信息："+context
                },
                { 
                    "role":"user", 
                    "content": des
                }
            ]
        )
        # print(response.choices[0].message.content)
        return response.choices[0].message.content
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
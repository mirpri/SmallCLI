# import slm1
import slm1_online_llm as slm1
import slm2
import slm3

import llm1
# import class1_bert as class1


user_continue="r"
steps=[]
sysinfo=slm2.command_exec("cat /etc/os-release")[0]

user_prompt=input("> ")
while user_continue!="y":
    if(user_continue=="n"):
        exit(0)
    elif(user_continue=="r"):
        steps=slm1.generate_steps(user_prompt, sysinfo=sysinfo)

        if not steps:
            print("无法生成步骤")
            exit(0)

        for i in range(len(steps)):
            print(f"{i+1}. {steps[i]}")
        user_continue=input("是否继续(y/n/r)? ").lower()
    elif(user_continue=="y"):
        break

memory=[]
context="系统信息："+sysinfo

for step in steps:
    print(step)
    # step_type=class1.classify_task_type(step)
    # print(class1.labels[step_type])
    if(step.startswith("综合推理: ")):
        step_type=0
    elif(step.startswith("执行命令: ")):
        step_type=1
    elif(step.startswith("文件编辑: ")):
        step_type=2
    step=step[6:].strip()
    success=False
    if step_type==0:
        ans=llm1.execute_inference(step,context=context)
        print(ans)
        memory.append(ans)
        success=True
    elif step_type==1:
        command=slm2.command_from_description(step,context=context)
        if command: 
            if(input(f"➜ {command} ")==''):
                out, err=slm2.command_exec(command)
                print(out,err)
                while err:
                    print("执行出错，尝试修正命令...")
                    command=slm2.command_fix(command, err, context=sysinfo)
                    if (input(f"➜ {command} ")!=''):
                        break
                    out, err=slm2.command_exec(command)
                    print(out,err)
                if not err:
                    success=True
                memory.append('\n'.join([command, out, err]))
        else:
            print("无法生成命令")
            exit(1)
    elif step_type==2:
        slm3.file_edit_exec(step,context=context)
        memory.append("")
        success=True
    else:
        success=False
    if not success:
        user_continue=input("步骤执行失败，是否继续(y/n)? ").lower()
        if user_continue=="n":
            exit(0)
    context="系统信息："+sysinfo+"\n"+("上一步信息："+memory[-1]) if len(memory[-1])>0 else "上一步无输出。"
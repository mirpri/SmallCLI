import operator
from typing import Annotated, List, TypedDict, Union
from langgraph.graph import StateGraph, END
from schema import AgentContext

# Import your existing modules
import slm1_online_llm as slm1
import slm2
import slm3
import llm1

# --- 1. Define the State (Context Management) ---
class AgentState(TypedDict):
    user_request: str
    steps: List[str]
    current_step_index: int
    agent_context: AgentContext
    last_step_success: bool

# --- 2. Define Nodes (Workflow Actions) ---

def planner_node(state: AgentState):
    """Generates the plan based on user request."""
    print(f"\n[Planner] Generating steps for: {state['user_request']}")
    # Pass the full context object
    steps = slm1.generate_steps(state['user_request'], context=state['agent_context'])
    
    if not steps:
        print("[Planner] Failed to generate steps.")
        return {"steps": [], "last_step_success": False}
    
    # Print steps for user visibility
    for i, step in enumerate(steps):
        print(f"{i+1}. {step}")
        
    return {
        "steps": steps, 
        "current_step_index": 0, 
        "last_step_success": True
    }

def router_node(state: AgentState):
    """Decides which tool to use based on the current step string."""
    steps = state['steps']
    idx = state['current_step_index']
    
    if idx >= len(steps):
        return "end"
        
    current_step = steps[idx]
    print(f"\n[Executing Step {idx+1}/{len(steps)}]: {current_step}")
    
    # Logic from original orchestrator
    if current_step.startswith("综合推理: "):
        return "inference"
    elif current_step.startswith("执行命令: "):
        return "command"
    elif current_step.startswith("文件编辑: "):
        return "edit"
    else:
        # Default fallback or error handling
        return "inference"

def inference_node(state: AgentState):
    step = state['steps'][state['current_step_index']]
    # Strip prefix
    step_desc = step.replace("综合推理: ", "").strip()
    
    # Pass context object
    ans = llm1.execute_inference(step_desc, context=state['agent_context'])
    print(f"[Inference Output]: {ans}")
    
    # Update memory in context
    state['agent_context'].memory.append(ans)
    
    return {
        "agent_context": state['agent_context'],
        "last_step_success": True
    }

def command_node(state: AgentState):
    step = state['steps'][state['current_step_index']]
    step_desc = step.replace("执行命令: ", "").strip()
    
    command = slm2.command_from_description(step_desc, context=state['agent_context'])
    
    if not command:
        return {"last_step_success": False}
        
    print(f"➜ {command}")

    out, err = slm2.command_exec(command)
    print(out, err)
    
    while err:
        print("执行出错，尝试修正命令...")
        command = slm2.command_fix(command, err, context=state['agent_context'])
        print(f"➜ {command}")
        out, err = slm2.command_exec(command)
        print(out, err)
        if not err:
            break
            
    result_str = '\n'.join([command, out, err])
    state['agent_context'].memory.append(result_str)
    
    return {
        "agent_context": state['agent_context'],
        "last_step_success": True if not err else False
    }

def edit_node(state: AgentState):
    step = state['steps'][state['current_step_index']]
    step_desc = step.replace("文件编辑: ", "").strip()
    
    success = slm3.file_edit_exec(step_desc, context=state['agent_context'])
    
    result_msg = "File edited successfully" if success else "File edit failed"
    state['agent_context'].memory.append(result_msg)
    
    return {
        "agent_context": state['agent_context'],
        "last_step_success": success
    }

def context_updater_node(state: AgentState):
    """Increments step index."""
    return {
        "current_step_index": state['current_step_index'] + 1
    }

# --- 3. Build the Graph ---

workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("planner", planner_node)
workflow.add_node("inference_exec", inference_node)
workflow.add_node("command_exec", command_node)
workflow.add_node("file_exec", edit_node)
workflow.add_node("updater", context_updater_node)

# Set Entry Point
workflow.set_entry_point("planner")

# Add Edges
# From planner, go to router logic
workflow.add_conditional_edges(
    "planner",
    router_node,
    {
        "inference": "inference_exec",
        "command": "command_exec",
        "edit": "file_exec",
        "end": END
    }
)

# After any executor, go to updater
workflow.add_edge("inference_exec", "updater")
workflow.add_edge("command_exec", "updater")
workflow.add_edge("file_exec", "updater")

# After updater, loop back to router to check if more steps exist
workflow.add_conditional_edges(
    "updater",
    router_node,
    {
        "inference": "inference_exec",
        "command": "command_exec",
        "edit": "file_exec",
        "end": END
    }
)

# Compile
app = workflow.compile()

# --- 4. Main Execution ---

if __name__ == "__main__":
    # Initial Setup
    sysinfo_list = slm2.command_exec("cat /etc/os-release")
    sysinfo = sysinfo_list[0] if sysinfo_list else "Unknown System"
    
    user_prompt = input("> ")
    
    # Initialize Context Object
    initial_context = AgentContext(sys_info=sysinfo)
    
    initial_state = {
        "user_request": user_prompt,
        "steps": [],
        "current_step_index": 0,
        "agent_context": initial_context,
        "last_step_success": True
    }
    
    # Run the graph
    for event in app.stream(initial_state):
        pass
        
    print("\n[Workflow Completed]")

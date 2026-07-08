import operator
from typing import Annotated, List, TypedDict, Union
from langgraph.graph import StateGraph, END
from schema import AgentContext

# Import your existing modules
import models.slm1_online_llm as slm1
import models.slm2 as slm2
import models.slm3 as slm3
import models.llm1 as llm1

# --- 1. Define the State (Context Management) ---
class AgentState(TypedDict):
    user_request: str
    steps: List[str]
    current_step_index: int
    agent_context: AgentContext
    last_step_success: bool
    pending_command: str
    pending_file_edit: dict # {'filename': str, 'content': str}
    sudo_password: str # Optional password for sudo commands
    retry_count: int # Track retries for current step
    last_error: str # Store error for fixing
    execution_output: str # Output from client execution
    execution_success: bool # Success status from client execution

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

def command_prep_node(state: AgentState):
    step = state['steps'][state['current_step_index']]
    step_desc = step.replace("执行命令: ", "").strip()
    
    command = slm2.command_from_description(step_desc, context=state['agent_context'])
    
    if not command:
        return {"last_step_success": False, "pending_command": ""}
        
    print(f"➜ [Generated Command] {command}")
    return {"pending_command": command}

def command_exec_node(state: AgentState):
    command = state.get('pending_command')
    output = state.get('execution_output', '')
    success = state.get('execution_success', False)
    
    print(f"➜ [Client Executed] {command}")
    print(f"Result: {output[:100]}..." if len(output) > 100 else f"Result: {output}")
    
    if not success:
        # Failed, return error for fix node
        return {
            "last_step_success": False,
            "last_error": output,
            "retry_count": state.get("retry_count", 0) + 1,
            "execution_output": "",
            "execution_success": False
        }
            
    result_str = f"{command}\n{output}"
    state['agent_context'].memory.append(result_str)
    
    return {
        "agent_context": state['agent_context'],
        "last_step_success": True,
        "pending_command": "", # Clear pending
        "sudo_password": "", # Clear password
        "retry_count": 0,
        "last_error": "",
        "execution_output": "",
        "execution_success": False
    }

def command_fix_node(state: AgentState):
    print("[Fixing Command] Attempting to fix error...")
    command = state.get('pending_command')
    err = state.get('last_error')
    
    # If sudo was used, strip the echo part for the LLM to understand the core command
    # This is a simplification.
    core_command = command
    if " | sudo -S " in command:
        parts = command.split(" | sudo -S ")
        if len(parts) > 1:
            core_command = "sudo " + parts[1]

    fixed_command = slm2.command_fix(core_command, err, context=state['agent_context'])
    print(f"➜ [Fixed Command] {fixed_command}")
    
    return {"pending_command": fixed_command}

def edit_prep_node(state: AgentState):
    step = state['steps'][state['current_step_index']]
    step_desc = step.replace("文件编辑: ", "").strip()
    
    filename, content = slm3.parse_file_edit_instructions(step_desc, context=state['agent_context'])
    
    if filename and content:
        print(f"[Generated Edit] File: {filename}")
        return {"pending_file_edit": {"filename": filename, "content": content}}
    
    return {"last_step_success": False}

def edit_exec_node(state: AgentState):
    edit_info = state.get('pending_file_edit')
    output = state.get('execution_output', '')
    success = state.get('execution_success', False)
    
    print(f"➜ [Client Edited] {edit_info.get('filename')}")
    
    result_msg = f"File edited successfully: {output}" if success else f"File edit failed: {output}"
    state['agent_context'].memory.append(result_msg)
    
    return {
        "agent_context": state['agent_context'],
        "last_step_success": success,
        "pending_file_edit": {}, # Clear pending
        "execution_output": "",
        "execution_success": False
    }

def context_updater_node(state: AgentState):
    """Increments step index."""
    return {
        "current_step_index": state['current_step_index'] + 1
    }

def command_router(state: AgentState):
    if state.get('last_step_success'):
        return "updater"
    
    # Check retry limit (e.g., 3 retries)
    if state.get('retry_count', 0) > 3:
        print("[Command Exec] Max retries reached. Failing step.")
        return "updater" # Or fail workflow
        
    return "command_fix"

# --- 3. Build the Graph ---

workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("planner", planner_node)
workflow.add_node("inference_exec", inference_node)
workflow.add_node("command_prep", command_prep_node)
workflow.add_node("command_exec", command_exec_node)
workflow.add_node("command_fix", command_fix_node)
workflow.add_node("file_prep", edit_prep_node)
workflow.add_node("file_exec", edit_exec_node)
workflow.add_node("updater", context_updater_node)

# Set Entry Point
workflow.set_entry_point("planner")

# Add Edges
workflow.add_conditional_edges(
    "planner",
    router_node,
    {
        "inference": "inference_exec",
        "command": "command_prep",
        "edit": "file_prep",
        "end": END
    }
)

workflow.add_edge("inference_exec", "updater")
workflow.add_edge("command_prep", "command_exec")

# Replace direct edge with conditional edge for retry loop
workflow.add_conditional_edges(
    "command_exec",
    command_router,
    {
        "updater": "updater",
        "command_fix": "command_fix"
    }
)

workflow.add_edge("command_fix", "command_exec") # Go back to exec after fix

workflow.add_edge("file_prep", "file_exec")
workflow.add_edge("file_exec", "updater")

workflow.add_conditional_edges(
    "updater",
    router_node,
    {
        "inference": "inference_exec",
        "command": "command_prep",
        "edit": "file_prep",
        "end": END
    }
)

# Compile (Optional here, usually done in server with checkpointer)
app = workflow.compile()

# --- 4. Main Execution ---

if __name__ == "__main__":
    # Initial Setup
    # sysinfo_list = slm2.command_exec("cat /etc/os-release")
    # sysinfo = sysinfo_list[0] if sysinfo_list else "Unknown System"
    sysinfo = "Linux Test System (Local)"
    
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

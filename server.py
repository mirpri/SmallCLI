from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uuid

from langgraph.checkpoint.memory import MemorySaver
from orchestrator_langgraph import workflow, AgentState
from schema import AgentContext
import models.slm2

app = FastAPI()

# In-memory storage for graph state
checkpointer = MemorySaver()
# Compile the graph with the checkpointer and interrupt logic
agent_app = workflow.compile(
    checkpointer=checkpointer,
    interrupt_after=["planner"], # Pause after planning to approve plan
    interrupt_before=["command_exec", "file_exec"] # Pause before executing dangerous actions
)

class TaskRequest(BaseModel):
    description: str
    system_info: Optional[str] = None

class TaskResponse(BaseModel):
    thread_id: str
    status: str
    next_step: Optional[str] = None
    pending_action: Optional[Dict[str, Any]] = None
    plan: Optional[List[str]] = None

class ApprovalRequest(BaseModel):
    thread_id: str
    approved: bool
    feedback: Optional[str] = None # Optional feedback to modify plan/command (not implemented yet)
    execution_output: Optional[str] = None # Output from client execution
    execution_success: Optional[bool] = False # Success status from client execution

@app.get("/")
def sayhello() -> dict:
    return {"message": "Welcome to Small CLI Agent Server!"}

@app.post("/agent/start", response_model=TaskResponse)
def start_agent(request: TaskRequest):
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    
    # Get system info if not provided
    sys_info = request.system_info or "Unknown System"

    initial_context = AgentContext(sys_info=sys_info)
    initial_state = {
        "user_request": request.description,
        "steps": [],
        "current_step_index": 0,
        "agent_context": initial_context,
        "last_step_success": True,
        "pending_command": "",
        "pending_file_edit": {},
        "sudo_password": ""
    }

    # Run until the first interruption (likely after planner)
    # We use stream but just get the last state
    # Actually, invoke is better if we expect it to stop
    # But invoke returns the final state, stream allows us to see progress.
    # Since we have interrupts, invoke will raise GraphInterrupt or return partial state?
    # LangGraph's invoke stops at interrupt.
    
    # We need to run it.
    # agent_app.invoke(initial_state, config=config) 
    # But invoke might return the state at interruption.
    
    result = agent_app.invoke(initial_state, config=config)
    
    # Inspect state to see where we are
    snapshot = agent_app.get_state(config)
    next_node = snapshot.next
    
    return _build_response(thread_id, snapshot)

@app.post("/agent/approve", response_model=TaskResponse)
def approve_action(request: ApprovalRequest):
    config = {"configurable": {"thread_id": request.thread_id}}
    snapshot = agent_app.get_state(config)
    
    if not snapshot.values:
        raise HTTPException(status_code=404, detail="Thread not found or expired")

    if not request.approved:
        # If rejected, we might want to abort or ask for replanning.
        # For now, let's just abort.
        return {"thread_id": request.thread_id, "status": "aborted"}

    # Resume execution
    # Update state with execution results from client
    update_values = {}
    if request.execution_output is not None:
        update_values["execution_output"] = request.execution_output
    if request.execution_success is not None:
        update_values["execution_success"] = request.execution_success
        
    if update_values:
        agent_app.update_state(config, update_values)
    
    result = agent_app.invoke(None, config=config)
    
    snapshot = agent_app.get_state(config)
    return _build_response(request.thread_id, snapshot)

@app.get("/agent/{thread_id}", response_model=TaskResponse)
def get_agent_state(thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    snapshot = agent_app.get_state(config)
    if not snapshot.values:
        raise HTTPException(status_code=404, detail="Thread not found")
    return _build_response(thread_id, snapshot)

def _build_response(thread_id: str, snapshot) -> TaskResponse:
    state = snapshot.values
    next_nodes = snapshot.next
    
    status = "running"
    pending_action = None
    
    if not next_nodes:
        status = "completed"
    elif "command_exec" in next_nodes:
        status = "waiting_for_command_approval"
        pending_action = {"type": "command", "command": state.get("pending_command")}
    elif "file_exec" in next_nodes:
        status = "waiting_for_edit_approval"
        pending_action = {"type": "edit", "details": state.get("pending_file_edit")}
    elif len(state.get("steps", [])) > 0 and state.get("current_step_index") == 0:
         # If we just finished planning (interrupt_after planner), we are here.
         # But wait, if interrupt_after planner, next node is router -> ...
         # Actually, if we interrupt AFTER planner, the next node is whatever router decides.
         # But router is conditional edge.
         # LangGraph pauses BEFORE the next node.
         # So if planner -> router -> command_prep, it might pause before command_prep?
         # No, I set interrupt_after=["planner"].
         # So it pauses before executing the edges out of planner? Or after planner finishes?
         # It pauses before the next node.
         status = "waiting_for_plan_approval"
    
    return TaskResponse(
        thread_id=thread_id,
        status=status,
        plan=state.get("steps", []),
        pending_action=pending_action,
        next_step=state.get("steps")[state.get("current_step_index")] if state.get("steps") and state.get("current_step_index") < len(state.get("steps")) else None
    )

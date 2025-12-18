from pydantic import BaseModel, Field
from typing import List

class AgentContext(BaseModel):
    sys_info: str = ""
    memory: List[str] = Field(default_factory=list)
    
    def to_prompt_string(self) -> str:
        """Converts the context into a string format suitable for LLM prompts."""
        last_output = self.memory[-1] if self.memory else "上一步无输出。"
        # We can include more history here if needed in the future
        return f"系统信息：{self.sys_info}\n上一步信息：{last_output}"

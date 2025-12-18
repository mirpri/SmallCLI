from fastapi import FastAPI

import slm1_online_llm as slm1 

app = FastAPI()

@app.get("/")
def sayhello() -> dict:
    return {"message": "Welcome to SmallCLI!"}

@app.get("/health")
def health_check() -> dict:
    return {"message": "SmallCLI Server is running."}

@app.post("/plan")
def create_plan(data: dict) -> dict:
    print("Received plan request:")
    plan = slm1.generate_steps(data.get("description", ""), sysinfo=data.get("system_info", ""))
    return {"plan": plan}

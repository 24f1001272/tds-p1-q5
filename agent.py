import os
import json
import requests
import io
import sys
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool

# 1. Define the STRICT output structure the grader demands
class BotResponse(BaseModel):
    answer: dict = Field(description="The final answer shaped exactly as requested by the user's prompt.")
    log_url: str = Field(description="The public, wget-able URL to the run.jsonl file.")

def log_action_to_jsonl(action_data):
    """Writes a single JSON object to a new line in run.jsonl"""
    with open("run.jsonl", "a") as f:
        f.write(json.dumps(action_data) + "\n")

def get_log_url():
    """
    Returns the public URL where the run.jsonl file is hosted.
    On Render, we will set the HOST_URL environment variable to your app's web address.
    If testing locally, it returns localhost.
    """
    host_url = os.environ.get("HOST_URL", "http://localhost:8080")
    # Ensure it doesn't end with a slash before adding /run.jsonl
    return f"{host_url.rstrip('/')}/run.jsonl"

@tool
def execute_python(code: str) -> str:
    """
    Executes Python code and returns the stdout (printed) output. 
    Use this to download data, load it into pandas, perform calculations, and print the answer.
    """
    old_stdout = sys.stdout
    new_stdout = io.StringIO()
    sys.stdout = new_stdout
    try:
        exec(code, globals())
        output = new_stdout.getvalue()
    except Exception as e:
        output = f"Error: {str(e)}"
    finally:
        sys.stdout = old_stdout
    return output

def run_data_agent(message_history):
    # The last message is the current task
    current_task = message_history[-1]
    
    # Log that we received a task
    log_action_to_jsonl({"event": "received_task", "task": current_task})
    
    # Setup the LLM
    llm = ChatGoogleGenerativeAI(model="gemini-3.5-flash-lite")
    llm_with_tools = llm.bind_tools([execute_python])
    
    log_action_to_jsonl({"event": "analyzing_data", "status": "in_progress"})
    
    # 1. Run the LLM to figure out the answer using Python code
    messages = [
        ("system", "You are a Python data analysis assistant. You have a tool to execute python code. "
                   "When given a data analysis question, write python code to download the dataset (if provided), "
                   "analyze it using pandas or other standard libraries, and print the answer. "
                   "IMPORTANT: Make sure your Python code prints the final result so you can read it."),
        ("human", current_task)
    ]
    
    try:
        response = llm_with_tools.invoke(messages)
        raw_answer = response.content
        
        # If the LLM decided to use our Python tool
        if response.tool_calls:
            for tool_call in response.tool_calls:
                if tool_call["name"] == "execute_python":
                    code_to_run = tool_call["args"].get("code", "")
                    # Execute the python code
                    tool_output = execute_python.invoke({"code": code_to_run})
                    raw_answer += f"\nPython Execution Output:\n{tool_output}"
    except Exception as e:
        raw_answer = f"Agent failed to calculate: {str(e)}"
        
    # 2. Extract the final answer and enforce the STRICT JSON structure requested by the user
    structured_llm = llm.with_structured_output(BotResponse)
    
    system_prompt = f"""
    You are a JSON formatter. Extract the final answer from the agent's analysis result and return it EXACTLY in the JSON shape requested by the user's original task.
    Do NOT wrap the output in markdown or backticks. Return raw JSON.
    
    Original Task from user: {current_task}
    
    Agent Analysis Result: {raw_answer}
    """
    
    result = structured_llm.invoke(system_prompt)
    
    # 3. Inject the public URL into the final output BEFORE logging it
    public_log_url = get_log_url()
    result.log_url = public_log_url
    
    log_action_to_jsonl({"event": "generated_response", "result": result.model_dump()})
    
    # 4. Return ONLY the raw JSON string as required by the assignment
    return result.model_dump_json()
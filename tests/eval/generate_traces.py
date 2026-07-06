import json
import asyncio
import os
from expense_agent.agent import workflow
from google.adk import Context

async def run_scenario(case):
    events = []
    ctx = Context(session_id=case["id"])
    
    try:
        async for event in workflow.run(ctx=ctx, node_input=case["payload"]):
            events.append({"type": "NodeEvent", "state": str(event)})
    except Exception as e:
        ex_name = type(e).__name__
        if ex_name == "RequestInput":
            events.append({"type": "RequestInput", "prompt": getattr(e, "prompt", "Please provide input")})
            
            decision = "terima" if "injection" not in case["id"] else "tolak"
            
            try:
                async for resume_event in workflow.run(ctx=ctx, node_input=decision):
                    events.append({"type": "ResumeEvent", "state": str(resume_event)})
            except Exception as e2:
                events.append({"type": "Error", "message": str(e2)})
        else:
            events.append({"type": "Error", "message": str(e)})

    return events

async def main():
    os.makedirs("artifacts/traces", exist_ok=True)
    
    with open("tests/eval/datasets/basic-dataset.json", "r") as f:
        dataset = json.load(f)
        
    traces = []
    
    for case in dataset:
        print(f"Running {case['id']}...")
        events = await run_scenario(case)
        traces.append({
            "id": case["id"],
            "input": case["payload"],
            "events": events,
            "expected_routing": case["expected_routing"],
            "expected_security": case["expected_security"]
        })
        
    with open("artifacts/traces/generated_traces.json", "w") as f:
        json.dump(traces, f, indent=2)
    print("Traces generated successfully.")

if __name__ == "__main__":
    asyncio.run(main())

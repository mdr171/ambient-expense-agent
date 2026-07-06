import json
import base64
import re
import typing
from pydantic import BaseModel
from google.adk.events import RequestInput, Event, EventActions
from google.adk.workflow import Workflow, node
from google.adk.agents.context import Context
from google.adk.agents.llm_agent import LlmAgent

from .config import MODEL_NAME, AUTO_APPROVE_THRESHOLD

class ExpenseData(BaseModel):
    amount: float
    submitter: str
    category: str
    description: str
    date: str

class ExpenseState(BaseModel):
    expense: ExpenseData | None = None
    risk_assessment: str | None = None
    status: str | None = None
    human_decision: str | None = None
    security_flags: list[str] = []

def parse_event(node_input: typing.Any) -> ExpenseState:
    """Entry point: Receives JSON and converts it into a pydantic state."""
    # Handle ADK 2.3.0 UI Chat input (Content object)
    if hasattr(node_input, 'parts') and node_input.parts:
        raw_text = node_input.parts[0].text if hasattr(node_input.parts[0], 'text') else str(node_input.parts[0])
        try:
            node_input = json.loads(raw_text)
        except Exception:
            node_input = {"data": raw_text}
            
    if not isinstance(node_input, dict):
        node_input = {"data": str(node_input)}
        
    if "data" in node_input:
        data = node_input["data"]
        if isinstance(data, str):
            try:
                decoded = base64.b64decode(data).decode('utf-8')
                data = json.loads(decoded)
            except Exception:
                data = json.loads(data)
    else:
        data = node_input
    
    expense = ExpenseData(**data)
    return ExpenseState(expense=expense, security_flags=[])

def route_expense(node_input: ExpenseState) -> Event:
    """Business routing logic based on expense amount."""
    if node_input.expense.amount < AUTO_APPROVE_THRESHOLD:
        return Event(actions=EventActions(route="auto_approve"), output=node_input)
    return Event(actions=EventActions(route="security_screen"), output=node_input)

def auto_approve(node_input: ExpenseState) -> ExpenseState:
    """Automatically approve expenses below the threshold ($100)."""
    node_input.status = "APPROVED_AUTO"
    return node_input

def security_screen(node_input: ExpenseState) -> ExpenseState:
    """PII Redaction (SSN, Credit Card) and Prompt Injection detection."""
    desc = node_input.expense.description
    
    # 1. PII Redaction
    ssn_pattern = r'\b\d{3}-\d{2}-\d{4}\b'
    cc_pattern = r'\b(?:\d[ -]*?){13,16}\b'
    
    if re.search(ssn_pattern, desc):
        desc = re.sub(ssn_pattern, '[REDACTED SSN]', desc)
        node_input.security_flags.append("PII_REDACTED_SSN")
        
    if re.search(cc_pattern, desc):
        desc = re.sub(cc_pattern, '[REDACTED CREDIT CARD]', desc)
        node_input.security_flags.append("PII_REDACTED_CC")
        
    node_input.expense.description = desc
    
    # 2. Prompt Injection Detection
    injection_keywords = ["ignore previous", "bypass", "auto-approve", "force approve"]
    desc_lower = desc.lower()
    if any(keyword in desc_lower for keyword in injection_keywords):
        node_input.security_flags.append("PROMPT_INJECTION_DETECTED")
        node_input.status = "SECURITY_REVIEW_REQUIRED"
        
    return node_input

def route_security(node_input: ExpenseState) -> Event:
    """If injection is detected, route directly to human (bypass LLM)."""
    if "PROMPT_INJECTION_DETECTED" in node_input.security_flags:
        return Event(actions=EventActions(route="wait_for_human"), output=node_input)
    return Event(actions=EventActions(route="prepare_review"), output=node_input)

def check_company_policy(category: str) -> str:
    """Checks the maximum expense policy limit based on category."""
    policies = {
        "Software": "Maximum $1000 per transaction. Anything above requires VP approval.",
        "Travel": "Maximum $2000 per transaction for economy or business class flights.",
        "Meals": "Maximum $50 per transaction. Must not include alcohol.",
    }
    return policies.get(category, "No specific policy. Use standard reasonable judgement.")

@node
def prepare_review(ctx: Context, node_input: ExpenseState) -> Event:
    """Prepares the prompt and state before sending to the LLM."""
    prompt = f"""
    You are a financial risk assessor. Evaluate the following expense:
    Submitter: {node_input.expense.submitter}
    Category: {node_input.expense.category}
    Amount: ${node_input.expense.amount}
    Description: {node_input.expense.description}
    Date: {node_input.expense.date}
    
    Use the check_company_policy tool to verify if this amount violates the policy.
    Provide a brief risk assessment and warn if there is anything suspicious, especially for unusual expenses.
    """
    yield Event(output=prompt, state={"expense": node_input.expense.model_dump() if node_input.expense else None})

llm_reviewer = LlmAgent(
    name="llm_reviewer",
    model=MODEL_NAME,
    instruction="Evaluate the financial risk of the given expense. You MUST check the company policy first.",
    tools=[check_company_policy],
    output_key="risk_assessment"
)

@node
def save_review(ctx: Context, node_input: str) -> ExpenseState:
    """Saves the LLM result back to the ExpenseState."""
    expense_data = ctx.state.get("expense", None)
    state = ExpenseState(expense=ExpenseData(**expense_data) if expense_data else None)
    state.risk_assessment = node_input
    state.status = "PENDING_HUMAN_REVIEW"
    return state

def wait_for_human(node_input: ExpenseState) -> RequestInput:
    """Pauses the graph to request human approval."""
    security_warning = ""
    if node_input.security_flags:
        security_warning = f"⚠️ SECURITY FLAGS: {', '.join(node_input.security_flags)}\n"
        
    prompt_text = (
        f"🚨 EXPENSE REQUIRES HUMAN APPROVAL:\n"
        f"From: {node_input.expense.submitter} | Amount: ${node_input.expense.amount}\n"
        f"{security_warning}"
        f"AI Assessment: {node_input.risk_assessment or 'NONE (Security Bypass)'}\n"
        f"Type 'APPROVE' to approve, or 'REJECT' to reject."
    )
    return RequestInput(
        prompt=prompt_text,
        state=node_input
    )

def handle_human_decision(node_input: typing.Any, ctx: typing.Any) -> ExpenseState:
    """Processes the final human decision (APPROVE / REJECT)."""
    payload = str(node_input).lower()
    decision = "APPROVED" if "approve" in payload or "yes" in payload else "REJECTED"
    
    # Reconstruct the Pydantic model from ADK's internal State wrapper
    state_dict = ctx.state.to_dict() if hasattr(ctx.state, 'to_dict') else dict(ctx.state)
    state = ExpenseState(**state_dict)
    
    state.human_decision = decision
    state.status = "PROCESSED"
    return state

# --- Initialize ADK Workflow ---
workflow = Workflow(
    name="expense_agent", 
    state_schema=ExpenseState,
    edges=[
        ("START", parse_event),
        (parse_event, route_expense, {"auto_approve": auto_approve, "security_screen": security_screen}),
        (security_screen, route_security, {"wait_for_human": wait_for_human, "prepare_review": prepare_review}),
        (prepare_review, llm_reviewer),
        (llm_reviewer, save_review),
        (save_review, wait_for_human),
        (wait_for_human, handle_human_decision)
    ]
)

# Export agent for Agents CLI
root_agent = workflow

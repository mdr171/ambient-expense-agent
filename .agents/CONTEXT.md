# Local Project Context & Secure Coding Standards

## Project Overview
This is an **Ambient Expense Approval Agent** built with Google ADK 2.0.
It processes expense submissions through a multi-stage pipeline with
automated security screening and human-in-the-loop approval.

## Core Paved Roads
We systematically address common vulnerability classes by guiding the agent
to use our pre-configured, secure-by-default helper patterns.

1. **Tool Input Validation**: Every agent tool must validate incoming
   parameters against strict Pydantic schemas rather than parsing raw
   dictionaries or strings.
2. **No Shell Execution**: Never use `run_command` or raw shell execution
   tools unless explicitly approved.
3. **PII Redaction**: All expense descriptions MUST be scanned for PII
   (SSN, credit card numbers) and redacted before any LLM processing
   or human review.
4. **Prompt Injection Defense**: Descriptions containing manipulation
   keywords (e.g., "ignore previous", "bypass", "force approve") MUST
   be flagged and routed directly to human review, bypassing LLM evaluation.
5. **Pre-Commit Remediation Loop**: If a git commit fails due to a pre-commit
   hook error (such as a Semgrep scan finding), treat the violation as a
   refactoring task, apply targeted fixes, and attempt to commit again.

## TDD Planning Gate
During the Plan phase, you must decompose the workspace task into logical,
modular stages. Every implementation plan MUST include a dedicated
**Security Boundaries & Assertions** section outlining specific edge cases
that could exploit the feature.

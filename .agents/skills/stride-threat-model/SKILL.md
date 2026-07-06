---
name: stride-threat-model
description: Evaluates the system architecture against STRIDE Threat Modeling framework to produce a threat_model.md report.
---

# STRIDE Threat Modeling Skill

When you use this skill, you must act as a Senior Security Engineer evaluating the codebase using the STRIDE methodology.

## Instructions
1. Analyze the entry points of the application (e.g. FastAPI endpoints, Pub/Sub triggers, LLM inputs).
2. Evaluate each component against the STRIDE categories:
   - **S**poofing
   - **T**ampering
   - **R**epudiation
   - **I**nformation Disclosure
   - **D**enial of Service
   - **E**levation of Privilege
3. Generate a comprehensive `threat_model.md` artifact in the workspace root detailing your findings and recommendations.
4. Highlight any critical vulnerabilities you find.

# Agentic AI Red Teaming Lab

Local adversarial evaluation framework for testing the security robustness of LLM-based agentic systems using Ollama + Python.

---

## Features

- Prompt injection testing
- System prompt extraction attempts
- Memory poisoning simulation
- Unsafe tool-use evaluation
- Automated risk scoring
- Comparative multi-model evaluation

---

## Models Evaluated

- Llama 3.2 3B
- Mistral 7B
- Qwen 2.5 7B
- Gemma2 9B

---

## Tech Stack

- Python
- Ollama
- Local LLM inference
- Rich console visualization

---

## Project Structure

```text
local-agentic-redteam/
├── attacks.py
├── config.py
├── evaluator.py
├── llm_ollama.py
├── run_redteam.py
├── victim_agent.py
└── requirements.txt
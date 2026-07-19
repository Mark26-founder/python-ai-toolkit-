# Python AI Toolkit

> **A provider-agnostic Python library that delivers reusable infrastructure for building reliable, maintainable, and scalable AI applications.**

[![Python](https://img.shields.io/badge/Python-3.11+-blue?style=flat-square)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Stable-success?style=flat-square)](#)

## Overview

Python AI Toolkit is a collection of reusable engineering components designed to solve recurring infrastructure problems in modern AI systems. Instead of repeatedly implementing retry mechanisms, token management, structured parsing, configuration handling, and logging across projects, the toolkit provides modular, fully typed, and documented implementations that can be reused in any Python AI application.

The library is provider-agnostic and framework-independent, making it suitable for applications built on OpenAI, Anthropic, Google Gemini, local models, or custom inference services.

---

## Features

- Full Jitter Exponential Backoff retry engine
- Synchronous and asynchronous retry decorators
- Token counting and context window management
- Prompt budgeting and cost estimation
- Structured parsing utilities
- Typed configuration management
- Structured logging utilities
- Provider-agnostic architecture
- Fully typed APIs
- Modular package design
- Comprehensive documentation
- Unit-tested components

---

## Modules

| Module | Purpose |
|---------|---------|
| **retry** | Fault-tolerant execution with configurable retry policies, exponential backoff, lifecycle callbacks, and exception handling. |
| **tokens** | Token counting, context window management, prompt budgeting, and API cost estimation. |
| **parsers** | Safe parsing and validation of structured LLM outputs into strongly typed Python objects. |
| **config** | Typed configuration models and reusable configuration utilities. |
| **logging** | Structured logging helpers designed for AI workflows and long-running systems. |

---

## Design Principles

- **Provider Agnostic** — No dependency on any specific AI provider or SDK.
- **Reusable** — Designed to be shared across multiple AI projects.
- **Strongly Typed** — Comprehensive type hints for reliability and developer tooling.
- **Modular** — Independent components with clear separation of concerns.
- **Minimal Dependencies** — Prefer the Python standard library whenever practical.
- **Testable** — Deterministic behavior and maintainable architecture.

---

## Repository Structure

```text
python-ai-toolkit/
│
├── src/
│   ├── retry/
│   ├── tokens/
│   ├── parsers/
│   ├── config/
│   └── logging/
│
├── tests/
├── docs/
├── examples/
└── pyproject.toml
```

---

## Example

```python
from retry import RetryPolicy, retry

policy = RetryPolicy(
    max_attempts=3,
    base_delay=1.0,
    retry_exceptions=(ConnectionError, TimeoutError),
)

@retry(policy)
def call_model():
    ...
```

---

## Engineering Goals

Python AI Toolkit emphasizes engineering quality over framework abstraction. Every component is designed to be:

- Reusable across projects
- Provider independent
- Fully documented
- Strongly typed
- Easy to test
- Simple to extend
- Suitable for production AI infrastructure

---

## Use Cases

- LLM applications
- AI agents
- Retrieval-Augmented Generation (RAG)
- Workflow automation
- Multi-provider AI systems
- AI microservices
- Research prototypes
- Production AI infrastructure

---

## License

Released under the MIT License.

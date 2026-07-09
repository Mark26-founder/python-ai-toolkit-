# Tokens Package

Why token management matters: when working with LLMs, managing prompt size, completion length, budgeting limits, and accurate financial forecasting is essential to prevent system failures, keep costs under control, and avoid context window overflows.

## Features

- **Token Counting**: Provider-agnostic interface to count prompt and completion tokens.
- **Context Windows**: Calculations to determine remaining capacity and safe prompt limits.
- **Budgeting**: Track allocations and enforce caps programmatically.
- **Cost Estimation**: Forecast single request and monthly recurring model costs with injected rates.

## Architecture

```
                 +-------------------+
                 |    TokenCounter   |
                 +---------+---------+
                           | uses
                           v
                 +---------+---------+
                 |     Tokenizer     | (Protocol)
                 +-------------------+

+---------------+  +--------------------+  +---------------+
| ContextWindow |  | TokenBudgetManager |  | CostEstimator |
+---------------+  +--------------------+  +---------------+
```

## Installation

```bash
pip install .
```

## Quick Start

### Token Counting

```python
from typing import Sequence
from tokens import TokenCounter, Tokenizer

class SimpleTokenizer(Tokenizer):
    def encode(self, text: str) -> Sequence[int]:
        # Minimal mock representation: split words as tokens
        return [1] * len(text.split())

counter = TokenCounter(SimpleTokenizer())
count = counter.count("Hello world from Antigravity")
print(f"Tokens: {count.token_count}, Characters: {count.character_count}")
```

### Context Windows

```python
from tokens import ContextWindow

window = ContextWindow(max_tokens=4096, reserved_completion_tokens=512)
print("Remaining:", window.remaining(2000))
print("Safe limit:", window.available_prompt_tokens(2000))
print("Overflow:", window.has_overflow(5000))
```

### Budgeting

```python
from tokens import TokenBudgetManager

budget = TokenBudgetManager(total_budget=10000, reserved_completion_tokens=1000)
print("Remaining budget:", budget.remaining(5000))
print("Within budget:", budget.within_budget(12000))
```

### Cost Estimation

```python
from tokens import CostEstimator, Pricing

pricing = Pricing(input_cost_per_1k_tokens=0.015, output_cost_per_1k_tokens=0.060)
estimator = CostEstimator(pricing)
cost = estimator.estimate(prompt_tokens=1000, completion_tokens=200)
print(f"Total cost: {cost.total_cost} {cost.currency}")
```

## Design Principles

- **Zero Third-party Dependencies**: Relies exclusively on the Python standard library.
- **Protocol-driven Injections**: Clean decoupling from concrete tokenizer implementations (e.g. Tiktoken, SentencePiece).
- **Strong Typing**: Full Python type hints with frozen immutable data models.

## Limitations

- Does not include pre-packaged model rates (rates must be explicitly injected).
- Does not run parsing or serialization transformations (operates strictly on text inputs).

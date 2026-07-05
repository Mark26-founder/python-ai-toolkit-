# Retry Package — Python AI Toolkit

A production-grade, provider-agnostic resilience utility built for Python 3.11+. This package provides robust retry mechanics natively supporting both synchronous and asynchronous workflows with configurable jittered exponential backoffs.

## Architecture

The package follows a decoupled, unidirectional dependency chain to avoid circular references and guarantee thread-safety:

`ExponentialBackoff` ➔ `RetryPolicy` ➔ `Decorators` ➔ `Callbacks` ➔ `Exceptions`

* **`RetryPolicy`**: A frozen, validated configuration dataclass mapping parameters and hook assignments.
* **`ExponentialBackoff`**: Pure functional engine computing backoff delays.
* **`Callbacks`**: Lifecycle interfaces tracking runtime context across execution steps.

## Retry Lifecycle

1. **Invoke**: Intercept target callable.
2. **Execute**: Evaluate operation.
   * *Success*: Fire `on_success` hook ➔ Return result.
   * *Caught Tracked Exception*: 
     * If `attempt == max_attempts`: Fire `on_failure` ➔ Raise `MaxRetriesExceededError`.
     * If `attempt < max_attempts`: Fire `before_retry` ➔ Sleep calculated delay ➔ Fire `after_retry` ➔ Re-execute loop.

## Configuration & Usage

### Basic Synchronous Example

```python
from retry import retry, RetryPolicy

policy = RetryPolicy(max_attempts=3, base_delay=0.5)

@retry(policy=policy)
def fetch_ai_metadata():
    # Transient network call
    pass

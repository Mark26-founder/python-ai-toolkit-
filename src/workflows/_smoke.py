import sys
sys.path.insert(0, 'src')

# --- import smoke test ---
from workflows import (
    WorkflowError, StepExecutionError, PipelineConfigurationError,
    ContextError, WorkflowValidationError,
    ExecutionMetadata, WorkflowContext,import sys
sys.path.insert(0, 'src')

# --- import smoke test ---
from workflows import (
    WorkflowError, StepExecutionError, PipelineConfigurationError,
    ContextError, WorkflowValidationError,
    ExecutionMetadata, WorkflowContext,
    StepStatus, StepResult, Step, FunctionStep,
    PipelineOptions, Pipeline,
    StepOutcome, ExecutionSummary, StepExecutor, PipelineExecutor,
)

# --- basic context round-trip ---
ctx = WorkflowContext(workflow_name='smoke')
ctx.set('x', 42)
assert ctx.get('x', int) == 42
assert ctx.has('x')
assert not ctx.has('y')
assert ctx.get_or_default('y', 'default') == 'default'

# --- FunctionStep ---
def double(c):
    c.set('result', c.get('x', int) * 2)

step = FunctionStep(double, name='DoubleStep')
assert step.name == 'DoubleStep'
result = step.run(ctx)
assert result.succeeded
assert ctx.get('result', int) == 84

# --- Pipeline + PipelineExecutor ---
pipeline = Pipeline(name='smoke-pipeline')
pipeline.add(FunctionStep(lambda c: c.set('greeting', 'hello'), name='SetGreeting'))
pipeline.add(FunctionStep(lambda c: c.set('msg', c.get('greeting', str) + ' world'), name='AppendWorld'))
pipeline.validate()

ctx2 = WorkflowContext(workflow_name='smoke-pipeline')
executor = PipelineExecutor()
summary = executor.run(pipeline, ctx2)
assert summary.succeeded, summary.errors
assert ctx2.get('msg', str) == 'hello world'
assert summary.step_count == 2
assert summary.total_duration_seconds >= 0

# --- run_safe ---
bad_pipeline = Pipeline(name='bad')
def boom_func(c):
    raise ZeroDivisionError("division by zero")

bad_pipeline.add(FunctionStep(boom_func, name='BoomStep'))
ctx3 = WorkflowContext(workflow_name='bad')
summary2 = PipelineExecutor().run_safe(bad_pipeline, ctx3)
assert not summary2.succeeded
assert len(summary2.errors) == 1

# --- StepExecutor ---
single_ctx = WorkflowContext(workflow_name='single')
single_ctx.set('v', 'ok')
se_result = StepExecutor().run(FunctionStep(lambda c: c.get('v', str), name='GetV'), single_ctx)
assert se_result.succeeded
assert se_result.output == 'ok'

print('All smoke tests passed.')

    StepStatus, StepResult, Step, FunctionStep,
    PipelineOptions, Pipeline,
    StepOutcome, ExecutionSummary, StepExecutor, PipelineExecutor,
)

# --- basic context round-trip ---
ctx = WorkflowContext(workflow_name='smoke')
ctx.set('x', 42)
assert ctx.get('x', int) == 42
assert ctx.has('x')
assert not ctx.has('y')
assert ctx.get_or_default('y', 'default') == 'default'

# --- FunctionStep ---
def double(c):
    c.set('result', c.get('x', int) * 2)

step = FunctionStep(double, name='DoubleStep')
assert step.name == 'DoubleStep'
result = step.run(ctx)
assert result.succeeded
assert ctx.get('result', int) == 84

# --- Pipeline + PipelineExecutor ---
pipeline = Pipeline(name='smoke-pipeline')
pipeline.add(FunctionStep(lambda c: c.set('greeting', 'hello'), name='SetGreeting'))
pipeline.add(FunctionStep(lambda c: c.set('msg', c.get('greeting', str) + ' world'), name='AppendWorld'))
pipeline.validate()

ctx2 = WorkflowContext(workflow_name='smoke-pipeline')
executor = PipelineExecutor()
summary = executor.run(pipeline, ctx2)
assert summary.succeeded, summary.errors
assert ctx2.get('msg', str) == 'hello world'
assert summary.step_count == 2
assert summary.total_duration_seconds >= 0

# --- run_safe ---
bad_pipeline = Pipeline(name='bad')
bad_pipeline.add(FunctionStep(lambda c: 1/0, name='BoomStep'))
ctx3 = WorkflowContext(workflow_name='bad')
summary2 = PipelineExecutor().run_safe(bad_pipeline, ctx3)
assert not summary2.succeeded
assert len(summary2.errors) == 1

# --- StepExecutor ---
single_ctx = WorkflowContext(workflow_name='single')
single_ctx.set('v', 'ok')
se_result = StepExecutor().run(FunctionStep(lambda c: c.get('v', str), name='GetV'), single_ctx)
assert se_result.succeeded
assert se_result.output == 'ok'

print('All smoke tests passed.')

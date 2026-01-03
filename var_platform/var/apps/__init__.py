"""Product layers (apps) built on top of the VAR kernel.

The kernel lives in:
- var.agent (state machine)
- var.tools (typed tool boundaries)
- var.store (durable artifacts)
- var.research + var.eval (testbed harness)

Apps are intentionally thin wrappers that:
- choose configs
- wire toolboxes
- provide a UI

This separation is what lets the same codebase serve:
- research testbed
- university coursework
- homeschooling (long-term)
"""

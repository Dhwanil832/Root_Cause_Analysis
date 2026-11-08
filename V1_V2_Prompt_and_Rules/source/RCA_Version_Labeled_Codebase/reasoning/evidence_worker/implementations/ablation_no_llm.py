"""Minimal evidence-worker baseline: execute the lead's permitted action.

No second model call, no redirection, no explicit coverage/failure diagnosis.
The host still enforces discovery-before-request and access to delivered data.
"""


def execute(runtime,action):
    return runtime._execute_baseline(action)

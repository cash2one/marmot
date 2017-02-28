# -*- coding: utf-8 -*-
import django.dispatch


# Fired when a new WorkflowActivity starts navigating a workflow. The sender is
# an instance of the WorkflowActivity model
workflow_started = django.dispatch.Signal()

# Fired just before a WorkflowActivity creates a new item in the Workflow History
# (the sender is an instance of the WorkflowHistory model)
workflow_pre_change = django.dispatch.Signal()

# Fired after a WorkflowActivity creates a new item in the Workflow History (the
# sender is an instance of the WorkflowHistory model)
workflow_post_change = django.dispatch.Signal()

# Fired when a WorkflowActivity causes a transition to a new state (the sender is
# an instance of the WorkflowHistory model)
workflow_transitioned = django.dispatch.Signal()

# Fired when a comment is created during the lift of a WorkflowActivity (the
# sender is an instance of the WorkflowHistory model)
workflow_commented = django.dispatch.Signal()

# Fired when an active WorkflowActivity reaches a workflow's end state. The
# sender is an instance of the WorkflowActivity model
workflow_ended = django.dispatch.Signal()

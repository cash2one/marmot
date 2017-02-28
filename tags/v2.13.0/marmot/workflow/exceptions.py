# -*- coding: utf-8 -*-


class WorkflowException(Exception):
    pass


class UnableToActivateWorkflow(WorkflowException):
    """
    To be raised if unable to activate the workflow because it did not pass the
    validation steps
    """


class UnableToStartWorkflow(WorkflowException):
    """
    To be raised if a WorkflowActivity is unable to start a workflow
    """


class UnableToProgressWorkflow(WorkflowException):
    """
    To be raised if the WorkflowActivity is unable to progress a workflow with a
    particular transition.
    """


class UnableToAddCommentToWorkflow(WorkflowException):
    """
    To be raised if the WorkflowActivity is unable to log a comment in the
    WorkflowHistory
    """


class UnableToDisableParticipant(WorkflowException):
    """
    To be raised if the WorkflowActivity is unable to disable a participant
    """


class UnableToEnableParticipant(WorkflowException):
    """
    To be raised if the WorkflowActivity is unable to enable a participant
    """

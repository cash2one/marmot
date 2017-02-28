# -*- coding: utf-8 -*-
"""
Model tests for Workflow
"""
from __future__ import unicode_literals

import sys
import datetime

from django.contrib.auth.models import User
from django.test.client import Client
from django.test import TestCase

from workflow.models import Workflow, State, Transition, WorkflowActivity, WorkflowHistory


class ModelTestCase(TestCase):
    """
    Testing Models
    """
    # Reference fixtures here
    fixtures = ['workflow_test_data']

    def test_workflow_lifecycle(self):
        """
        Makes sure the methods in the Workflow model work as expected
        """
        # All new workflows start with status DEFINITION - from the fixtures
        w = Workflow.objects.get(id=1)
        self.assertEquals(Workflow.DEFINITION, w.status)

        # Activate the workflow
        w.activate()
        self.assertEquals(Workflow.ACTIVE, w.status)

        # Retire it.
        w.retire()
        self.assertEquals(Workflow.RETIRED, w.status)

    def test_workflow_is_valid(self):
        """
        Makes sure that the validation for a workflow works as expected
        """
        # from the fixtures
        w = Workflow.objects.get(id=1)
        self.assertEquals(Workflow.DEFINITION, w.status)

        # make sure the workflow contains exactly one start state
        # 0 start states
        state1 = State.objects.get(id=1)
        state1.is_start_state = False
        state1.save()
        self.assertEqual(False, w.is_valid())
        self.assertEqual(True, 'There must be only one start state' in w.errors['workflow'])
        state1.is_start_state = True
        state1.save()

        # >1 start states
        state2 = State.objects.get(id=2)
        state2.is_start_state = True
        state2.save()
        self.assertEqual(False, w.is_valid())
        self.assertEqual(True, 'There must be only one start state' in w.errors['workflow'])
        state2.is_start_state = False
        state2.save()

        # make sure we have at least one end state
        # 0 end states
        end_states = w.states.filter(is_end_state=True)
        for state in end_states:
            state.is_end_state = False
            state.save()
        self.assertEqual(False, w.is_valid())
        self.assertEqual(True, 'There must be at least one end state' in w.errors['workflow'])
        for state in end_states:
            state.is_end_state = True
            state.save()

        # make sure we don't have any orphan states
        orphan_state = State(name='orphaned_state', workflow=w)
        orphan_state.save()
        self.assertEqual(False, w.is_valid())
        self.assertEqual(True, orphan_state.id in w.errors['states'])
        msg = 'This state is orphaned. There is no way to get to it given ' \
              'the current workflow topology.'
        self.assertEqual(True, msg in w.errors['states'][orphan_state.id])
        orphan_state.delete()

        # make sure we don't have any cul-de-sacs from which one can't
        # escape (re-using an end state for the same effect)
        cul_de_sac = end_states[0]
        cul_de_sac.is_end_state = False
        cul_de_sac.save()
        self.assertEqual(False, w.is_valid())
        self.assertEqual(True, cul_de_sac.id in w.errors['states'])
        msg = 'This state is a dead end. It is not marked as an end state' \
              ' and there is no way to exit from it.'
        self.assertEqual(True, msg in w.errors['states'][cul_de_sac.id])
        cul_de_sac.is_end_state = True
        cul_de_sac.save()

    def test_workflow_has_errors(self):
        """
        Ensures that has_errors() returns the appropriate response for all
        possible circumstances
        """
        # Some housekeepeing
        w = Workflow.objects.get(id=1)
        u = User.objects.get(id=1)
        w.activate()
        w2 = w.clone(u)

        # A state with no errors
        state1 = State.objects.get(id=1)
        w.is_valid()
        self.assertEqual([], w.has_errors(state1))

        # A state with errors
        state1.is_start_state = False
        state1.save()
        w.is_valid()
        msg = 'This state is orphaned. There is no way to get to it given' \
              ' the current workflow topology.'
        self.assertEqual([msg], w.has_errors(state1))

        # A transition with no errors
        transition = Transition.objects.get(id=10)
        w.is_valid()
        self.assertEqual([], w.has_errors(transition))

        # A state not associated with the workflow
        state2 = w2.states.all()[0]
        state2.is_start_state = False
        state2.save()
        w.is_valid()
        # The state is a problem state but isn't anything to do with the
        # workflow w
        self.assertEqual([], w.has_errors(state2))

    def test_workflow_activate_validation(self):
        """
        Makes sure that the appropriate validation of a workflow happens
        when the activate() method is called
        """
        # from the fixtures
        w = Workflow.objects.get(id=1)
        self.assertEquals(Workflow.DEFINITION, w.status)

        # make sure only workflows in definition can be activated
        w.status = Workflow.ACTIVE
        w.save()
        try:
            w.activate()
        except Exception, instance:
            self.assertEqual('Only workflows in the "definition" state may be activated',
                             instance.args[0])
        else:
            self.fail('Exception expected but not thrown')
        w.status = Workflow.DEFINITION
        w.save()

        # Lets make sure the workflow is validated before being activated by
        # making sure the workflow in not valid
        state1 = State.objects.get(id=1)
        state1.is_start_state = False
        state1.save()
        try:
            w.activate()
        except Exception, instance:
            self.assertEqual("Cannot activate as the workflow doesn't validate.",
                             instance.args[0])
        else:
            self.fail('Exception expected but not thrown')
        state1.is_start_state = True
        state1.save()

        # so all the potential pitfalls have been validated. Lets make sure
        # we *can* approve it as expected.
        w.activate()
        self.assertEqual(Workflow.ACTIVE, w.status)

    def test_workflow_retire_validation(self):
        """
        Makes sure that the appropriate state is set against a workflow when
        this method is called
        """
        w = Workflow.objects.get(id=1)
        w.retire()
        self.assertEqual(Workflow.RETIRED, w.status)

    def test_state_deadline(self):
        """
        Makes sure we get the right result from the deadline() method in the
        State model
        """
        w = Workflow.objects.get(id=1)
        s = State(name='test', workflow=w)
        s.save()

        # Lets make sure the default is correct
        self.assertEquals(None, s.deadline())

        # Changing the unit of time measurements mustn't change anything
        s.estimation_unit = s.HOUR
        s.save()
        self.assertEquals(None, s.deadline())

        # Only when we have a positive value in the estimation_value field
        # should a deadline be returned
        s._today = lambda: datetime.datetime(2000, 1, 1, 0, 0, 0)

        # Seconds
        s.estimation_unit = s.SECOND
        s.estimation_value = 1
        s.save()
        expected = datetime.datetime(2000, 1, 1, 0, 0, 1)
        actual = s.deadline()
        self.assertEquals(expected, actual)

        # Minutes
        s.estimation_unit = s.MINUTE
        s.save()
        expected = datetime.datetime(2000, 1, 1, 0, 1, 0)
        actual = s.deadline()
        self.assertEquals(expected, actual)

        # Hours
        s.estimation_unit = s.HOUR
        s.save()
        expected = datetime.datetime(2000, 1, 1, 1, 0)
        actual = s.deadline()
        self.assertEquals(expected, actual)

        # Days
        s.estimation_unit = s.DAY
        s.save()
        expected = datetime.datetime(2000, 1, 2)
        actual = s.deadline()
        self.assertEquals(expected, actual)

        # Weeks
        s.estimation_unit = s.WEEK
        s.save()
        expected = datetime.datetime(2000, 1, 8)
        actual = s.deadline()
        self.assertEquals(expected, actual)

    def test_workflowactivity_current_state(self):
        """
        Check we always get the latest state (or None if the WorkflowActivity
        hasn't started navigating a workflow
        """
        w = Workflow.objects.get(id=1)
        u = User.objects.get(id=1)
        wa = WorkflowActivity(workflow=w, created_by=u)
        wa.save()
        # We've not started the workflow yet so make sure we don't get
        # anything back
        self.assertEqual(None, wa.current_state())
        wa.start(u)
        # We should be in the first state
        s1 = State.objects.get(id=1)  # From the fixtures
        current_state = wa.current_state()
        # check we have a good current state
        self.assertNotEqual(None, current_state)
        self.assertEqual(s1, current_state.state)
        # Lets progress the workflow and make sure the *latest* state is the
        # current state
        tr = Transition.objects.get(id=1)
        wa.progress(tr, u)
        s2 = State.objects.get(id=2)
        current_state = wa.current_state()
        self.assertEqual(s2, current_state.state)
        self.assertEqual(tr, current_state.transition)

    def test_workflowactivity_start(self):
        """
        Make sure the method works in the right way for all possible
        situations
        """
        w = Workflow.objects.get(id=1)
        u = User.objects.get(id=1)
        wa = WorkflowActivity(workflow=w, created_by=u)
        wa.save()
        # Lets make sure we can't start a workflow that has been stopped
        wa.force_stop(u, 'foo')
        try:
            wa.start(u)
        except Exception, instance:
            self.assertEqual('Already completed', instance.args[0])
        else:
            self.fail('Exception expected but not thrown')
        wa = WorkflowActivity(workflow=w, created_by=u)
        wa.save()
        # Lets make sure we can't start a workflow activity if there isn't
        # a single start state
        s2 = State.objects.get(id=2)
        s2.is_start_state = True
        s2.save()
        try:
            wa.start(u)
        except Exception, instance:
            self.assertEqual('Cannot find single start state',
                             instance.args[0])
        else:
            self.fail('Exception expected but not thrown')
        s2.is_start_state = False
        s2.save()
        # Lets make sure we *can* start it now we only have a single start
        # state
        wa.start(u)
        # We should be in the first state
        s1 = State.objects.get(id=1)  # From the fixtures
        current_state = wa.current_state()
        # check we have a good current state
        self.assertNotEqual(None, current_state)
        self.assertEqual(s1, current_state.state)
        # Lets make sure we can't "start" the workflowactivity again
        try:
            wa.start(u)
        except Exception, instance:
            self.assertEqual('Already started', instance.args[0])
        else:
            self.fail('Exception expected but not thrown')

    def test_workflowactivity_progress(self):
        """
        Make sure the transition from state to state is validated and
        recorded in the correct way.
        """
        # Some housekeeping...
        w = Workflow.objects.get(id=1)
        u = User.objects.get(id=1)
        wa = WorkflowActivity(workflow=w, created_by=u)
        wa.save()
        self.assertEqual(None, wa.completed_on)
        # Validation checks:
        # 1. The workflow activity must be started
        tr5 = Transition.objects.get(id=5)
        try:
            wa.progress(tr5, u)
        except Exception, instance:
            self.assertEqual('Start the workflow before attempting to transition',
                             instance.args[0])
        else:
            self.fail('Exception expected but not thrown')
        wa.start(u)
        # 2. The transition's from_state *must* be the current state
        try:
            wa.progress(tr5, u)
        except Exception, instance:
            self.assertEqual('Transition not valid (wrong parent)',
                             instance.args[0])
        else:
            self.fail('Exception expected but not thrown')
        # Lets test again with a valid transition with the correct
        # from_state
        tr1 = Transition.objects.get(id=1)
        wa.progress(tr1, u)
        s2 = State.objects.get(id=2)
        self.assertEqual(s2, wa.current_state().state)
        # 3. All mandatory events for the state are in the worklow history
        # (s2) has a single mandatory event associated with it
        tr2 = Transition.objects.get(id=2)
        try:
            wa.progress(tr2, u)
        except Exception, instance:
            self.assertEqual('Transition not valid (mandatory event missing)',
                             instance.args[0])
        else:
            self.fail('Exception expected but not thrown')

    def test_workflowactivity_add_comment(self):
        """
        Make sure we can add comments to the workflow history via the
        WorkflowActivity instance
        """
        w = Workflow.objects.get(id=1)
        u = User.objects.get(id=1)
        wa = WorkflowActivity(workflow=w, created_by=u)
        wa.save()

        # Test we can add a comment to an un-started workflow
        wh = wa.add_comment(u, 'test')
        self.assertEqual('test', wh.note)
        self.assertEqual(WorkflowHistory.COMMENT, wh.log_type)
        self.assertEqual(None, wh.state)
        # Start the workflow and add a comment
        wa.start(u)
        s = State.objects.get(id=1)
        wh = wa.add_comment(u, 'test2')
        self.assertEqual('test2', wh.note)
        self.assertEqual(WorkflowHistory.COMMENT, wh.log_type)
        self.assertEqual(s, wh.state)
        # Add a comment from an unknown user
        u2 = User.objects.get(id=2)
        wh = wa.add_comment(u2, 'test3')
        self.assertEqual('test3', wh.note)
        self.assertEqual(WorkflowHistory.COMMENT, wh.log_type)
        self.assertEqual(s, wh.state)
        # Make sure we can't add an empty comment
        try:
            wa.add_comment(u, '')
        except Exception, instance:
            self.assertEqual('Cannot add an empty comment', instance.args[0])
        else:
            self.fail('Exception expected but not thrown')

    def test_workflowactivity_force_stop(self):
        """
        Make sure a WorkflowActivity is stopped correctly with this method
        """
        # Make sure we can appropriately force_stop an un-started workflow
        # activity
        w = Workflow.objects.get(id=1)
        u = User.objects.get(id=1)
        wa = WorkflowActivity(workflow=w, created_by=u)
        wa.save()
        wa.force_stop(u, 'foo')
        self.assertNotEqual(None, wa.completed_on)
        self.assertEqual(None, wa.current_state())
        # Lets make sure we can force_stop an already started workflow
        # activity
        wa = WorkflowActivity(workflow=w, created_by=u)
        wa.save()
        wa.start(u)
        wa.force_stop(u, 'foo')
        self.assertNotEqual(None, wa.completed_on)
        wh = wa.current_state()
        self.assertEqual('Workflow forced to stop! Reason given: foo', wh.note)
        self.assertEqual(None, wh.deadline)

    def test_workflow_history_unicode(self):
        """
        Make sure the __unicode__() method returns the correct string for
        workflow history items
        """
        w = Workflow.objects.get(id=1)
        u = User.objects.get(id=1)
        wa = WorkflowActivity(workflow=w, created_by=u)
        wa.save()
        wh = wa.start(u)
        self.assertEqual('Started workflow created by test_admin - Administrator', wh.__unicode__())

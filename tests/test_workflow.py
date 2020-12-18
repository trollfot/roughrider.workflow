import pytest
from roughrider.predicate import Error, Validator, Or
from roughrider.workflow.components import Action, Transition, Transitions
from roughrider.workflow.workflow import (
    WorkflowItem, WorkflowState, Workflow)


class Document:
    state = None
    body = ""


def NonEmptyDocument(item, **namespace):
    if not item.body:
        raise Error(message='Body is empty.')


class RoleValidator(Validator):

    def __init__(self, role):
        self.role = role

    def __call__(self, item, role=None, **namespace):
        if role != self.role:
            raise Error(message=f'Unauthorized. Missing the `{role}` role.')


class PublicationWorkflow(Workflow):

    class wrapper(WorkflowItem):

        @property
        def state(self):
            return self.workflow.get(self.item.state)

        @state.setter
        def state(self, state):
            self.item.state = state.name


    class states(WorkflowState):
        draft = 'Draft'
        published = 'Published'
        submitted = 'Submitted'


    transitions = Transitions((
        Transition(
            origin=states.draft,
            target=states.published,
            action=Action(
                'Publish',
                constraints=[NonEmptyDocument, RoleValidator('publisher')]
            )
        ),
        Transition(
            origin=states.published,
            target=states.draft,
            action=Action(
                'Retract',
                constraints=[
                    Or((RoleValidator('owner'),
                        RoleValidator('publisher')))
                ]
            )
        ),
        Transition(
            origin=states.draft,
            target=states.submitted,
            action=Action(
                'Submit',
                constraints=[NonEmptyDocument, RoleValidator('owner')],
            )
        ),
        Transition(
            origin=states.submitted,
            target=states.published,
            action=Action(
                'Publish',
                constraints=[NonEmptyDocument, RoleValidator('publisher')],
            )
        )
    ))


workflow = PublicationWorkflow('draft')


@workflow.subscribe('Submit')
def submit_trigger(trn, item, role, messages):
    messages.append('I did trigger !!')


def test_publish_worflow():
    item = Document()
    workflow_item = workflow(item, role='some role')
    assert workflow_item.state == workflow.get('draft')
    assert not workflow_item.get_possible_transitions()

    item.body = "Some text here"
    assert not workflow_item.get_possible_transitions()

    messages = []
    workflow_item = workflow(item, role='owner', messages=messages)
    assert workflow_item.get_possible_transitions() == (
        workflow.transitions[2],
    )

    workflow_item.transition_to(PublicationWorkflow.states.submitted)
    assert messages == ['I did trigger !!']

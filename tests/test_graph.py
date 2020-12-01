import pytest
from roughrider.workflow.graph import (
    WorkflowState, OR, Workflow, Validator, Error, Action, Transition, Transitions)


class Document:
    __workflow_state__ = None
    body = ""


def submit_trigger(item, **namespace):
    raise RuntimeError('I did trigger !!')


class NonEmptyDocument(Validator):

    @classmethod
    def validate(cls, item, **namespace):
        if not item.body:
            raise Error(message='Body is empty.')


class RoleValidator(Validator):

    def __init__(self, role):
        self.role = role

    def validate(self, item, role=None, **namespace):
        if role != self.role:
            raise Error(message=f'Unauthorized. Missing the `{role}` role.')


class PublicationWorkflow(Workflow):

    class states(WorkflowState):
        draft = 'Draft'
        published = 'Published'
        submitted = 'Submitted'


    transitions = Transitions(
        publish_directly=Transition(
            origin=states.draft,
            target=states.published,
            action=Action(
                'Publish',
                constraints=[NonEmptyDocument, RoleValidator('publisher')]
            )
        ),
        retract=Transition(
            origin=states.published,
            target=states.draft,
            action=Action(
                'Retract',
                constraints=[
                    OR(RoleValidator('owner'),
                       RoleValidator('publisher'))
                ]
            )
        ),
        submit=Transition(
            origin=states.draft,
            target=states.submitted,
            action=Action(
                'Submit',
                constraints=[NonEmptyDocument, RoleValidator('owner')],
                triggers=[submit_trigger]
            )
        ),
        publish=Transition(
            origin=states.submitted,
            target=states.published,
            action=Action(
                'Publish',
                constraints=[NonEmptyDocument, RoleValidator('publisher')],
            )
        )
    )


workflow = PublicationWorkflow('draft')


def test_publish_worflow():
    item = Document()
    workflow_item = workflow(item, role='some role')
    assert workflow_item.state == workflow.get_state('draft')
    assert workflow_item.get_possible_transitions() == {}

    item.body = "Some text here"
    assert workflow_item.get_possible_transitions() == {}

    workflow_item = workflow(item, role='owner')
    assert workflow_item.get_possible_transitions() == {
        'submit': workflow.transitions['submit']
    }

    with pytest.raises(RuntimeError) as exc:
        workflow_item.set_state('submitted')

    assert str(exc.value) == 'I did trigger !!'

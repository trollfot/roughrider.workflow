import pytest
from roughrider.workflow.exceptions import Error
from roughrider.workflow.meta import OR, Workflow, Validator


class Document:
    __workflow_state__ = None
    body = ""


class PublicationWorkflow(Workflow):
    pass


workflow = PublicationWorkflow(default_state='draft')


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


workflow.add_action(
    'Publish', origin='draft', target='published',
    constraints=[NonEmptyDocument, RoleValidator('publisher')],
    triggers=[]
)

workflow.add_action(
    'Retract', origin='published', target='draft',
    constraints=[OR(RoleValidator('owner'), RoleValidator('publisher'))],
    triggers=[]
)

workflow.add_action(
    'Submit', origin='draft', target='submitted',
    constraints=[NonEmptyDocument, RoleValidator('owner')],
    triggers=[submit_trigger]
)

workflow.add_action(
    'Publish', origin='submitted', target='published',
    constraints=[NonEmptyDocument, RoleValidator('publisher')],
    triggers=[]
)


def test_publish_worflow():
    item = Document()
    workflow_item = workflow(item, role='some role')
    assert workflow_item.state == workflow.states.get('draft')
    assert workflow_item.get_target_states() == {}

    item.body = "Some text here"
    assert workflow_item.get_target_states() == {}

    workflow_item = workflow(item, role='owner')
    assert workflow_item.get_target_states() == {
        'Submit': workflow['submitted']
    }

    with pytest.raises(RuntimeError) as exc:
        workflow_item.set_state('submitted')

    assert str(exc.value) == 'I did trigger !!'

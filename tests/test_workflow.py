import pytest
from roughrider.workflow.exceptions import Error
from roughrider.workflow.meta import OR, Workflow, Validator, StatefulItem


class Document(StatefulItem):
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
    'Submit', origin='draft', target='submitted',
    constraints=[NonEmptyDocument, RoleValidator('owner')],
    triggers=[submit_trigger]
)

workflow.add_action(
    'Publish', origin='draft', target='published',
    constraints=[NonEmptyDocument, RoleValidator('publisher')],
    triggers=[]
)

workflow.add_action(
    'Unpublish', origin='published', target='draft',
    constraints=[OR(RoleValidator('owner'), RoleValidator('publisher'))],
    triggers=[]
)

workflow.add_action(
    'Retract', origin='submitted', target='draft',
    constraints=[NonEmptyDocument, RoleValidator('owner')],
    triggers=[]
)

workflow.add_action(
    'Publish', origin='submitted', target='published',
    constraints=[NonEmptyDocument, RoleValidator('publisher')],
    triggers=[]
)


def test_worflow_inexisting_default_state():
    item = Document()
    workflow.default_state = 'default'
    workflow_item = workflow(item)

    with pytest.raises(KeyError):
        workflow_item.state


def test_worflow_set_state_directly():
    item = Document()
    item.__workflow_state__ = 'published'
    workflow.default_state = 'draft'
    workflow_item = workflow(item)
    assert workflow_item.state == workflow['published']


def test_worflow_item_without_state():
    item = object()
    with pytest.raises(TypeError):
        workflow_item = workflow(item)


def test_worflow_transition_to_unknown_state():
    item = Document()
    workflow.default_state = 'draft'
    workflow_item = workflow(item)
    with pytest.raises(LookupError):
        workflow_item.set_state('something')


def test_worflow_unknown_transition():
    item = Document()
    item.__workflow_state__ = 'published'
    workflow.default_state = 'draft'
    workflow_item = workflow(item)
    with pytest.raises(LookupError):
        workflow_item.set_state('submitted')


def test_publish_worflow():
    item = Document()
    workflow.default_state = 'draft'
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

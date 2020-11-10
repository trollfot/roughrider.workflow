import pytest
from roughrider.workflow.meta import Workflow, State, StatefulItem


draft = State(
    title="Draft",
    identifier="myproject.draft",
    destinations={
        "Submit": "myproject.submitted",
        "Directly publish": "myproject.published"
    }
)


submitted = State(
        title="Submitted",
        identifier="myproject.submitted",
        destinations={
            'Retract': 'myproject.draft',
            'Publish': 'myproject.published'
        }
)


published =  State(
    title="Published",
    identifier="myproject.published",
    destinations={
        'Retract': 'myproject.draft',
        'Re-submit': 'myproject.submitted'
    }
)


class PublicationWorkflow(Workflow):
    pass


class OtherWorkflow(Workflow):
    pass


class Document(StatefulItem):
    __workflow_state__ = None
    body = ""


PublicationWorkflow.register(Document, draft, default=True)
PublicationWorkflow.register(Document, submitted)
PublicationWorkflow.register(Document, published)


def test_publish_worflow():
    item = Document()
    workflow = PublicationWorkflow(item)
    assert workflow.current_state == draft


def test_other_workflow():
    item = Document()
    workflow = OtherWorkflow(item)
    with pytest.raises(LookupError):
        workflow.get_state('myproject.draft')

from roughrider.workflow.meta import Workflow, State


class PublicationWorkflow(Workflow):
    pass


class OtherWorkflow(Workflow):
    pass


class Item:
    pass


PublicationWorkflow.register(
    Item, State(
        title="Draft",
        identifier="myproject.draft",
        destinations={
            "Submit": "myproject.submitted",
            "Directly publish": "myproject.published"
        }
    )
)


PublicationWorkflow.register(
    Item, State(
        title="Submitted",
        identifier="myproject.submitted",
        destinations={
            'Retract': 'myproject.draft',
            'Publish': 'myproject.published'
        }
    )
)


PublicationWorkflow.register(
    Item, State(
        title="Published",
        identifier="myproject.published",
        destinations={
            'Retract': 'myproject.draft',
            'Re-submit': 'myproject.submitted'
        }
    )
)


def test_publish_worflow():
    item = Item()
    workflow = PublicationWorkflow(item)
    state = workflow.get_state('myproject.draft')


def test_other_workflow():
    item = Item()
    workflow = OtherWorkflow(item)
    state = workflow.get_state('myproject.draft')

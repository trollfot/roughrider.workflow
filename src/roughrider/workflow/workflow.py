import enum
from typing import Type
from roughrider.workflow.transition import State, Transitions


class WorkflowState(State, enum.Enum):
    pass


class Workflow:

    states: Type[WorkflowState]
    transitions: Transitions
    default_state: WorkflowState

    def __init__(self, default_state):
        self.default_state = self.states[default_state]  # idempotent

    def __getitem__(self, name) -> WorkflowState:
        return self.states[name]

    def get(self, name=None):
        if name is None:
            return self.default_state
        return self.states[name]

    def __call__(self, item, **namespace):
        return WorkflowItem(self, item, **namespace)


class WorkflowItem:

    def __init__(self, workflow, item, **namespace):
        self.item = item
        self.workflow = workflow
        self.namespace = namespace

    @property
    def state(self):
        return self.workflow.get(self.item.__workflow_state__)

    def get_possible_actions(self):
        return tuple(self.workflow.transitions.available(
            self.state, self.item, **self.namespace))

    def set_state(self, target_state: str):
        target = self.workflow.states[target_state]
        trn = self.workflow.transitions.find(self.state, target)
        error = trn.action.check_constraints(self.item, **self.namespace)
        if error is not None:
            raise error
        for trigger in trn.action.triggers:
            trigger(self.item, **self.namespace)
        self.item.__workflow_state__ = target.name
        return

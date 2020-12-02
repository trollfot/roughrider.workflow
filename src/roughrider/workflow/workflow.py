import enum
from abc import ABC, abstractmethod
from typing import Type, Optional
from roughrider.workflow.transition import State, Transitions
from roughrider.workflow.validation import ConstraintsErrors


class WorkflowState(State, enum.Enum):
    pass


class WorkflowItem(ABC):

    def __init__(self, workflow, item, **namespace):
        self.workflow = workflow
        self.item = item
        self.namespace = namespace

    def get_possible_transitions(self):
        origin = self.get_state()
        return tuple(self.workflow.transitions.available(
            origin, self.item, **self.namespace))

    def check_reachable(self, state: State) -> Optional[ConstraintsErrors]:
        origin = self.get_state()
        target = self.workflow.states(state)  # idempotent
        trn = self.workflow.transitions.find(origin, target)
        error = trn.action.check_constraints(self.item, **self.namespace)
        if error is not None:
            return error
        for trigger in trn.action.triggers:
            trigger(self.item, **self.namespace)
        return None

    @abstractmethod
    def get_state(self) -> WorkflowState:
        pass

    @abstractmethod
    def set_state(self, state: WorkflowState):
        pass


class Workflow:

    states: Type[WorkflowState]
    wrapper: Type[WorkflowItem]
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
        return self.wrapper(self, item, **namespace)

import enum
from abc import ABC, abstractproperty
from collections import defaultdict
from typing import Type, Optional, Dict, Callable
from roughrider.workflow.components import State, Transitions, Transition


class WorkflowState(State, enum.Enum):
    pass


class WorkflowItem(ABC):

    state: WorkflowState

    def __init__(self, workflow, item, **namespace):
        self.workflow = workflow
        self.item = item
        self.namespace = namespace

    @abstractproperty
    def state(self):
        pass

    def get_possible_transitions(self):
        return tuple(self.workflow.transitions.available(
             self.state, self.item, **self.namespace))

    def get_transition(self, target: State) -> Optional[Transition]:
        target = self.workflow.states(target)  # idempotent
        return self.workflow.transitions.find(self.state, target)

    def apply_transition(self, transition: Transition):
        error = transition.action.check_constraints(
            self.item, **self.namespace)
        if error is not None:
            raise error
        self.state = transition.target

    def transition_to(self, state: State):
        transition = self.get_transition(state)
        self.apply_transition(transition)


class Workflow:

    states: Type[WorkflowState]
    wrapper: Type[WorkflowItem]
    transitions: Transitions
    default_state: WorkflowState

    def __init__(self, default_state):
        if default_state in self.states.__members__:
            self.default_state = self.states[default_state]
        else:
            self.default_state = self.states(default_state)

    def __getitem__(self, name: str) -> WorkflowState:
        return self.states[name]

    def __call__(self, item, **namespace):
        return self.wrapper(self, item, **namespace)

    def get(self, name=None):
        if name is None:
            return self.default_state
        return self.states[name]

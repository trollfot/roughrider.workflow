import enum
from abc import ABC, abstractproperty
from collections import defaultdict
from typing import Type, Optional, Dict, Callable
from roughrider.workflow.transition import State, Transitions, Transition
from roughrider.workflow.validation import ConstraintsErrors


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
        self.workflow.notify(
            transition.action.identifier,
            transition, self.item, **self.namespace)

    def transition_to(self, state: State):
        transition = self.get_transition(state)
        self.apply_transition(transition)


class Workflow:

    states: Type[WorkflowState]
    wrapper: Type[WorkflowItem]
    transitions: Transitions
    default_state: WorkflowState
    subscribers: Dict[str, Callable]

    def __init__(self, default_state):
        self.default_state = self.states[default_state]  # idempotent
        self.subscribers = defaultdict(list)

    def __getitem__(self, name) -> WorkflowState:
        return self.states[name]

    def __call__(self, item, **namespace):
        return self.wrapper(self, item, **namespace)

    def get(self, name=None):
        if name is None:
            return self.default_state
        return self.states[name]

    def subscribe(self, event_name: str):
        def wrapper(func):
            self.subscribers[event_name].append(func)
        return wrapper

    def notify(self, event_name: str, *args, **kwargs):
        if event_name in self.subscribers:
            for subscriber in self.subscribers[event_name]:
                if (result := subscriber(*args, **kwargs)):
                    return result

import enum
import inspect
from collections import UserDict
from abc import ABC, abstractmethod
from typing import NamedTuple
from typing import Type, Iterable, List, Tuple, Optional, Mapping, Callable
from dataclasses import dataclass, field


class Error(Exception):
    message: str

    def __init__(self, message):
        self.message = message


class ConstraintsErrors(Exception):
    errors: List[Error]

    def __init__(self, *errors):
        self.errors = list(errors)

    def __iter__(self):
        return iter(self.errors)


Errors = Optional[ConstraintsErrors]


class Validator(ABC):
    """A validator.
    """
    description: Optional[str]

    @abstractmethod
    def validate(self, item, **namespace):
        """Validates the item.
        """


class OR(Validator):

    def __init__(self, *validators):
        self.validators = validators

    def validate(self, item, **namespace):
        errors = []
        for validator in self.validators:
            try:
                validator.validate(item, **namespace)
                return
            except Error as exc:
                errors.append(exc)
            except ConstraintsErrors as exc:
                errors.extends(exc.errors)

        raise ConstraintsError(*errors)


def resolve_validators(validators: List[Validator],
                       item, **namespace) -> Optional[ConstraintsErrors]:
    """Checks the validators against the given object.
    """
    errors = []
    for validator in validators:
        try:
            validator.validate(item, **namespace)
        except Error as exc:
            errors.append(exc)
        except ConstraintsErrors as exc:
            errors.extends(exc.errors)
    if errors:
        return ConstraintsErrors(*errors)


@dataclass
class Action:

    identifier: str
    constraints: Iterable[Validator] = field(default_factory=list)
    triggers: Iterable[Callable] = field(default_factory=list)

    def check_constraints(self, item, **namespace) -> Errors:
        """Checks the constraints against the given object.
        """
        if self.constraints:
            return resolve_validators(self.constraints, item, **namespace)


@dataclass
class State:
    identifier: str


class WorkflowState(State, enum.Enum):
    pass


class Transition(NamedTuple):
    action: Action
    origin: WorkflowState
    target: WorkflowState


class Transitions(Tuple[Transition]):

    def available(self, origin, item, **ns):
        return (trn for trn in self
                if (trn.origin == origin and
                    trn.action.check_constraints(item, **ns) is None))

    def find(self, origin, target):
        for trn in self:
            if trn.origin == origin and trn.target == target:
                return trn
        raise LookupError(f'No transition from {origin} to {target}')


class Workflow:

    states: Type[WorkflowState]
    transitions: Mapping[str, Transition]
    default_state: WorkflowState

    def __init__(self, default_state):
        self.default_state = self.states[default_state]  # idempotent

    def __getitem__(self, name):
        return self.states[name]

    def get_state(self, name):
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
        if self.item.__workflow_state__:
            return self.workflow.get_state(self.item.__workflow_state__)
        return self.workflow.get_state(None)

    def get_possible_transitions(self):
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

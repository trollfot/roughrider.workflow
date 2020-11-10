from abc import ABC, abstractmethod
from typing import Any, Iterable, List, Optional, Mapping, Callable
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
    actions: Mapping[str, Action] = field(default_factory=dict)

    def add_action(self, target: str, name: str,
                   constraints: list, triggers: list):
        self.actions[target] = Action(name, constraints, triggers)

    def available_actions(self, item, **namespace):
        for target, action in self.actions.items():
            if action.check_constraints(item, **namespace) is None:
                yield action.identifier, target


class Workflow:

    def __init__(self, default_state):
        self.states = {}
        self.default_state = default_state

    def __getitem__(self, name):
        return self.states[name]

    def add_state(self, identifier):
        state = State(identifier)
        self.states[identifier] = state
        return state

    def get_state(self, identifier):
        if identifier is None:
            return self.states[self.default_state]
        return self.states[identifier]

    def add_action(self, name: str, origin: str, target: str,
                   constraints: list, triggers: list):
        origin_state = self.states.get(origin)
        if origin_state is None:
            origin_state = self.add_state(origin)

        target_state = self.states.get(target)
        if target_state is None:
            target_state = self.add_state(target)

        origin_state.add_action(target, name, constraints, triggers)

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

    def get_target_states(self):
        return {action: self.workflow.get_state(target_state)
                for action, target_state in self.state.available_actions(
                        self.item, **self.namespace)}

    def set_state(self, target_state: str):
        if (target_action := self.state.actions.get(target_state)) is not None:
            if (error := target_action.check_constraints(
                    self.item, **self.namespace)) is not None:
                raise error
            for trigger in target_action.triggers:
                trigger(self.item, **self.namespace)
            self.item.__workflow_state__ = target_state
            return
        raise LookupError('Unknow action {action}')

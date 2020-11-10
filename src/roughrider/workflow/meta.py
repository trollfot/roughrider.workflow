from abc import ABC, abstractmethod
from typing import Any, List, Optional, Mapping, Callable
from dataclasses import dataclass, field
from roughrider.workflow import exceptions


Errors = Optional[exceptions.ConstraintsErrors]


class Validator(ABC):
    """A validator.
    """
    description: Optional[str]

    @abstractmethod
    def validate(self, item, **namespace):
        """Validates the item.
        """


class StatefulItem(ABC):
    __workflow_state__: Optional[str] = None


class OR(Validator):

    def __init__(self, *validators):
        self.validators = validators

    def validate(self, item: Any, **namespace) -> Errors:
        errors = []
        for validator in self.validators:
            try:
                validator.validate(item, **namespace)
                return
            except exceptions.Error as exc:
                errors.append(exc)
            except exceptions.ConstraintsErrors as exc:
                errors.extends(exc.errors)

        raise exceptions.ConstraintsError(*errors)


def resolve_validators(
        validators: List[Validator], item: Any, **namespace) -> Errors:
    """Checks the validators against the given object.
    """
    errors = []
    for validator in validators:
        try:
            validator.validate(item, **namespace)
        except exceptions.Error as exc:
            errors.append(exc)
        except exceptions.ConstraintsErrors as exc:
            errors.extends(exc.errors)
    if errors:
        return exceptions.ConstraintsErrors(*errors)


@dataclass
class Action:

    identifier: str
    constraints: List[Validator] = field(default_factory=list)
    triggers: List[Callable] = field(default_factory=list)

    def check_constraints(self, item: Any, **namespace) -> Errors:
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
        action = Action(name, constraints, triggers)
        self.actions[target] = action
        return action

    def available_actions(self, item: Any, **namespace):
        for target, action in self.actions.items():
            if action.check_constraints(item, **namespace) is None:
                yield action.identifier, target


class Workflow:

    default_state: str

    def __init__(self, default_state):
        self.states = {}
        self.default_state = default_state

    def __contains__(self, name: str) -> bool:
        return name in self.states

    def __getitem__(self, name: str) -> State:
        return self.states[name]

    def add_state(self, identifier: str) -> State:
        state = State(identifier)
        self.states[identifier] = state
        return state

    def get_state(self, identifier) -> State:
        if identifier is None:
            return self.states[self.default_state]
        return self.states[identifier]

    def add_action(self, name: str, origin: str, target: str,
                   constraints: list, triggers: list) -> Action:
        origin_state = self.states.get(origin)
        if origin_state is None:
            origin_state = self.add_state(origin)

        target_state = self.states.get(target)
        if target_state is None:
            target_state = self.add_state(target)

        return origin_state.add_action(
            target, name, constraints, triggers)

    def __call__(self, item, **namespace) -> 'WorkflowItem':
        return WorkflowItem(self, item, **namespace)


class WorkflowItem:

    def __init__(self, workflow: Workflow, item: StatefulItem, **namespace):
        if not isinstance(item, StatefulItem):
            raise TypeError(f'Item needs to be of type {StatefulItem}')

        self.item = item
        self.workflow = workflow
        self.namespace = namespace

    @property
    def state(self) -> State:
        if self.item.__workflow_state__:
            return self.workflow.get_state(self.item.__workflow_state__)
        return self.workflow.get_state(None)

    def get_target_states(self) -> Mapping[str, State]:
        return {action: self.workflow.get_state(target_state)
                for action, target_state in self.state.available_actions(
                        self.item, **self.namespace)}

    def set_state(self, target: str):
        if not target in self.workflow:
            raise LookupError(f'Unknown target state `{target}`.')
        origin = self.state
        if (action := origin.actions.get(target)) is not None:
            if (error := action.check_constraints(
                    self.item, **self.namespace)) is not None:
                raise error
            for trigger in action.triggers:
                trigger(self.item, **self.namespace)
            self.item.__workflow_state__ = target
            return
        raise LookupError(
            f'No transition from {origin.identifier} to {target}. ')

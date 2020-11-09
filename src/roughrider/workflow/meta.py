from abc import ABC, abstractmethod
from typing import Any, Iterable, Optional, Mapping
from dataclasses import dataclass, field
import reg


class Error:
    pass


class ConstraintsError(Exception):

    def __init__(self, trigger, *errors):
        self.trigger = trigger
        self.errors = errors


class LocksError(Exception):

    def __init__(self, trigger, *errors):
        self.trigger = trigger
        self.errors = errors


class StatefulItem:
    __workflow_state__: str


class Validator(ABC):
    """A validator.
    """
    description: str

    @abstractmethod
    def validate(self, obj, **namespace) -> Optional[Error]:
        """Validates the item.
        """


@dataclass
class State:
    """Workflow State
    Nomenclature::
       * constraints: pre-validation
       * locks: post-validation
    """
    identifier: str
    title: str
    description: str = ""
    pre_validators: Iterable[Validator] = field(default_factory=list)
    post_validators: Iterable[Validator] = field(default_factory=list)
    destinations: Mapping[str, 'State'] = field(default_factory=dict)

    def check_constraints(self, item) ->  Iterable[Error]:
        """Checks the constraints against the given object.
        """
        return [validator.validate(item)
                for validator in self.pre_validators]

    def check_locks(self, item) -> Iterable[Error]:
        """Checks the locks against the given object.
        """
        return [validator.validate(item)
                for validator in self.post_validators]

    def get_reachable_states(self, item) -> Mapping[str, str]:
        if bool(self.check_locks(item)) is False:
            return {
                state.identifer: action
                for action, state in self.destinations.items()
                if not state.check_constraints(item)
            }
        return {}


class WorkflowMeta(type):

    def register(cls, item, state):
        assert issubclass(item, StatefulItem)

        def state_factory(workflow, item, id):
            return state

        workflow_state.register(
            state_factory, workflow=cls, item=item, id=state.identifier)


class Workflow(metaclass=WorkflowMeta):

    item: StatefulItem
    current_state: State
    available_states: Optional[Iterable[State]]

    def __init__(self, item: StatefulItem, **namespace):
        self.item = item
        self.namespace = namespace

    @property
    def current_state(self):
        return self.get_state(self.item.__workflow_state__)

    def get_state(self, name) -> State:
        return workflow_state(self, self.item, name)

    def trigger_transition(self, action: str) -> None:
        current = self.current_state
        if errors := current.check_locks(self.item, **namespace):
            raise LocksError(action, *errors)
        destination = self.current_state.destinations.get(action)
        if destination is None:
            raise LookupError(f'Unknow trigger: {action}')
        if errors := destination.check_constraints(item, **namespace):
            raise ConstraintsError(action, *errors)


@reg.dispatch(
    reg.match_instance('workflow'),
    reg.match_instance('item'),
    reg.match_key('id'))
def workflow_state(workflow: Workflow, item: State, id: str):
    raise LookupError(
        f'Workflow {workflow}: unknown state {id} for object {item}')

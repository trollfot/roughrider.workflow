from abc import ABC, abstractmethod
from typing import Any, Iterable, List, Optional, Mapping, ClassVar
from dataclasses import dataclass, field
import reg


@dataclass
class Error:
    state_identifier: str
    message: str


class ConstraintsError(Exception):

    trigger: str
    errors: List[Error]

    def __init__(self, trigger, *errors):
        self.trigger = trigger
        self.errors = errors


class LocksError(Exception):

    trigger: str
    errors: List[Error]

    def __init__(self, trigger, *errors):
        self.trigger = trigger
        self.errors = errors


class StatefulItem:
    __workflow_state__: Optional[str] = None


class Validator(ABC):
    """A validator.
    """
    description: str

    @abstractmethod
    def validate(self, item: StatefulItem, **namespace) -> Optional[Error]:
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

    def check_constraints(self, item, **namespace) ->  Iterable[Error]:
        """Checks the constraints against the given object.
        """
        return [validator.validate(item, **namespace)
                for validator in self.pre_validators]

    def check_locks(self, item, **namespace) -> Iterable[Error]:
        """Checks the locks against the given object.
        """
        return [validator.validate(item, **namespace)
                for validator in self.post_validators]

    def register_destination(self, action: str, state: 'State'):
        assert action not in self.destinations
        self.destinations[action] = state

    def get_reachable_states(self, item, **namespace) -> Mapping[str, str]:
        if bool(self.check_locks(item)) is False:
            return {
                state.identifer: action
                for action, state in self.destinations.items()
                if not state.check_constraints(item, **namespace)
            }
        return {}


class WorkflowMeta(type):

    def register(cls, item, state, default=False):
        assert issubclass(item, StatefulItem)

        if default:
            if not cls.default_state_identifier:
                cls.default_state_identifier = state.identifier
            else:
                raise AttributeError(
                    f'Workflow {cls} already has a default state.')

        def state_factory(workflow, item, id):
            return state

        workflow_state.register(
            state_factory, workflow=cls, item=item, id=state.identifier)


class Workflow(metaclass=WorkflowMeta):

    item: StatefulItem
    current_state: State
    default_state_identifier: ClassVar[str] = ""
    available_destinations: Mapping[str, str]

    def __init__(self, item: StatefulItem, **namespace):
        self.item = item
        self.namespace = namespace

    @property
    def current_state(self):
        if self.item.__workflow_state__:
            return self.get_state(self.item.__workflow_state__)
        return self.get_state(self.default_state_identifier)

    @property
    def available_destinations(self):
        return {action: self.get_state(id)
                for action, id in self.current_state.get_reachable_states(
                        self.item, **self.namespace)}

    def get_state(self, name) -> State:
        return workflow_state(self, self.item, name)

    def trigger_transition(self, action: str) -> None:
        current = self.current_state
        if errors := current.check_locks(self.item, **self.namespace):
            raise LocksError(action, *errors)
        destination = self.current_state.destinations.get(action)
        if destination is None:
            raise LookupError(f'Unknow trigger: {action}')
        if errors := destination.check_constraints(item, **self.namespace):
            raise ConstraintsError(action, *errors)


@reg.dispatch(
    reg.match_instance('workflow'),
    reg.match_instance('item'),
    reg.match_key('id'))
def workflow_state(workflow: Workflow, item: State, id: str):
    raise LookupError(
        f'Workflow {workflow}: unknown state {id} for object {item}')

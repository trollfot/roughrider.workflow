from collections import defaultdict
from typing import NamedTuple, Iterable, Tuple, Optional, Mapping
from dataclasses import dataclass, field
from roughrider.workflow.validation import (
    Validator, resolve_validators, ConstraintsErrors)


@dataclass
class State:
    identifier: str

    def __hash__(self):
        return hash(self.identifier)


@dataclass
class Action:

    identifier: str
    constraints: Iterable[Validator] = field(default_factory=list)

    def check_constraints(self, item, **ns) -> Optional[ConstraintsErrors]:
        """Checks the constraints against the given object.
        """
        if self.constraints:
            return resolve_validators(self.constraints, item, **ns)


class Transition(NamedTuple):
    action: Action
    origin: State
    target: State


class Transitions(Tuple[Transition]):

    _edges: Mapping[State, Mapping[State, Action]] = None

    def __new__(cls, transitions: Iterable[Transition]):
        obj = super().__new__(Transitions, transitions)
        obj._edges = defaultdict(dict)
        for trn in transitions:
            obj._edges[trn.origin][trn.target] = trn
        return obj

    def available(self, origin, item, **ns):
        for target, trn in self._edges[origin].items():
            if trn.action.check_constraints(item, **ns) is None:
                yield trn

    def find(self, origin, target):
        try:
            return self._edges[origin][target]
        except KeyError:
            raise LookupError(f'No transition from {origin} to {target}')

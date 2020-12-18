from abc import ABC, abstractmethod
from typing import Iterable, List, Tuple, Optional, Callable, Any, TypeVar


class Error(Exception):
    message: str

    def __init__(self, message):
        self.message = message

    def __eq__(self, error):
        return self.message == error.message


class ConstraintsErrors(Exception):
    errors: List[Error]

    def __init__(self, *errors):
        self.errors = list(errors)

    def __iter__(self):
        return iter(self.errors)

    def __len__(self):
        return len(self.errors)


class Validator(ABC):
    """A validator.
    """
    description: Optional[str]

    @abstractmethod
    def __call__(self, item, **namespace):
        """Validates the item.
        """


Constraint = TypeVar('Constraint', Validator,  Callable[..., None])


class OR(Tuple[Constraint], Validator):

    def __call__(self, item, **namespace):
        errors = []
        for validator in self.validators:
            try:
                validator(item, **namespace)
                return
            except Error as exc:
                errors.append(exc)
            except ConstraintsErrors as exc:
                errors.extends(exc.errors)

        raise ConstraintsErrors(*errors)


def resolve_validators(validators: Iterable[Constraint],
                       item, **namespace) -> Optional[ConstraintsErrors]:
    """Checks the validators against the given object.
    """
    errors = []
    for validator in validators:
        try:
            validator(item, **namespace)
        except Error as exc:
            errors.append(exc)
        except ConstraintsErrors as exc:
            errors.extends(exc.errors)
    if errors:
        return ConstraintsErrors(*errors)

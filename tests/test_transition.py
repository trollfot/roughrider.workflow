import pytest
from roughrider.workflow.components import Action, Transition, Transitions
from roughrider.workflow.workflow import WorkflowState
from roughrider.predicate.validators import ConstraintError


def only_test(item: str):
    if item != 'test':
        raise ConstraintError('We need a test')


class states(WorkflowState):
    foo = 'Foo'
    bar = 'Bar'


forward = Transition(
    origin=states.foo,
    target=states.bar,
    action=Action('Foobaring')
)

backward = Transition(
    origin=states.bar,
    target=states.foo,
    action=Action(
        'Barfooing',
        constraints=[only_test],
    )
)


def test_transition():
    assert forward.origin == states.foo
    assert forward.target == states.bar
    assert forward.action == Action('Foobaring')

    assert backward.origin == states.bar
    assert backward.target == states.foo
    assert backward.action == Action(
        'Barfooing',
        constraints=[only_test],
    )


def test_init_transition_faulty():

    with pytest.raises(TypeError) as exc:
        Transition()

    assert str(exc.value) == (
        "__new__() missing 3 required positional arguments: "
        "'action', 'origin', and 'target'"
    )


def test_transitions_internal_edges():

    transitions = Transitions((forward,))

    assert isinstance(transitions, tuple)
    assert isinstance(transitions._edges, dict)
    assert dict(transitions._edges) == {
        states.foo: {
            states.bar: forward
        }
    }

    transitions = Transitions((forward, backward))
    assert dict(transitions._edges) == {
        states.foo: {
            states.bar: forward
        },
        states.bar: {
            states.foo: backward
        }
    }


def test_transitions_find():

    transitions = Transitions((forward,))

    assert transitions.find(states.foo, states.bar) == forward

    with pytest.raises(LookupError) as exc:
        transitions.find(states.bar, states.foo)

    assert str(exc.value) == 'No transition from states.bar to states.foo'

    transitions = Transitions((forward, backward))
    assert transitions.find(states.foo, states.bar) == forward
    assert transitions.find(states.bar, states.foo) == backward


def test_transitions_available():

    transitions = Transitions((forward, backward))
    assert list(transitions.available(states.foo, 'test')) == [forward]
    assert list(transitions.available(states.bar, 'test')) == [backward]
    assert list(transitions.available(states.bar, 'nope')) == []

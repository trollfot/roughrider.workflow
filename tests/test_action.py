from roughrider.workflow.components import Action
from roughrider.predicate import Validator, Error, ConstraintsErrors


def test_no_constraints_action():
    action = Action(identifier='Test')
    assert action.identifier == 'Test'
    assert action.constraints == []
    assert not action.check_constraints('item')


def test_constraint_action():

    def tester(item, **namespace):
        if item != 'test':
            raise Error('This needs to be a test')

    action = Action(identifier='Test', constraints=[tester])
    assert action.identifier == 'Test'
    assert action.constraints == [tester]

    errors = action.check_constraints('not test')
    assert isinstance(errors, ConstraintsErrors)
    assert len(errors) == 1
    assert list(errors) == [Error('This needs to be a test')]

    assert not action.check_constraints('test')

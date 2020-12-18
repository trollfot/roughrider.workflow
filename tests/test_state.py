from roughrider.workflow import WorkflowState, State


def test_state():

    state = State('test')
    assert state.identifier == 'test'

    state = State(identifier='test')
    assert state.identifier == 'test'

    assert hash(state) == hash('test')


def test_workflow_states():

    class states(WorkflowState):
        foo = 'Foo'
        bar = 'Bar'

    assert isinstance(states.foo, State)
    assert isinstance(states.foo, WorkflowState)
    assert states.foo.name == 'foo'
    assert states.foo.identifier == 'Foo'

    assert states('Foo') is states.foo
    assert states(states.foo) is states.foo
    assert states['foo'] is states.foo

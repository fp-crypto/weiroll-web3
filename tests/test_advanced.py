import eth_abi
import pytest

import weiroll.client as weiroll


def test_weiroll_func_takes_and_replaces_current_state(alice, testContract):
    """Test replacing current state with a function's return value."""
    planner = weiroll.WeirollPlanner(alice)
    planner.replaceState(testContract.useState(planner.state))

    commands, state = planner.plan()

    assert len(commands) == 1
    # We don't check exact command hex as it might differ with web3.py
    assert len(state) == 0


def test_weiroll_supports_subplan(alice, math, subplanContract):
    """Test basic subplan functionality."""
    subplanner = weiroll.WeirollPlanner(alice)
    subplanner.add(math.add(1, 2))

    planner = weiroll.WeirollPlanner(alice)
    planner.addSubplan(subplanContract.execute(subplanner, subplanner.state))

    commands, state = planner.plan()

    assert len(commands) == 1
    assert len(state) == 3
    assert state[0] == eth_abi.encode(["uint256"], [1])
    assert state[1] == eth_abi.encode(["uint256"], [2])
    # The third state item should be the serialized subplan
    assert len(state[2]) > 0


def test_weiroll_subplan_allows_return_in_parent_scope(alice, math, subplanContract):
    """Test using return values from subplans in parent scope."""
    subplanner = weiroll.WeirollPlanner(alice)
    sum_value = subplanner.add(math.add(1, 2))

    planner = weiroll.WeirollPlanner(alice)
    planner.addSubplan(subplanContract.execute(subplanner, subplanner.state))
    planner.add(math.add(sum_value, 3))

    commands, _ = planner.plan()
    assert len(commands) == 2


def test_weiroll_return_values_across_scopes(alice, math, subplanContract):
    """Test return values across multiple subplan scopes."""
    subplanner1 = weiroll.WeirollPlanner(alice)
    sum_value = subplanner1.add(math.add(1, 2))

    subplanner2 = weiroll.WeirollPlanner(alice)
    subplanner2.add(math.add(sum_value, 3))

    planner = weiroll.WeirollPlanner(alice)
    planner.addSubplan(subplanContract.execute(subplanner1, subplanner1.state))
    planner.addSubplan(subplanContract.execute(subplanner2, subplanner2.state))

    commands, state = planner.plan()

    assert len(commands) == 2
    assert len(state) >= 5  # At least 5 state slots


def test_weiroll_add_subplan_needs_args(alice, math, subplanContract):
    """Test that subplans require both planner and state arguments."""
    subplanner = weiroll.WeirollPlanner(alice)
    subplanner.add(math.add(1, 2))

    planner = weiroll.WeirollPlanner(alice)

    with pytest.raises(
        ValueError, match="Subplans must take planner and state arguments"
    ):
        # Empty list instead of state
        planner.addSubplan(subplanContract.execute(subplanner, []))

    with pytest.raises(
        ValueError, match="Subplans must take planner and state arguments"
    ):
        # Empty list instead of planner
        planner.addSubplan(subplanContract.execute([], subplanner.state))


def test_weiroll_doesnt_allow_multiple_subplans_per_call(
    alice, math, multiSubplanContract
):
    """Test that a call can only have one subplan argument."""
    subplanner = weiroll.WeirollPlanner(alice)
    subplanner.add(math.add(1, 2))

    planner = weiroll.WeirollPlanner(alice)
    with pytest.raises(ValueError, match="Subplans can only take one planner argument"):
        planner.addSubplan(
            multiSubplanContract.execute(subplanner, subplanner, subplanner.state)
        )


def test_weiroll_doesnt_allow_state_array_per_call(
    alice, math, multiStateSubplanContract
):
    """Test that a call can only have one state argument."""
    subplanner = weiroll.WeirollPlanner(alice)
    subplanner.add(math.add(1, 2))

    planner = weiroll.WeirollPlanner(alice)
    with pytest.raises(ValueError, match="Subplans can only take one state argument"):
        planner.addSubplan(
            multiStateSubplanContract.execute(
                subplanner, subplanner.state, subplanner.state
            )
        )


def test_weiroll_subplan_has_correct_return_type(alice, math, badSubplanContract):
    """Test that subplans must return bytes[] or nothing."""
    subplanner = weiroll.WeirollPlanner(alice)
    subplanner.add(math.add(1, 2))

    planner = weiroll.WeirollPlanner(alice)
    with pytest.raises(
        ValueError,
        match=r"Subplans must return a bytes\[\] replacement state or nothing",
    ):
        planner.addSubplan(badSubplanContract.execute(subplanner, subplanner.state))


def test_forbid_infinite_loops(alice, subplanContract):
    """Test that a planner can't contain itself (infinite loop)."""
    planner = weiroll.WeirollPlanner(alice)
    planner.addSubplan(subplanContract.execute(planner, planner.state))

    with pytest.raises(ValueError, match="A planner cannot contain itself"):
        planner.plan()


def test_subplans_without_returns(alice, math, readonlySubplanContract):
    """Test subplans without return values."""
    subplanner = weiroll.WeirollPlanner(alice)
    subplanner.add(math.add(1, 2))

    planner = weiroll.WeirollPlanner(alice)
    planner.addSubplan(readonlySubplanContract.execute(subplanner, subplanner.state))

    commands, _ = planner.plan()
    assert len(commands) == 1


def test_read_only_subplans_requirements(alice, math, readonlySubplanContract):
    """Test that read-only subplans can't expose return values outside."""
    subplanner = weiroll.WeirollPlanner(alice)
    sum_value = subplanner.add(math.add(1, 2))

    planner = weiroll.WeirollPlanner(alice)
    planner.addSubplan(readonlySubplanContract.execute(subplanner, subplanner.state))

    # Try to use return value from subplan in parent scope
    with pytest.raises(ValueError, match="Return value from .* is not visible here"):
        planner.add(math.add(sum_value, 3))
        planner.plan()


def test_plan_call(alice, math_contract):
    """Test using the call method."""
    planner = weiroll.WeirollPlanner(alice)
    planner.call(math_contract, "add", 1, 2)
    commands, state = planner.plan()

    assert len(commands) == 1
    assert len(state) == 2
    assert state[0] == eth_abi.encode(["uint256"], [1])
    assert state[1] == eth_abi.encode(["uint256"], [2])


def test_plan_call_with_static(alice, math_contract):
    """Test using the call method with static=True."""
    planner = weiroll.WeirollPlanner(alice)
    planner.call(math_contract, "add", 1, 2, static=True)
    commands, state = planner.plan()

    assert len(commands) == 1
    assert len(state) == 2
    assert state[0] == eth_abi.encode(["uint256"], [1])
    assert state[1] == eth_abi.encode(["uint256"], [2])


def test_plan_call_with_value(alice, math_contract):
    """Test using the call method with value parameter."""
    planner = weiroll.WeirollPlanner(alice)
    planner.call(math_contract, "add", 3, 4, value=1)
    commands, state = planner.plan()

    assert len(commands) == 1
    assert len(state) == 3
    assert state[0] == eth_abi.encode(["uint256"], [1])
    assert state[1] == eth_abi.encode(["uint256"], [3])
    assert state[2] == eth_abi.encode(["uint256"], [4])


def test_plan_call_with_static_and_value(alice, math_contract):
    """Test that static and value parameters can't be combined."""
    planner = weiroll.WeirollPlanner(alice)
    with pytest.raises(ValueError, match="Cannot combine value and static"):
        planner.call(math_contract, "add", 1, 2, static=True, value=1)


def test_plan_call_with_raw_value(alice, math_contract):
    """Test using the call method with raw=True."""
    planner = weiroll.WeirollPlanner(alice)
    planner.call(math_contract, "add", 1, 2, raw=True)
    commands, state = planner.plan()

    assert len(commands) == 1
    assert len(state) == 2
    assert state[0] == eth_abi.encode(["uint256"], [1])
    assert state[1] == eth_abi.encode(["uint256"], [2])

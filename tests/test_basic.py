import pytest
import eth_abi.abi as eth_abi
from hexbytes import HexBytes
from web3 import Web3

import weiroll.client as weiroll
from weiroll.utils import eth_abi_encode_single


def test_web3_connection(web3):
    """Test basic connection to Anvil node."""
    assert web3.is_connected()
    assert len(web3.eth.accounts) > 0


def test_contract_deployment(math_contract):
    """Test that contracts can be deployed."""
    assert math_contract.address is not None
    assert Web3.is_address(math_contract.address)

    # Print contract details
    print("Math contract:", math_contract)
    print("Math contract dir:", dir(math_contract))
    print("Math functions:", dir(math_contract.functions))
    print("Math functions.add:", dir(math_contract.functions.add))

    # Call a function to ensure the contract works
    result = math_contract.functions.add(1, 2).call()
    assert result == 3


def test_weiroll_contract_wrapping(math):
    """Test WeirollContract wrapping."""
    # Check that it has the expected methods
    assert hasattr(math, "add")

    # Check function call creation
    result = math.add(1, 2)

    # Verify the function call object
    assert result.contract == math
    assert result.fragment.name == "add"
    assert result.fragment.inputs == ["uint256", "uint256"]
    assert result.fragment.outputs == ["uint256"]
    assert result.fragment.signature == "0x771602f7"
    assert result.callvalue is None
    assert result.flags == weiroll.CommandFlags.DELEGATECALL

    # Check arguments
    args = result.args
    assert len(args) == 2
    assert args[0].param == "uint256"
    assert args[0].value == eth_abi.encode(["uint256"], [1])
    assert args[1].param == "uint256"
    assert args[1].value == eth_abi.encode(["uint256"], [2])


def test_weiroll_planner_basic(alice, math):
    """Test basic planner functionality."""
    planner = weiroll.WeirollPlanner(alice)
    result = planner.add(math.add(1, 2))

    assert len(planner.commands) == 1
    assert result.param == "uint256"

    command = planner.commands[0]
    assert command.call.fragment.name == "add"
    assert command.type == weiroll.CommandType.CALL


def test_weiroll_planner_simple_program(alice, math):
    """Test generating a simple plan."""
    planner = weiroll.WeirollPlanner(alice)
    planner.add(math.add(1, 2))

    commands, state = planner.plan()

    assert len(commands) == 1
    assert len(state) == 2
    assert state[0] == eth_abi.encode(["uint256"], [1])
    assert state[1] == eth_abi.encode(["uint256"], [2])


def test_weiroll_planner_multi_commands(alice, math):
    """Test generating a plan with multiple commands."""
    planner = weiroll.WeirollPlanner(alice)
    sum1 = planner.add(math.add(1, 2))
    sum2 = planner.add(math.add(3, 4))
    planner.add(math.add(sum1, sum2))

    commands, state = planner.plan()

    # Verify the plan has the right commands
    assert len(commands) == 3
    assert len(state) >= 4  # At least inputs plus output slots


def test_weiroll_return_values(alice, math):
    """Test using return values between commands."""
    planner = weiroll.WeirollPlanner(alice)

    # Add numbers and capture return value
    sum1 = planner.add(math.add(5, 7))

    # Use the return value in another operation
    result = planner.add(math.mul(sum1, 2))

    # Create and execute the plan
    commands, state = planner.plan()

    # Verify we have the right number of commands
    assert len(commands) == 2
    assert isinstance(sum1, weiroll.ReturnValue)
    assert isinstance(result, weiroll.ReturnValue)

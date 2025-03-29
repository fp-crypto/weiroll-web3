import pytest
from web3 import Web3
from weiroll.client import WeirollContract, WeirollPlanner
from tests.integration.conftest import (
    convert_to_wei,
    impersonate_account,
    stop_impersonating,
    send_contract_tx,
)


def test_curve_add_liquidity(
    weiroll_vm,
    mainnet_fork_web3,
    setup_accounts,
    whale_account,
    token_dai,
    curve_pool,
    three_crv,
):
    # Use whale account
    whale = whale_account
    dev = setup_accounts

    # Check if whale has DAI balance
    dai_balance = token_dai.functions.balanceOf(whale).call()
    if dai_balance < convert_to_wei(10):
        pytest.skip(f"Whale does not have enough DAI: {dai_balance}")

    # Check initial state
    initial_3crv = three_crv.functions.balanceOf(whale).call()

    try:
        # Impersonate whale account
        impersonate_account(
            mainnet_fork_web3, whale, fund_amount=convert_to_wei(1), dev_account=dev
        )

        # Regular way - approve and add liquidity
        # Approve DAI for Curve pool
        send_contract_tx(
            mainnet_fork_web3,
            token_dai.functions.approve(curve_pool.address, 2**256 - 1),
            whale,
        )

        # Add liquidity to Curve pool
        send_contract_tx(
            mainnet_fork_web3,
            curve_pool.functions.add_liquidity([convert_to_wei(10), 0, 0], 0),
            whale,
            gas=3000000,
        )

        # Verify we got 3CRV tokens
        assert three_crv.functions.balanceOf(whale).call() > initial_3crv

        # Send DAI to the weiroll VM contract
        send_contract_tx(
            mainnet_fork_web3,
            token_dai.functions.transfer(weiroll_vm.address, convert_to_wei(10)),
            whale,
        )

        # Weiroll version
        planner = WeirollPlanner(weiroll_vm)

        w_dai = WeirollContract.createContract(token_dai)
        w_curve_pool = WeirollContract.createContract(curve_pool)

        planner.add(w_dai.approve(w_curve_pool.address, 2**256 - 1))
        w_dai_balance = planner.add(w_dai.balanceOf(weiroll_vm.address))
        planner.add(w_curve_pool.add_liquidity([w_dai_balance, 0, 0], 0))

        cmds, state = planner.plan()

        # Execute weiroll commands
        send_contract_tx(
            mainnet_fork_web3,
            weiroll_vm.functions.execute(cmds, state),
            whale,
            gas=3000000,
        )

        # Verify results
        assert three_crv.functions.balanceOf(weiroll_vm.address).call() > 0

    except Exception as e:
        pytest.fail(f"Error during test: {str(e)}")

    finally:
        # Always stop impersonating when done
        stop_impersonating(mainnet_fork_web3, whale)


def test_curve_add_liquidity_with_call(
    weiroll_vm,
    mainnet_fork_web3,
    setup_accounts,
    whale_account,
    token_dai,
    curve_pool,
    three_crv,
):
    # Use whale account
    whale = whale_account
    dev = setup_accounts

    # Check if whale has DAI balance
    dai_balance = token_dai.functions.balanceOf(whale).call()
    if dai_balance < convert_to_wei(10):
        pytest.skip(f"Whale does not have enough DAI: {dai_balance}")

    try:
        # Impersonate whale account
        impersonate_account(
            mainnet_fork_web3, whale, fund_amount=convert_to_wei(1), dev_account=dev
        )

        # Send DAI to the weiroll VM contract
        send_contract_tx(
            mainnet_fork_web3,
            token_dai.functions.transfer(weiroll_vm.address, convert_to_wei(10)),
            whale,
        )

        # Weiroll version using call method
        planner = WeirollPlanner(weiroll_vm)

        w_dai = WeirollContract.createContract(token_dai)
        w_curve_pool = WeirollContract.createContract(curve_pool)

        # Get DAI balance
        dai_balance = token_dai.functions.balanceOf(weiroll_vm.address).call()

        planner.add(w_dai.approve(w_curve_pool.address, 2**256 - 1))
        planner.call(curve_pool, "add_liquidity", [dai_balance, 0, 0], 0)

        cmds, state = planner.plan()

        # Execute weiroll commands
        send_contract_tx(
            mainnet_fork_web3,
            weiroll_vm.functions.execute(cmds, state),
            whale,
            gas=3000000,
        )

        # Verify results
        assert three_crv.functions.balanceOf(weiroll_vm.address).call() > 0

    except Exception as e:
        pytest.fail(f"Error during test: {str(e)}")

    finally:
        # Always stop impersonating when done
        stop_impersonating(mainnet_fork_web3, whale)


# Utility function to convert ether to wei (duplicated for backward compatibility)
def convert_to_wei(amount_in_ether):
    """Convert ether to wei"""
    return Web3.to_wei(amount_in_ether, "ether")

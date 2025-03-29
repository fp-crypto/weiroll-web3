import os
import pytest
import requests
from web3 import Web3
from typing import Dict, Any

from weiroll.client import WeirollPlanner, WeirollContract, ReturnValue
from tests.integration.conftest import (
    impersonate_account,
    stop_impersonating,
    send_contract_tx,
)

ONE_INCH_API_KEY = os.environ.get("ONE_INCH_API_KEY")


# @pytest.mark.skipif(ONE_INCH_API_KEY is None, reason="Need 1inch api key")
@pytest.mark.skip()
def test_chaining_action(mainnet_fork_web3, weiroll_vm, tuple_helper):
    # Whale account with ETH, WETH, etc.
    whale_address = "0x57757E3D981446D585Af0D9Ae4d7DF6D64647806"

    # Impersonate the whale account
    whale = impersonate_account(
        mainnet_fork_web3, whale_address, fund_amount=Web3.to_wei(1, "ether")
    )

    try:
        # Setup token and contract addresses
        weth_address = Web3.to_checksum_address(
            "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
        )
        yfi_address = Web3.to_checksum_address(
            "0x0bc529c00C6401aEF6D220BE8C6Ea1667F6Ad93e"
        )
        crv_yfi_weth_address = Web3.to_checksum_address(
            "0x29059568bB40344487d62f7450E78b8E6C74e0e5"
        )
        curve_swap_address = Web3.to_checksum_address(
            "0xC26b89A667578ec7b3f11b2F98d6Fd15C07C54ba"
        )

        # Get ERC20 ABI for token interactions
        erc20_abi = [
            {
                "constant": True,
                "inputs": [{"name": "_owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "balance", "type": "uint256"}],
                "payable": False,
                "type": "function",
            },
            {
                "constant": False,
                "inputs": [
                    {"name": "_to", "type": "address"},
                    {"name": "_value", "type": "uint256"},
                ],
                "name": "transfer",
                "outputs": [{"name": "success", "type": "bool"}],
                "payable": False,
                "type": "function",
            },
            {
                "constant": False,
                "inputs": [
                    {"name": "_spender", "type": "address"},
                    {"name": "_value", "type": "uint256"},
                ],
                "name": "approve",
                "outputs": [{"name": "success", "type": "bool"}],
                "payable": False,
                "type": "function",
            },
        ]

        # Create Web3 contract instances
        weth = mainnet_fork_web3.eth.contract(address=weth_address, abi=erc20_abi)
        yfi = mainnet_fork_web3.eth.contract(address=yfi_address, abi=erc20_abi)
        crv_yfi_weth = mainnet_fork_web3.eth.contract(
            address=crv_yfi_weth_address, abi=erc20_abi
        )

        # Curve swap ABI
        curve_swap_abi = [
            {
                "name": "add_liquidity",
                "outputs": [{"type": "uint256", "name": ""}],
                "inputs": [
                    {"type": "uint256[2]", "name": "amounts"},
                    {"type": "uint256", "name": "min_mint_amount"},
                ],
                "stateMutability": "nonpayable",
                "type": "function",
            }
        ]
        curve_swap = mainnet_fork_web3.eth.contract(
            address=curve_swap_address, abi=curve_swap_abi
        )

        # Check initial setup
        assert weth.functions.balanceOf(weiroll_vm.address).call() == 0
        assert yfi.functions.balanceOf(weiroll_vm.address).call() == 0
        assert crv_yfi_weth.functions.balanceOf(weiroll_vm.address).call() == 0

        # Transfer 10 ETH to the weiroll VM to start the process
        send_contract_tx(
            mainnet_fork_web3,
            weth.functions.transfer(weiroll_vm.address, Web3.to_wei(10, "ether")),
            whale,
        )

        # Setup Weiroll planner and contracts
        planner = WeirollPlanner(weiroll_vm)
        w_weth = WeirollContract.createContract(weth)
        w_yfi = WeirollContract.createContract(yfi)
        w_tuple_helper = WeirollContract.createContract(tuple_helper)
        w_curve_swap = WeirollContract.createContract(curve_swap)
        w_crv_yfi_weth = WeirollContract.createContract(crv_yfi_weth)

        # Get 1inch swap data for WETH -> YFI
        swap_url = f"https://api.1inch.dev/swap/v5.2/1/swap"
        headers = {"Authorization": f"Bearer {ONE_INCH_API_KEY}"}
        response = requests.get(
            swap_url,
            params={
                "fromTokenAddress": weth_address,
                "toTokenAddress": yfi_address,
                "amount": Web3.to_wei(5, "ether"),
                "fromAddress": weiroll_vm.address,
                "slippage": 5,
                "disableEstimate": "true",
                "allowPartialFill": "false",
            },
            headers=headers,
        )

        assert (
            response.ok and response.status_code == 200
        ), f"1inch API error: {response.text}"
        tx_data = response.json()["tx"]

        # Get the 1inch router address and create a contract instance
        one_inch_address = Web3.to_checksum_address(tx_data["to"])

        # Create a dummy ABI for 1inch router with a function that returns a tuple
        # We'll extract the actual calldata from the 1inch API
        one_inch_abi = [
            {
                "inputs": [
                    {"internalType": "address", "name": "caller", "type": "address"}
                ],
                "name": "swap",
                "outputs": [
                    {
                        "internalType": "uint256",
                        "name": "returnAmount",
                        "type": "uint256",
                    },
                    {
                        "internalType": "uint256",
                        "name": "spentAmount",
                        "type": "uint256",
                    },
                ],
                "stateMutability": "nonpayable",
                "type": "function",
            }
        ]
        one_inch = mainnet_fork_web3.eth.contract(
            address=one_inch_address, abi=one_inch_abi
        )
        w_one_inch = WeirollContract.createContract(one_inch)

        # Get transaction data and parameters from 1inch
        tx_data_bytes = Web3.to_bytes(hexstr=tx_data["data"])
        function_signature = tx_data_bytes[:4].hex()

        # Add WETH approval for 1inch router
        planner.add(w_weth.approve(one_inch_address, 2**256 - 1))

        # Add the 1inch swap and extract return value (tuple)
        # Since we can't easily decode the exact parameters, we'll use a raw call
        # and extract the first element of the return tuple (the YFI amount)
        one_inch_ret = planner.addRawCall(one_inch_address, 0, tx_data_bytes, True)

        # Extract the YFI amount from the returned tuple
        one_inch_amount = planner.add(w_tuple_helper.getElement(one_inch_ret, 0))
        yfi_int_amount = ReturnValue("uint256", one_inch_amount.command)

        # Add approvals for Curve
        planner.add(w_weth.approve(curve_swap_address, 2**256 - 1))
        planner.add(w_yfi.approve(curve_swap_address, 2**256 - 1))

        # Add liquidity to Curve
        curve_ret = planner.add(
            w_curve_swap.add_liquidity([Web3.to_wei(5, "ether"), yfi_int_amount], 0)
        )

        # Transfer the LP tokens to the tuple helper contract
        planner.add(w_crv_yfi_weth.transfer(tuple_helper.address, curve_ret))

        # Execute the plan
        cmds, state = planner.plan()
        tx_hash = weiroll_vm.execute(cmds, state, {"from": whale})
        receipt = mainnet_fork_web3.eth.wait_for_transaction_receipt(tx_hash)

        # Verify that tuple_helper received the Curve LP tokens
        lp_balance = crv_yfi_weth.functions.balanceOf(tuple_helper.address).call()
        assert lp_balance > 0, "No Curve LP tokens received"

    finally:
        # Always stop impersonating
        stop_impersonating(mainnet_fork_web3, whale)

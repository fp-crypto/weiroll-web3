import os
import pytest
import requests
from web3 import Web3

from weiroll.client import WeirollPlanner, WeirollContract
from tests.integration.conftest import (
    impersonate_account,
    stop_impersonating,
    send_contract_tx,
)

ONE_INCH_API_KEY = os.environ.get("ONE_INCH_API_KEY")


# @pytest.mark.skipif(ONE_INCH_API_KEY is None, reason="Need 1inch api key")
@pytest.mark.skip()
def test_one_inch(mainnet_fork_web3, weiroll_vm):
    # Whale account with ETH
    whale_address = "0x57757E3D981446D585Af0D9Ae4d7DF6D64647806"

    # Impersonate the whale account
    whale = impersonate_account(
        mainnet_fork_web3, whale_address, fund_amount=Web3.to_wei(1, "ether")
    )

    try:
        # Setup token contracts
        weth_address = Web3.to_checksum_address(
            "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
        )
        crv_address = Web3.to_checksum_address(
            "0xD533a949740bb3306d119CC777fa900bA034cd52"
        )

        # Get ERC20 ABI for the token interactions
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
        crv = mainnet_fork_web3.eth.contract(address=crv_address, abi=erc20_abi)

        # Transfer WETH to weiroll VM
        amount_to_swap = Web3.to_wei(10, "ether")
        send_contract_tx(
            mainnet_fork_web3,
            weth.functions.transfer(weiroll_vm.address, amount_to_swap),
            whale,
        )

        # Get 1inch swap data
        swap_url = "https://api.1inch.dev/swap/v5.2/1/swap"
        headers = {"Authorization": f"Bearer {ONE_INCH_API_KEY}"}
        response = requests.get(
            swap_url,
            params={
                "fromTokenAddress": weth_address,
                "toTokenAddress": crv_address,
                "amount": amount_to_swap,
                "fromAddress": weiroll_vm.address,
                "slippage": 5,
                "disableEstimate": "true",
                "allowPartialFill": "false",
            },
            headers=headers,
        )

        assert response.ok and response.status_code == 200, (
            f"1inch API error: {response.text}"
        )
        tx_data = response.json()["tx"]

        # Get the 1inch router address and create a contract instance
        one_inch_address = Web3.to_checksum_address(tx_data["to"])

        # Create a minimal ABI for interacting with 1inch router
        one_inch_abi = [
            {
                "inputs": [],
                "name": "execute",
                "outputs": [],
                "stateMutability": "payable",
                "type": "function",
            }
        ]
        one_inch = mainnet_fork_web3.eth.contract(
            address=one_inch_address, abi=one_inch_abi
        )

        # Get the transaction data
        tx_data_bytes = Web3.to_bytes(hexstr=tx_data["data"])

        # Weiroll planning
        planner = WeirollPlanner(weiroll_vm)

        # Create WeirollContract instances
        w_weth = WeirollContract.createContract(weth)
        w_one_inch = WeirollContract.createContract(one_inch)

        # Approve 1inch router to spend WETH
        planner.add(w_weth.approve(one_inch_address, 2**256 - 1))

        # Since we're executing an arbitrary transaction, use the low-level call functionality
        # Extract the function signature and parameters
        function_signature = tx_data_bytes[:4]
        parameters = tx_data_bytes[4:]

        # Add the call to the planner
        # This uses the raw calldata from the 1inch API
        planner.addRawCall(one_inch_address, 0, tx_data_bytes)

        # Execute the plan
        cmds, state = planner.plan()
        tx_hash = weiroll_vm.execute(cmds, state, {"from": whale})
        receipt = mainnet_fork_web3.eth.wait_for_transaction_receipt(tx_hash)

        # Verify that we received CRV tokens
        crv_balance = crv.functions.balanceOf(weiroll_vm.address).call()
        assert crv_balance > 0, "No CRV tokens received"

    finally:
        # Always stop impersonating
        stop_impersonating(mainnet_fork_web3, whale)

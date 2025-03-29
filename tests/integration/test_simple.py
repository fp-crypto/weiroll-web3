import pytest
from web3 import Web3
import json


def test_simple_dai_balance(mainnet_fork_web3):
    """
    A simple test to check if we can connect to the mainnet fork
    and query a known token contract.
    """
    # Set up DAI token contract
    dai_address = Web3.to_checksum_address("0x6B175474E89094C44Da98b954EedeAC495271d0F")

    # Define a simple ERC20 ABI with just balanceOf
    erc20_abi = json.loads("""[
        {"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"}
    ]""")

    # Create the contract instance
    dai_contract = mainnet_fork_web3.eth.contract(address=dai_address, abi=erc20_abi)

    # Check Compound whale's DAI balance
    whale_address = Web3.to_checksum_address(
        "0x5d3a536E4D6DbD6114cc1Ead35777bAB948E3643"
    )

    # Query balance
    try:
        dai_balance = dai_contract.functions.balanceOf(whale_address).call()
        print(f"DAI balance of whale: {dai_balance}")

        # Just make sure the balance is a number, we can't guarantee any specific value
        assert isinstance(dai_balance, int)

    except Exception as e:
        pytest.fail(f"Failed to query DAI balance: {str(e)}")

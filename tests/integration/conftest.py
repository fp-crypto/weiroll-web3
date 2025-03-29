import os
import pytest
import json
import functools
from pathlib import Path
from web3 import Web3
from typing import Callable, Any, Dict, Optional, Union

# Import common test fixtures but not the weiroll_vm which depends on TestableVM
from tests.conftest import (
    get_web3, load_contract_data, alice, deploy_contract, 
    math_contract, math, strings_contract, strings
)

@pytest.fixture(scope="session")
def mainnet_fork_web3():
    """
    Connect to a forked Ethereum mainnet instance (Anvil).
    
    This fixture requires that Anvil is running with:
    yarn anvil --fork-url $ETH_RPC_URL
    """
    fork_url = os.environ.get("ANVIL_RPC_URL", "http://127.0.0.1:8545")
    w3 = Web3(Web3.HTTPProvider(fork_url))
    
    if not w3.is_connected():
        pytest.skip("Anvil fork not available. Run 'yarn anvil' first.")
    
    return w3

@pytest.fixture(scope="module")
def weiroll_vm(deploy_contract):
    """TestableVM contract instance."""
    return deploy_contract("TestableVM", "test") 
    
@pytest.fixture(scope="module")
def setup_accounts(mainnet_fork_web3):
    """
    Set up test accounts with ETH for transactions.
    Provides a dev account (with ETH) and returns it.
    """
    # Get the default account from Anvil (has plenty of ETH)
    dev_account = mainnet_fork_web3.eth.accounts[0]
    
    # Set it as the default account for all transactions
    mainnet_fork_web3.eth.default_account = dev_account
    
    # Return the funded account
    return dev_account

@pytest.fixture(scope="module")
def whale_account(mainnet_fork_web3, setup_accounts):
    """A known account with DAI balance for tests.
    
    In Anvil fork mode, this account will be accessible without private keys.
    The account will be funded with ETH for gas fees.
    """
    dev_account = setup_accounts
    
    # Try different known DAI whale addresses
    whale_addresses = [
        "0x5d3a536E4D6DbD6114cc1Ead35777bAB948E3643",  # Compound: cDAI
        "0x47ac0Fb4F2D84898e4D9E7b4DaB3C24507a6D503",  # Binance
        "0x28C6c06298d514Db089934071355E5743bf21d60",  # Binance 14
        "0xBE0eB53F46cd790Cd13851d5EFf43D12404d33E8",  # Binance 7
        "0x075e72a5edf65f0a5f44699c7654c1a76941ddc8",  # Maker: PSM
        "0x50D1c9771902476076eCFc8B2A83Ad6b9355a4c9"   # FTX
    ]
    
    # Try each whale address until we find one with DAI
    for raw_address in whale_addresses:
        whale = Web3.to_checksum_address(raw_address)
        
        try:
            # Load DAI token contract to check balance
            dai_address = Web3.to_checksum_address("0x6B175474E89094C44Da98b954EedeAC495271d0F")
            dai_abi = json.loads('''[
                {"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"}
            ]''')
            dai_contract = mainnet_fork_web3.eth.contract(address=dai_address, abi=dai_abi)
            
            # Check if whale has DAI
            dai_balance = dai_contract.functions.balanceOf(whale).call()
            
            # We need at least 30 DAI (10 for each test)
            min_required = Web3.to_wei(30, 'ether')
            
            if dai_balance >= min_required:
                print(f"Found DAI whale: {whale} with {Web3.from_wei(dai_balance, 'ether')} DAI")
                
                # Impersonate the whale account
                mainnet_fork_web3.provider.make_request("anvil_impersonateAccount", [whale])
                
                # Fund the whale with ETH (10 ETH should be plenty)
                tx_hash = mainnet_fork_web3.eth.send_transaction({
                    'from': dev_account,
                    'to': whale,
                    'value': Web3.to_wei(10, 'ether')
                })
                mainnet_fork_web3.eth.wait_for_transaction_receipt(tx_hash)
                
                # Stop impersonating for now (tests will impersonate again when needed)
                mainnet_fork_web3.provider.make_request("anvil_stopImpersonatingAccount", [whale])
                
                return whale
        except Exception as e:
            print(f"Error with whale {whale}: {str(e)}")
            continue
    
    # If we get here, none of the whales had enough DAI
    pytest.skip("Could not find a whale with enough DAI")
    return None
    
@pytest.fixture(scope="module")
def token_dai(mainnet_fork_web3):
    """DAI token contract"""
    raw_address = "0x6B175474E89094C44Da98b954EedeAC495271d0F"
    dai_address = Web3.to_checksum_address(raw_address)
    # Load a standard ERC20 ABI
    erc20_abi = json.loads('''[
        {"constant":true,"inputs":[],"name":"name","outputs":[{"name":"","type":"string"}],"payable":false,"stateMutability":"view","type":"function"},
        {"constant":false,"inputs":[{"name":"_spender","type":"address"},{"name":"_value","type":"uint256"}],"name":"approve","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"},
        {"constant":true,"inputs":[],"name":"totalSupply","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},
        {"constant":false,"inputs":[{"name":"_from","type":"address"},{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transferFrom","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"},
        {"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"payable":false,"stateMutability":"view","type":"function"},
        {"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},
        {"constant":true,"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string"}],"payable":false,"stateMutability":"view","type":"function"},
        {"constant":false,"inputs":[{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transfer","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"},
        {"constant":true,"inputs":[{"name":"_owner","type":"address"},{"name":"_spender","type":"address"}],"name":"allowance","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},
        {"anonymous":false,"inputs":[{"indexed":true,"name":"owner","type":"address"},{"indexed":true,"name":"spender","type":"address"},{"indexed":false,"name":"value","type":"uint256"}],"name":"Approval","type":"event"},
        {"anonymous":false,"inputs":[{"indexed":true,"name":"from","type":"address"},{"indexed":true,"name":"to","type":"address"},{"indexed":false,"name":"value","type":"uint256"}],"name":"Transfer","type":"event"}
    ]''')
    return mainnet_fork_web3.eth.contract(address=dai_address, abi=erc20_abi)

@pytest.fixture(scope="module")
def curve_pool(mainnet_fork_web3):
    """Curve 3pool contract"""
    raw_address = "0xbebc44782c7db0a1a60cb6fe97d0b483032ff1c7"
    pool_address = Web3.to_checksum_address(raw_address)
    # Simplified ABI for the Curve pool with only the functions we need
    pool_abi = json.loads('''[
        {"name":"add_liquidity","outputs":[{"type":"uint256","name":""}],"inputs":[{"type":"uint256[3]","name":"amounts"},{"type":"uint256","name":"min_mint_amount"}],"stateMutability":"nonpayable","type":"function"},
        {"name":"remove_liquidity","outputs":[],"inputs":[{"type":"uint256","name":"_amount"},{"type":"uint256[3]","name":"min_amounts"}],"stateMutability":"nonpayable","type":"function"}
    ]''')
    return mainnet_fork_web3.eth.contract(address=pool_address, abi=pool_abi)

@pytest.fixture(scope="module")
def three_crv(mainnet_fork_web3):
    """3CRV token contract"""
    raw_address = "0x6c3F90f043a72FA612cbac8115EE7e52BDe6E490"
    token_address = Web3.to_checksum_address(raw_address)
    # Using standard ERC20 ABI
    erc20_abi = json.loads('''[
        {"constant":true,"inputs":[],"name":"name","outputs":[{"name":"","type":"string"}],"payable":false,"stateMutability":"view","type":"function"},
        {"constant":false,"inputs":[{"name":"_spender","type":"address"},{"name":"_value","type":"uint256"}],"name":"approve","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"},
        {"constant":true,"inputs":[],"name":"totalSupply","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},
        {"constant":false,"inputs":[{"name":"_from","type":"address"},{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transferFrom","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"},
        {"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"payable":false,"stateMutability":"view","type":"function"},
        {"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},
        {"constant":true,"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string"}],"payable":false,"stateMutability":"view","type":"function"},
        {"constant":false,"inputs":[{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transfer","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"},
        {"constant":true,"inputs":[{"name":"_owner","type":"address"},{"name":"_spender","type":"address"}],"name":"allowance","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},
        {"anonymous":false,"inputs":[{"indexed":true,"name":"owner","type":"address"},{"indexed":true,"name":"spender","type":"address"},{"indexed":false,"name":"value","type":"uint256"}],"name":"Approval","type":"event"},
        {"anonymous":false,"inputs":[{"indexed":true,"name":"from","type":"address"},{"indexed":true,"name":"to","type":"address"},{"indexed":false,"name":"value","type":"uint256"}],"name":"Transfer","type":"event"}
    ]''')
    return mainnet_fork_web3.eth.contract(address=token_address, abi=erc20_abi)

# Helper functions
def convert_to_wei(amount_in_ether):
    """Convert ether to wei"""
    return Web3.to_wei(amount_in_ether, 'ether')


def impersonate_account(web3: Web3, account: str, fund_amount: Optional[int] = None, dev_account: Optional[str] = None):
    """
    Impersonates a given account in Anvil and optionally funds it with ETH.
    
    Args:
        web3: Web3 instance
        account: Address to impersonate
        fund_amount: Amount of ETH to fund (in wei), if any
        dev_account: Account to use for funding, defaults to first account
        
    Returns:
        The impersonated account address
    """
    # Convert to checksum address
    impersonated = Web3.to_checksum_address(account)
    
    # If dev account not specified, use the first account
    if dev_account is None:
        dev_account = web3.eth.accounts[0]
    
    # Impersonate the account
    web3.provider.make_request("anvil_impersonateAccount", [impersonated])
    
    # Fund the account if requested
    if fund_amount is not None and fund_amount > 0:
        tx_hash = web3.eth.send_transaction({
            'from': dev_account,
            'to': impersonated,
            'value': fund_amount
        })
        web3.eth.wait_for_transaction_receipt(tx_hash)
    
    return impersonated


def stop_impersonating(web3: Web3, account: str):
    """
    Stops impersonating an account in Anvil.
    
    Args:
        web3: Web3 instance
        account: Address to stop impersonating
    """
    try:
        web3.provider.make_request("anvil_stopImpersonatingAccount", [account])
    except Exception as e:
        # Log but don't fail if there's an issue with stopping impersonation
        print(f"Warning: Failed to stop impersonating {account}: {str(e)}")


def impersonated_tx(web3: Web3, account: str, gas_price: int = None):
    """
    Returns a decorator that wraps a function to execute with an impersonated account.
    The decorated function will receive the impersonated account address and Web3 object
    as its first arguments, followed by any other arguments passed to it.
    
    Args:
        web3: Web3 instance to use
        account: Address to impersonate
        gas_price: Gas price to use for transactions, defaults to 1 gwei
        
    Returns:
        A decorator that ensures the account is impersonated during function execution
    """
    # Use a low gas price if not specified
    if gas_price is None:
        gas_price = Web3.to_wei(1, 'gwei')
    
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Impersonate the account
            impersonated = impersonate_account(web3, account)
            
            try:
                # Call the wrapped function with the impersonated account
                return func(impersonated, web3, *args, **kwargs)
            finally:
                # Always stop impersonating when done
                stop_impersonating(web3, impersonated)
        return wrapper
    return decorator


def send_contract_tx(
    web3: Web3,
    contract_func,
    from_address: str,
    gas: int = 500000,
    gas_price: Optional[int] = None,
    value: int = 0,
    nonce: Optional[int] = None,
    **tx_params
) -> str:
    """
    Helper function to build and send a contract transaction.
    
    Args:
        web3: Web3 instance
        contract_func: Contract function object (e.g., token.functions.transfer(...))
        from_address: Address to send transaction from
        gas: Gas limit
        gas_price: Gas price (defaults to 1 gwei if None)
        value: ETH value to send
        nonce: Transaction nonce (defaults to next nonce if None)
        **tx_params: Additional transaction parameters
        
    Returns:
        Transaction hash
    """
    # Set default gas price if not provided
    if gas_price is None:
        gas_price = Web3.to_wei(1, 'gwei')
    
    # Use next nonce if not provided
    if nonce is None:
        nonce = web3.eth.get_transaction_count(from_address)
    
    # Build the transaction
    tx = contract_func.build_transaction({
        'from': from_address,
        'gas': gas,
        'gasPrice': gas_price,
        'value': value,
        'nonce': nonce,
        **tx_params
    })
    
    # Send the transaction
    tx_hash = web3.eth.send_transaction(tx)
    
    # Wait for the transaction to be mined
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
    
    # Check for transaction failure
    if receipt.status == 0:
        raise Exception(f"Transaction failed: {tx_hash.hex()}")
    
    return tx_hash
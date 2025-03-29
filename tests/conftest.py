import json
import os
import pytest
from pathlib import Path
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware as geth_poa_middleware

from weiroll.client import WeirollContract


def get_web3():
    """
    Connect to local Anvil instance.
    
    By default, connects to localhost:8545, which is the default port for Anvil.
    """
    # Get RPC URL from environment variable or use default local Anvil address
    rpc_url = os.environ.get("ANVIL_RPC_URL", "http://127.0.0.1:8545")
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    
    # Apply middleware for POA chains (needed for some networks)
    w3.middleware_onion.inject(geth_poa_middleware, layer=0)
    
    return w3


def load_contract_data(contract_name, category=None):
    """
    Load contract ABI and bytecode from the compiled output.
    
    Args:
        contract_name: Contract name (e.g., "Math", "TestableVM")
        category: Optional category (e.g., "Libraries", "test")
        
    Returns:
        tuple: (abi, bytecode)
    """
    # Base directory for contract artifacts
    base_dir = Path(__file__).parent.parent / "build" / "contracts"
    
    # Path to the appropriate combined.json file
    if category:
        json_file = base_dir / category / "combined.json"
    else:
        json_file = base_dir / "combined.json"
    
    if not json_file.exists():
        raise FileNotFoundError(f"Could not find compiled contract data at {json_file}")
    
    # Load the combined JSON file
    with open(json_file) as f:
        combined_data = json.load(f)
    
    # Find the contract in the combined output
    contract_key = None
    for key in combined_data["contracts"].keys():
        if key.endswith(f":{contract_name}"):
            contract_key = key
            break
    
    if not contract_key:
        raise ValueError(f"Contract {contract_name} not found in {json_file}")
    
    # Extract ABI and bytecode
    contract_data = combined_data["contracts"][contract_key]
    # Check if ABI is already a list or needs to be parsed from JSON string
    if isinstance(contract_data["abi"], str):
        abi = json.loads(contract_data["abi"])
    else:
        abi = contract_data["abi"]
    bytecode = "0x" + contract_data["bin"]
    
    return abi, bytecode


@pytest.fixture(scope="session")
def web3():
    """Web3 connection to the Anvil instance."""
    w3 = get_web3()
    if not w3.is_connected():
        pytest.skip("Could not connect to Anvil node. Make sure it's running with 'yarn anvil'")
    return w3


@pytest.fixture(scope="session")
def alice(web3):
    """First account from the Anvil node."""
    return web3.eth.accounts[0]


@pytest.fixture(scope="module")
def deploy_contract(web3, alice):
    """Factory fixture to deploy contracts."""
    
    def _deploy_contract(contract_name, category=None):
        abi, bytecode = load_contract_data(contract_name, category)
        contract = web3.eth.contract(abi=abi, bytecode=bytecode)
        tx_hash = contract.constructor().transact({"from": alice})
        tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
        return web3.eth.contract(address=tx_receipt.contractAddress, abi=abi)
    
    return _deploy_contract


@pytest.fixture(scope="module")
def weiroll_vm(deploy_contract):
    """TestableVM contract instance."""
    return deploy_contract("TestableVM")


@pytest.fixture(scope="module")
def math_contract(deploy_contract):
    """Math contract instance (raw web3 contract)."""
    return deploy_contract("Math", "Libraries")


@pytest.fixture(scope="module")
def math(math_contract):
    """Math contract wrapped with WeirollContract."""
    # Print available functions for debugging
    print("Math contract functions:", dir(math_contract.functions))
    return WeirollContract.createLibrary(math_contract)


@pytest.fixture(scope="module")
def strings_contract(deploy_contract):
    """Strings contract instance (raw web3 contract)."""
    return deploy_contract("Strings", "Libraries")


@pytest.fixture(scope="module")
def strings(strings_contract):
    """Strings contract wrapped with WeirollContract."""
    return WeirollContract.createLibrary(strings_contract)


@pytest.fixture(scope="module")
def test_contract(deploy_contract):
    """TestContract instance (raw web3 contract)."""
    return deploy_contract("TestContract", "test")


@pytest.fixture(scope="module")
def testContract(test_contract):
    """TestContract wrapped with WeirollContract."""
    return WeirollContract.createLibrary(test_contract)


@pytest.fixture(scope="module")
def subplan_contract(deploy_contract):
    """TestSubplan contract instance (raw web3 contract)."""
    return deploy_contract("TestSubplan", "test")


@pytest.fixture(scope="module")
def subplanContract(subplan_contract):
    """TestSubplan contract wrapped with WeirollContract."""
    return WeirollContract.createLibrary(subplan_contract)


@pytest.fixture(scope="module")
def multi_subplan_contract(deploy_contract):
    """TestMultiSubplan contract instance (raw web3 contract)."""
    return deploy_contract("TestMultiSubplan", "test")


@pytest.fixture(scope="module")
def multiSubplanContract(multi_subplan_contract):
    """TestMultiSubplan contract wrapped with WeirollContract."""
    return WeirollContract.createLibrary(multi_subplan_contract)


@pytest.fixture(scope="module")
def bad_subplan_contract(deploy_contract):
    """TestBadSubplan contract instance (raw web3 contract)."""
    return deploy_contract("TestBadSubplan", "test")


@pytest.fixture(scope="module")
def badSubplanContract(bad_subplan_contract):
    """TestBadSubplan contract wrapped with WeirollContract."""
    return WeirollContract.createLibrary(bad_subplan_contract)


@pytest.fixture(scope="module")
def multi_state_subplan_contract(deploy_contract):
    """TestMultiStateSubplan contract instance (raw web3 contract)."""
    return deploy_contract("TestMultiStateSubplan", "test")


@pytest.fixture(scope="module")
def multiStateSubplanContract(multi_state_subplan_contract):
    """TestMultiStateSubplan contract wrapped with WeirollContract."""
    return WeirollContract.createLibrary(multi_state_subplan_contract)


@pytest.fixture(scope="module")
def readonly_subplan_contract(deploy_contract):
    """TestReadonlySubplan contract instance (raw web3 contract)."""
    return deploy_contract("TestReadonlySubplan", "test")


@pytest.fixture(scope="module")
def readonlySubplanContract(readonly_subplan_contract):
    """TestReadonlySubplan contract wrapped with WeirollContract."""
    return WeirollContract.createLibrary(readonly_subplan_contract)


@pytest.fixture(scope="module")
def tuple_helper(deploy_contract):
    """TupleHelper contract instance."""
    return deploy_contract("TupleHelper", "Helpers")

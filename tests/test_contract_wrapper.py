"""
Test script for developing the WeirollContract wrapper around web3.py contracts.
"""
import json
from pathlib import Path
from web3 import Web3
from weiroll.client import CommandFlags

def get_web3():
    """Connect to local Anvil instance."""
    return Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))

def load_contract_data(contract_name, category="Libraries"):
    """Load contract ABI and bytecode."""
    base_dir = Path(__file__).parent.parent / "build" / "contracts"
    json_file = base_dir / category / "combined.json"
    
    with open(json_file) as f:
        combined_data = json.load(f)
    
    contract_key = None
    for key in combined_data["contracts"].keys():
        if key.endswith(f":{contract_name}"):
            contract_key = key
            break
    
    if not contract_key:
        raise ValueError(f"Contract {contract_name} not found in {json_file}")
    
    contract_data = combined_data["contracts"][contract_key]
    
    if isinstance(contract_data["abi"], str):
        abi = json.loads(contract_data["abi"])
    else:
        abi = contract_data["abi"]
    bytecode = "0x" + contract_data["bin"]
    
    return abi, bytecode

def deploy_contract(w3, contract_name, category="Libraries"):
    """Deploy a contract and return a web3.py contract instance."""
    abi, bytecode = load_contract_data(contract_name, category)
    contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    tx_hash = contract.constructor().transact({"from": w3.eth.accounts[0]})
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    return w3.eth.contract(address=tx_receipt.contractAddress, abi=abi)

class SimpleWeirollContract:
    """A simplified version of WeirollContract for testing."""
    
    def __init__(self, web3_contract, command_flags=CommandFlags.DELEGATECALL):
        self.web3_contract = web3_contract
        self.address = web3_contract.address
        self.command_flags = command_flags
        
        # Process all functions in the contract ABI and create wrapper methods
        self._process_functions()
    
    def _process_functions(self):
        """Process contract functions and create wrapper methods."""
        function_names = [fn for fn in dir(self.web3_contract.functions) 
                         if not fn.startswith('_') and fn not in ['abi', 'address', 'w3']]
        
        print(f"Processing functions: {function_names}")
        
        for name in function_names:
            function = getattr(self.web3_contract.functions, name)
            self._add_function(name, function)
    
    def _add_function(self, name, function):
        """Add a wrapper method for a contract function."""
        def wrapper(*args):
            print(f"Calling {name} with args: {args}")
            # In a real implementation, this would create a FunctionCall object
            return {
                "name": name,
                "args": args,
                "function": function
            }
        
        setattr(self, name, wrapper)
    
    @classmethod
    def createLibrary(cls, contract):
        """Create a library wrapper (DELEGATECALL)."""
        return cls(contract, CommandFlags.DELEGATECALL)
    
    @classmethod
    def createContract(cls, contract):
        """Create a contract wrapper (regular CALL)."""
        return cls(contract, CommandFlags.CALL)

if __name__ == "__main__":
    w3 = get_web3()
    math_contract = deploy_contract(w3, "Math")
    
    # Test the native web3.py contract
    print("Direct call result:", math_contract.functions.add(1, 2).call())
    
    # Now test our wrapper
    wrapped = SimpleWeirollContract.createLibrary(math_contract)
    
    # This should print the function names and the wrapper is adding
    print("Wrapped contract methods:", [m for m in dir(wrapped) if not m.startswith('_')])
    
    # Test calling a wrapped function
    result = wrapped.add(3, 4)
    print("Wrapped call result:", result)
    
    # We can also check what methods the function object has
    print("Function methods:", dir(math_contract.functions.add))
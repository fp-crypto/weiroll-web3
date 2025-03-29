import pytest
import random
from hexbytes import HexBytes
from web3 import Web3

# Convert skip marker to use web3.py style
pytestmark = pytest.mark.skip("Skip for now")

def to_bytes(x):
    """Convert an integer to bytes32 format"""
    return Web3.to_bytes(x).rjust(32, b'\0')  # Ensure 32 bytes length

# Pre-defined test bytes
b2 = to_bytes(2)
b1 = to_bytes(1)
b4 = to_bytes(4)

def test_insert(web3, tuple_helper, alice):
    # Test inserting at the beginning
    result = tuple_helper.functions.insertElement(
        b2 + b1, 0, b4, False
    ).call({'from': alice})
    assert HexBytes(result) == HexBytes(b4 + b2 + b1)
    
    # Test inserting in the middle
    result = tuple_helper.functions.insertElement(
        b2 + b1, 1, b4, False
    ).call({'from': alice})
    assert HexBytes(result) == HexBytes(b2 + b4 + b1)
    
    # Test inserting at the end
    result = tuple_helper.functions.insertElement(
        b2 + b1, 2, b4, False
    ).call({'from': alice})
    assert HexBytes(result) == HexBytes(b2 + b1 + b4)
    
    # Test inserting at an invalid position
    with pytest.raises(Exception):
        tuple_helper.functions.insertElement(
            b2 + b1, 3, b4, False
        ).call({'from': alice})
    
    # Generate random bytes for more thorough testing
    rands = b"".join([to_bytes(random.randint(0, 2**256 - 1)) for _ in range(100)])
    
    # Test inserting at each position in the random bytes
    for i in range(101):
        result = tuple_helper.functions.insertElement(
            rands, i, b4, False
        ).call({'from': alice})
        
        # Calculate expected result
        inserted = HexBytes(rands[:i * 32] + b4 + rands[i * 32:])
        assert HexBytes(result) == inserted

def test_replace(web3, tuple_helper, alice):
    # Test replacing the first element
    result = tuple_helper.functions.replaceElement(
        b2 + b1, 0, b4, False
    ).call({'from': alice})
    assert HexBytes(result) == HexBytes(b4 + b1)
    
    # Test replacing the second element
    result = tuple_helper.functions.replaceElement(
        b2 + b1, 1, b4, False
    ).call({'from': alice})
    assert HexBytes(result) == HexBytes(b2 + b4)
    
    # Test replacing at an invalid position
    with pytest.raises(Exception):
        tuple_helper.functions.replaceElement(
            b2 + b1, 2, b4, False
        ).call({'from': alice})
    
    # Generate random bytes for more thorough testing
    rands = b"".join([to_bytes(random.randint(0, 2**256 - 1)) for _ in range(100)])
    
    # Test replacing at each position in the random bytes
    for i in range(100):
        result = tuple_helper.functions.replaceElement(
            rands, i, b4, False
        ).call({'from': alice})
        
        # Calculate expected result
        replaced = HexBytes(rands[:i * 32] + b4 + rands[(i + 1) * 32:])
        assert HexBytes(result) == replaced

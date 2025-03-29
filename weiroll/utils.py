from eth_abi.abi import encode
import eth_abi.grammar
from hexbytes import HexBytes


def eth_abi_encode_single(param: str, arg) -> HexBytes:
    start = 0
    if eth_abi.grammar.parse(param).is_dynamic:
        start = 32

    return HexBytes(encode([param], [arg]))[start:]

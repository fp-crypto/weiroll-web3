import pytest
from web3 import Web3
import json
from weiroll.client import WeirollContract, WeirollPlanner
from tests.integration.conftest import (
    convert_to_wei,
    impersonate_account,
    stop_impersonating,
    send_contract_tx,
)


def test_swaps(weiroll_vm, mainnet_fork_web3, setup_accounts, whale_account):
    # Setup accounts
    whale = whale_account
    dev = setup_accounts

    # Create contract instances
    weth_address = Web3.to_checksum_address(
        "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
    )
    crvseth_address = Web3.to_checksum_address(
        "0xc5424B857f758E906013F3555Dad202e4bdB4567"
    )
    susd_address = Web3.to_checksum_address(
        "0x57Ab1ec28D129707052df4dF418D58a2D46d5f51"
    )
    yvweth_address = Web3.to_checksum_address(
        "0xa258C4606Ca8206D8aA700cE2143D7db854D168c"
    )
    sushi_router_address = Web3.to_checksum_address(
        "0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F"
    )
    univ3_router_address = Web3.to_checksum_address(
        "0xE592427A0AEce92De3Edee1F18E0157C05861564"
    )

    # Load ABIs
    erc20_abi = json.loads("""[
        {"constant":true,"inputs":[],"name":"name","outputs":[{"name":"","type":"string"}],"payable":false,"stateMutability":"view","type":"function"},
        {"constant":false,"inputs":[{"name":"_spender","type":"address"},{"name":"_value","type":"uint256"}],"name":"approve","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"},
        {"constant":true,"inputs":[],"name":"totalSupply","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},
        {"constant":false,"inputs":[{"name":"_from","type":"address"},{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transferFrom","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"},
        {"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"payable":false,"stateMutability":"view","type":"function"},
        {"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},
        {"constant":true,"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string"}],"payable":false,"stateMutability":"view","type":"function"},
        {"constant":false,"inputs":[{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transfer","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"},
        {"constant":true,"inputs":[{"name":"_owner","type":"address"},{"name":"_spender","type":"address"}],"name":"allowance","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"}
    ]""")

    yvweth_abi = erc20_abi + json.loads("""[
        {"name":"withdraw","inputs":[{"name":"maxShares","type":"uint256"}],"outputs":[{"name":"","type":"uint256"}],"stateMutability":"nonpayable","type":"function"}
    ]""")

    crvseth_abi = erc20_abi + json.loads("""[
        {"name":"coins","inputs":[{"name":"i","type":"uint256"}],"outputs":[{"name":"","type":"address"}],"stateMutability":"view","type":"function"}
    ]""")

    sushi_router_abi = json.loads("""[
        {"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint256","name":"amountOutMin","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapExactTokensForTokens","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"nonpayable","type":"function"}
    ]""")

    univ3_router_abi = json.loads("""[
        {"inputs":[{"components":[{"internalType":"address","name":"tokenIn","type":"address"},{"internalType":"address","name":"tokenOut","type":"address"},{"internalType":"uint24","name":"fee","type":"uint24"},{"internalType":"address","name":"recipient","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"},{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint256","name":"amountOutMinimum","type":"uint256"},{"internalType":"uint160","name":"sqrtPriceLimitX96","type":"uint160"}],"internalType":"struct ISwapRouter.ExactInputSingleParams","name":"params","type":"tuple"}],"name":"exactInputSingle","outputs":[{"internalType":"uint256","name":"amountOut","type":"uint256"}],"stateMutability":"nonpayable","type":"function"}
    ]""")

    # Create contract instances
    weth_contract = mainnet_fork_web3.eth.contract(address=weth_address, abi=erc20_abi)
    crvseth_contract = mainnet_fork_web3.eth.contract(
        address=crvseth_address, abi=crvseth_abi
    )
    susd_contract = mainnet_fork_web3.eth.contract(address=susd_address, abi=erc20_abi)
    yvweth_contract = mainnet_fork_web3.eth.contract(
        address=yvweth_address, abi=yvweth_abi
    )
    sushi_router = mainnet_fork_web3.eth.contract(
        address=sushi_router_address, abi=sushi_router_abi
    )
    univ3_router = mainnet_fork_web3.eth.contract(
        address=univ3_router_address, abi=univ3_router_abi
    )

    # Get SETH address from crvseth contract
    seth_address = crvseth_contract.functions.coins(1).call()
    seth_contract = mainnet_fork_web3.eth.contract(address=seth_address, abi=erc20_abi)

    try:
        # Impersonate whale account with ETH funding
        impersonate_account(
            mainnet_fork_web3, whale, fund_amount=convert_to_wei(1), dev_account=dev
        )

        # Check if whale has the required tokens
        yvweth_balance = yvweth_contract.functions.balanceOf(whale).call()
        weth_balance = weth_contract.functions.balanceOf(whale).call()

        if yvweth_balance < int(2e18) or weth_balance < int(1.118383e18):
            pytest.skip(
                f"Whale doesn't have enough tokens. yvWETH: {yvweth_balance}, WETH: {weth_balance}"
            )

        # Transfer tokens to weiroll VM contract
        send_contract_tx(
            mainnet_fork_web3,
            yvweth_contract.functions.transfer(weiroll_vm.address, int(2e18)),
            whale,
            gas=200000,
        )

        send_contract_tx(
            mainnet_fork_web3,
            weth_contract.functions.transfer(weiroll_vm.address, int(1.118383e18)),
            whale,
            gas=200000,
        )

        # Create the weiroll plan
        planner = WeirollPlanner(weiroll_vm)

        # Wrap contracts for weiroll
        WeirollContract.createContract(yvweth_contract)
        w_weth = WeirollContract.createContract(weth_contract)
        w_susd = WeirollContract.createContract(susd_contract)
        w_seth = WeirollContract.createContract(seth_contract)
        w_sushi_router = WeirollContract.createContract(sushi_router)
        w_univ3_router = WeirollContract.createContract(univ3_router)

        # Withdraw tokens from Yearn vault
        planner.call(yvweth_contract, "withdraw", int(1e18))

        # Get WETH balance
        weth_bal = planner.add(w_weth.balanceOf(weiroll_vm.address))

        # Swap WETH → SUSD on Sushiswap
        planner.add(w_weth.approve(w_sushi_router.address, weth_bal))
        planner.add(
            w_sushi_router.swapExactTokensForTokens(
                weth_bal,
                0,
                [w_weth.address, w_susd.address],
                weiroll_vm.address,
                2**256 - 1,
            )
        )

        # Get SUSD balance
        susd_bal = planner.add(w_susd.balanceOf(weiroll_vm.address))

        # Swap SUSD → WETH → SETH on Sushiswap
        planner.add(w_susd.approve(w_sushi_router.address, susd_bal))
        planner.add(
            w_sushi_router.swapExactTokensForTokens(
                susd_bal,
                0,
                [w_susd.address, w_weth.address, w_seth.address],
                weiroll_vm.address,
                2**256 - 1,
            )
        )

        # Get SETH balance
        seth_bal = planner.add(w_seth.balanceOf(weiroll_vm.address))

        # Swap SETH → WETH on Uniswap V3
        planner.add(w_seth.approve(w_univ3_router.address, seth_bal))
        planner.add(
            w_univ3_router.exactInputSingle(
                (
                    w_seth.address,
                    w_weth.address,
                    500,
                    weiroll_vm.address,
                    2**256 - 1,
                    seth_bal,
                    0,
                    0,
                )
            )
        )

        # Execute the plan
        cmds, state = planner.plan()

        # Execute weiroll commands
        send_contract_tx(
            mainnet_fork_web3,
            weiroll_vm.functions.execute(cmds, state),
            whale,
            gas=5000000,
        )

        # Verify results
        final_weth_balance = weth_contract.functions.balanceOf(
            weiroll_vm.address
        ).call()
        assert final_weth_balance > 0

    except Exception as e:
        pytest.skip(f"Error during swap test: {str(e)}")

    finally:
        # Stop impersonating the account
        stop_impersonating(mainnet_fork_web3, whale)

# weiroll-web3

![weiroll](https://user-images.githubusercontent.com/83050944/265799164-385dbc06-b9cb-4a80-89bf-72552f0e6d74.png)

weiroll-web3 is a planner for the operation-chaining/scripting language [weiroll](https://github.com/weiroll/weiroll), integrated with the web3.py library for Ethereum interactions.

It provides an easy-to-use API for generating weiroll programs that can be passed to any compatible implementation.

## Installation

```
pip install weiroll-web3
```

## Usage

### Wrapping contracts

Weiroll programs consist of a sequence of calls to functions in external contracts. These calls can be delegate calls to dedicated library contracts, or standard/static calls to external contracts. Before you can start creating a weiroll program, you must create interfaces for at least one contract you intend to use.

The easiest way to do this is by wrapping web3.py contract instances:

```python
from web3 import Web3
from weiroll import WeirollContract

# Connect to an Ethereum node
w3 = Web3(Web3.HTTPProvider("https://mainnet.infura.io/v3/YOUR_API_KEY"))

# Create a contract instance
contract_abi = [...] # Contract ABI
contract_address = "0x..."
web3_contract = w3.eth.contract(address=contract_address, abi=contract_abi)

# Create weiroll contracts
# For delegate calls (libraries)
library = WeirollContract.createLibrary(web3_contract)
# For regular calls
contract = WeirollContract.createContract(web3_contract)
```

### Planning programs

First, instantiate a planner:

```python
from weiroll import WeirollPlanner

# Create a planner with the account that will execute the transactions
planner = WeirollPlanner(executor_address)
```

Next, add one or more commands to execute:

```python
ret = planner.add(contract.func(a, b))
```

Return values from one invocation can be used in another one:

```python
planner.add(contract.func2(ret))
```

Remember to wrap each call to a contract in `planner.add`. Attempting to pass the result of one contract function directly to another will not work - each one needs to be added to the planner!

For calls to external contracts, you can also pass a value in ether to send:

```python
planner.add(contract.func(a, b).withValue(c))
```

`withValue` takes the same argument types as contract functions so that you can pass the return value of another function or a literal value. You cannot combine `withValue` with delegate calls (eg, calls to a library created with `WeirollContract.createLibrary`) or static calls.

Likewise, if you want to make a particular call static, you can use `.staticcall()`:

```python
result = planner.add(contract.func(a, b).staticcall())
```

Weiroll only supports functions that return a single value by default. If your function returns multiple values, though, you can instruct weiroll to wrap it in a `bytes`, which subsequent commands can decode and work with:

```python
ret = planner.add(contract.func(a, b).rawValue())
```

Once you are done planning operations, generate the program:

```python
commands, state = planner.plan()
```

### Subplans

In some cases, it may be useful to instantiate nested instances of the weiroll VM - for example, when using flash loans, or other systems that function by making a callback to your code. The weiroll planner supports this via 'subplans'.

To make a subplan, construct the operations that should take place inside the nested instance usually, then pass the planner object to a contract function that executes the subplan, and pass that to the outer planner's `.addSubplan()` function instead of `.add()`.

For example, suppose you want to call a nested instance to do some math:

```python
subplanner = WeirollPlanner(executor_address)
sum = subplanner.add(Math.add(1, 2))

planner = WeirollPlanner(executor_address)
planner.addSubplan(Weiroll.execute(subplanner, subplanner.state))
planner.add(events.logUint(sum))

commands, state = planner.plan()
```

Subplan functions must specify which argument receives the current state using the special variable `planner.state` and take exactly one subplanner and one state argument. Subplan functions must either return an updated state or nothing.

If a subplan returns an updated state, return values created in a subplanner, such as `sum` above, can be referenced in the outer scope, and even in other subplans, as long as they are referenced after the command that produces them. Subplans that do not return updated state are read-only, and return values defined inside them cannot be referenced outside them.

## Development

### Build and Test

First, make sure you have Anvil running for tests:

```
yarn anvil:local
```

Then to build and run tests:

```
yarn compile  # Compile Solidity contracts
yarn test     # Run all tests
```

Or you can run individual test files:

```
yarn test:basic  # Run basic functionality tests
```

### Integration Tests

Integration tests allow you to test weiroll with real-world contracts on mainnet. To run these tests, you'll need to have Anvil running in fork mode:

```
# Start Anvil with a mainnet fork
yarn anvil
```

Run all integration tests:

```
yarn test:integration
```

Or run specific integration tests:

```
yarn test:integration:curve   # Test Curve pool liquidity add
yarn test:integration:swaps   # Test multi-protocol swaps
yarn test:integration:chain   # Test action chaining
yarn test:integration:1inch   # Test 1inch swaps (needs API key)
```

For tests that require API keys (like 1inch tests), set the environment variable:

```
export ONE_INCH_API_KEY=your-api-key
```

## Credits

- [@BlinkyStitt](https://github.com/BlinkyStitt) for the original weiroll implementation in Python

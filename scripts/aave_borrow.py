from scripts.get_weth import get_weth
from scripts.helpful_scripts import get_account, LOCAL_BLOCKCHAIN_ENVIRONMENTS
from brownie import interface, config, network
from web3 import Web3

AMOUNT = Web3.toWei(0.1, "ether")


def main():
    account = get_account()
    erc20_address = config["networks"][network.show_active()]["weth_token"]
    if network.show_active() in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        get_weth()
    lending_pool = get_lending_pool()

    # Approve transaction
    approve_erc20(AMOUNT, lending_pool.address, erc20_address, account)
    # Depositing
    print("Depositing")
    tx = lending_pool.deposit(
        erc20_address, AMOUNT, account.address, 0, {"from": account}
    )
    tx.wait(1)
    print("Deposited")
    # Account Status
    borrowable_eth, total_debt = get_borrowable_data(lending_pool, account)
    # DAI en terminos de ETH
    dai_eth_price = get_asset_price(
        config["networks"][network.show_active()]["dai_eth_price_feed"]
    )
    print(f"The DAI/ETH price is {dai_eth_price}")

    amount_dai_to_borrow = (1 / dai_eth_price) * (borrowable_eth * 0.95)
    print(f"We are going to borrow {amount_dai_to_borrow} DAI")

    dai_token = config["networks"][network.show_active()]["dai_token"]
    borrow_txn = lending_pool.borrow(
        dai_token,  # Token address
        Web3.toWei(amount_dai_to_borrow, "ether"),  # Amount
        1,  # Interest Rate
        0,  # Referral Code
        account.address,  # In Behalf Of
        {"from": account},
    )
    borrow_txn.wait(1)
    print("We borrowed some DAI")
    get_borrowable_data(lending_pool, account)

    # RepayAll
    repay_all(Web3.toWei(amount_dai_to_borrow, "ether"), lending_pool, account)
    print("You just deposted, borrowed and repaid with brownie, aave and chainlink")


def get_lending_pool():
    # ABI
    # ADDRESS
    lending_pool_addresses_provider = interface.ILendingPoolAddressesProvider(
        config["networks"][network.show_active()]["lending_pool_addresses_provider"]
    )
    lending_pool_address = lending_pool_addresses_provider.getLendingPool()
    lending_pool = interface.ILendingPool(lending_pool_address)
    return lending_pool


def approve_erc20(amount, spender, erc20_address, account):
    # ABI
    # ADDRESS
    print("Approving ERC20")
    erc20 = interface.IERC20(erc20_address)
    tx = erc20.approve(spender, amount, {"from": account})
    tx.wait(1)
    print("Approved ERC20")
    return tx


def get_borrowable_data(lending_pool, account):
    (
        total_collateral_eth,  # Garantia
        total_debt_eth,  # Total Prestado
        available_borrow_eth,  # Total que se nos permite pedir prestado
        current_liquidation_threshold,  # Nuestro umbral de liquidacion
        ltv,
        health_factor,  # Indice de salud
    ) = lending_pool.getUserAccountData(account.address)

    available_borrow_eth = Web3.fromWei(available_borrow_eth, "ether")
    total_collateral_eth = Web3.fromWei(total_collateral_eth, "ether")
    total_debt_eth = Web3.fromWei(total_debt_eth, "ether")
    print(
        f"You have {total_collateral_eth} ETH in collateral"
    )  # Me devuelve lo que tengo en garantia
    print(
        f"You can borrow {available_borrow_eth} ETH"
    )  # Lo que puedo pedir prestado, nunca puedo superar este numero por que me liquidan
    print(
        f"You have {total_debt_eth} ETH in debt"
    )  # No tengo nada en deuda, por que no he pedido prestado nada aun
    return (float(available_borrow_eth), float(total_debt_eth))


def get_asset_price(price_feed_address):
    # ABI
    # ADDRESS
    dai_eth_price_feed = interface.AggregatorV3Interface(price_feed_address)
    latest_price = dai_eth_price_feed.latestRoundData()[1]
    convertered_latest_price = Web3.fromWei(latest_price, "ether")
    return float(convertered_latest_price)


def repay_all(amount, lending_pool, account):
    # Approve payback
    approve_erc20(
        Web3.toWei(amount, "ether"),
        lending_pool,
        config["networks"][network.show_active()]["dai_token"],
        account,
    )
    dai_token = config["networks"][network.show_active()]["dai_token"]
    repay_txn = lending_pool.repay(
        dai_token, amount, 1, account.address, {"from": account}
    )
    repay_txn.wait(1)
    print("Repaid")

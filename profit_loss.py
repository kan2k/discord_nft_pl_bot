from dotenv import dotenv_values
from datetime import datetime
from web3 import Web3
import requests
import time
import os

here = os.path.dirname(os.path.abspath(__file__))
config = dotenv_values(os.path.join(here, ".env"))

w3 = Web3(Web3.HTTPProvider(config["http_rpc"]))
etherscan_api_key = config["etherscan_api_key"]
start_block = 3914495 # Defaults at CryptoPunk creation block
block = w3.eth.get_block('latest')
last_block = block['number']

def to_ether(wei):
    return w3.fromWei(int(wei), 'ether')

def get_eth_price_now():
    url = "https://api.coinbase.com/v2/exchange-rates?currency=ETH"
    res = requests.get(url)
    data = res.json()
    return round(float(data["data"]['rates']['USDC']), 1)

def os_link_to_api(url):
    return url.lower().replace("www.", "").replace("zh-CN/", "").replace("zh-TW/", "").replace("https://opensea.io/collection/", "https://api.opensea.io/collection/")

# def get_eth_price_with_timestamp(timestamp):
#     # CoinGecko
#     date = datetime.fromtimestamp(int(timestamp)).strftime("%d-%m-%Y")
#     url = f"https://api.coingecko.com/api/v3/coins/ethereum/history?date={date}"
#     print(url)
#     response = requests.get(url)
#     data = response.json()
#     return round(data['market_data']['current_price']['usd'], 2)




async def get_pl_from_wallets(os_link, wallets):
    # Returns
    # None when project is not found

    # fetch and init data from os
    project_contract_address = ""
    project_name = ""
    project_image_url = ""
    project_floor = 0
    if "opensea.io" in os_link:
        url = os_link_to_api(os_link)
        response = requests.get(url)
        data = response.json()
        project_contract_address = data['collection']['primary_asset_contracts'][0]['address']
        project_name = data['collection']['primary_asset_contracts'][0]['name']
        project_image_url = data['collection']['banner_image_url']
        project_floor = floor_price = data["collection"]["stats"]["floor_price"]
    else:
        return None

    # set start block as contract creation
    url = f"https://api.etherscan.io/api?module=contract&action=getcontractcreation&contractaddresses={project_contract_address}&apikey={etherscan_api_key}"
    response = requests.get(url)
    data = response.json()
    creation_hash = data['result'][0]['txHash']
    creation_tx = w3.eth.get_transaction(creation_hash)
    start_block = creation_tx['blockNumber']

    # nft calculation
    trade_tx_hashes = []
    free_and_mint_tx_hashes = []
    free_and_mint_count = sell_count = buy_count = 0

    for wallet in wallets:
        url = f"https://api.etherscan.io/api?module=account&action=tokennfttx&contractaddress={project_contract_address}&address={wallet}&startblock={start_block}&endblock={last_block}&sort=asc&apikey={etherscan_api_key}"
        response = requests.get(url)
        data = response.json()
        if data['status'] == 0:
            return None
        data = data['result']
        for record in data:
            # free airdrop or mint case, doesnt have internal txs to identify, therefore will not go to [trade_tx_hashes] for proessing
            if record['from'] == "0x0000000000000000000000000000000000000000":
                free_and_mint_count += 1
                if record['hash'] not in free_and_mint_tx_hashes:
                    free_and_mint_tx_hashes.append(record['hash'])
                continue
            if record['from'] in wallets:
                sell_count += 1
            if record['to'] in wallets:
                buy_count += 1
            trade_tx_hashes.append(record['hash'])
    total_trade_count = sell_count + buy_count
    total_nft_count = free_and_mint_count + buy_count - sell_count

    # eth calculation
    print(f"Trading Details of {project_name}: ")
    cost_eth = sale_eth = 0
    for hash in trade_tx_hashes:
        url = f"https://api.etherscan.io/api?module=account&action=txlistinternal&txhash={hash}&apikey={etherscan_api_key}"
        response = requests.get(url)
        data = response.json()
        internal_txs = data['result']
        type_of_tx = ''
        total_amount_in_tx = 0
        # depreciated because coingecko api rate limit of 50/min
        # eth_price_on_day_of_tx = get_eth_price_with_timestamp(internal_txs[0]['timeStamp']) 
        for tx in internal_txs:
            total_amount_in_tx += to_ether(tx['value'])
            if tx['to'] in wallets:
                type_of_tx = 'sale'
                amount = to_ether(tx['value'])
                print(f"[{hash}] Sold 1x {project_name} for {amount} ETH")
                # print(f"[{hash}] Sold for {amount} ETH (${float(amount) * eth_price_on_day_of_tx})")
                sale_eth += amount
                # sale_usd += float(amount) * eth_price_on_day_of_tx
        if type_of_tx != 'sale':
            print(f"[{hash}] Bought 1x {project_name} for {total_amount_in_tx} ETH")
            # print(f"[{hash}] Bought for {total_amount_in_tx} ETH (${float(total_amount_in_tx) * eth_price_on_day_of_tx})")
            cost_eth += total_amount_in_tx
            # cost_usd += float(total_amount_in_tx) * eth_price_on_day_of_tx

    mint_eth = 0
    for hash in free_and_mint_tx_hashes:
        record = w3.eth.get_transaction(hash)
        mint_eth += to_ether(record['value'])

    eth_price = get_eth_price_now()

    print(f"\nSummary of {project_name}: ")
    print(f"Currently owning {total_nft_count}x {project_name}")
    print(f"Traded {total_trade_count} times on {project_name}, {free_and_mint_count + buy_count - sell_count} are still unrealised")
    print(f"Minted {free_and_mint_count}x {project_name} for {mint_eth} ETH (~${float(mint_eth) * eth_price})")
    print(f"Bought {buy_count}x {project_name} for {cost_eth} ETH (~${float(cost_eth) * eth_price})")
    print(f"Sold {sell_count}x {project_name} for {sale_eth} ETH (~${float(sale_eth) * eth_price})")

    return {"eth_price_today": eth_price, "project_name": project_name, "project_floor": project_floor, "project_image_url": project_image_url,"total_nft_count": total_nft_count, "total_trade_count": total_trade_count, "free_and_mint_count": free_and_mint_count, "buy_count": buy_count, "sell_count": sell_count, "mint_eth": mint_eth, "cost_eth": cost_eth, "sale_eth": sale_eth}
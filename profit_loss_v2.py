from concurrent.futures import ThreadPoolExecutor
from dotenv import dotenv_values
import requests, os, aiohttp, asyncio, datetime
from web3 import Web3
from collections import Counter

here = os.path.dirname(os.path.abspath(__file__))
config = dotenv_values(os.path.join(here, ".env"))
w3 = Web3(Web3.HTTPProvider(config['http_rpc']))
etherscan_api_key = config['etherscan_api_key']
null_address = "0x0000000000000000000000000000000000000000"
weth_contract = "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"

def to_ether(wei):
    return float(w3.fromWei(int(wei), 'ether'))

def get_eth_price_now():
    url = "https://api.coinbase.com/v2/exchange-rates?currency=ETH"
    res = requests.get(url)
    data = res.json()
    return round(float(data["data"]['rates']['USDC']), 1)

def get_collection_data(os_url: str) -> dict:
    """
    returns collection data in dict
    """
    collection = os_url.lower().replace("www.", "").replace("zh-cn/", "").replace("zh-tw/", "").replace("https://opensea.io/collection/", "")
    api_url = "https://api.opensea.io/collection/" + collection
    response = requests.get(api_url)
    data = response.json()
    name = data['collection']['name']
    contract_address = data['collection']['primary_asset_contracts'][0]['address']
    floor_price = data["collection"]["stats"]["floor_price"]
    image = "https://open-graph.opensea.io/v1/collections/" + collection
    return {"name": name, "contract_address": contract_address, "floor_price": floor_price, "image": image}


async def get_transaction_details(wallet_address, hash, start_block, last_block):
    """
    returns
    from_address, to_address, gas_spent, eth_spent
    """
    wallet_address = wallet_address.lower()
    tx = w3.eth.get_transaction(hash)
    from_address = tx['from'].lower()
    to_address = tx['to'].lower()

    # Transaction fee in ETH = gasPrice * gasUsed, only calculated when the wallet is the one who initiate the tx
    # figure out eth spent and gain with internal txs
    receipt = w3.eth.get_transaction_receipt(hash)
    eth_gas_spent = eth_spent = eth_gained = 0
    if from_address == wallet_address:
        eth_gas_spent = tx['gasPrice'] * receipt['gasUsed']
        eth_spent += tx['value']


    api_url = f"https://api.etherscan.io/api?module=account&action=txlistinternal&txhash={hash}&apikey={etherscan_api_key}"
    response = requests.get(api_url)
    data = response.json()
    internal_txs = data['result']
    if internal_txs == []:
        api_url = f"https://api.etherscan.io/api?module=account&action=tokentx&contractaddress={weth_contract}&address=0x7d93491bE90281479be4e1128fc9b028Fd69d697&startblock={start_block}&endblock={last_block}&sort=asc&apikey={etherscan_api_key}"
        response = requests.get(api_url)
        data = response.json()
        weth_txs = data['result']
        # no internal txs and weth, taking contract value
        amount = int(tx['value'])
        if weth_txs == []:
            if from_address == wallet_address:
                eth_spent += amount
            if to_address == wallet_address:
                eth_gained += amount
        else:
            for weth_tx in weth_txs:
                amount = int(weth_tx['value'])
                if weth_tx['hash'] != hash:
                    continue
                if weth_tx['from'] == wallet_address:
                    eth_spent += amount
                if weth_tx['to'] == wallet_address:
                    eth_gained += amount

    if internal_txs != []:
        for internal_tx in internal_txs:
            amount = int(internal_tx['value'])
            if internal_tx['to'].lower() == wallet_address:
                eth_gained += amount
            if internal_tx['from'].lower() == wallet_address:
                eth_spent += amount

    return {"eth_gas_spent": to_ether(eth_gas_spent), 
            "eth_spent": to_ether(eth_spent), 
            "eth_gained": to_ether(eth_gained),} 

async def get_erc721_transactions(wallet_address: str, collection_contract_address: str, start_block: str, last_block: str):
    """
    returns 
    a dict of erc721 transfer count and total num of that collection owned currently
        e.g. total nft in (denoted as positive num) and total nft out (negative) per transcation
    """
    wallet_address = wallet_address.lower()
    api_url = f"https://api.etherscan.io/api?module=account&action=tokennfttx&contractaddress={collection_contract_address}&address={wallet_address}&startblock={start_block}&endblock={last_block}&sort=asc&apikey={etherscan_api_key}"
    response = requests.get(api_url)
    data = response.json()
    raw_transactions = data['result']
    nft_per_tx_dict = {}
    nft_owned = mint_amount = buy_amount = sell_amount = 0
    for transaction in raw_transactions:
        hash = transaction['hash']
        if hash not in nft_per_tx_dict:
            nft_per_tx_dict[hash] = 0

        if transaction['to'] == wallet_address: # token transfer in
            nft_per_tx_dict[hash] += 1
            buy_amount += 1
            nft_owned += 1

        if transaction['from'] == null_address: # token is minted
            mint_amount += 1
        if transaction['from'] == wallet_address: # token transfer out
            nft_per_tx_dict[hash] -= 1
            sell_amount += 1
            nft_owned -= 1

    return nft_per_tx_dict, nft_owned, mint_amount, buy_amount, sell_amount


async def get_pl(os_url: str, wallets: list) -> dict:
    wallets = [s.lower() for s in wallets]
    collection = get_collection_data(os_url)

    # fetch start and last block
    # set start block as contract creation block
    start_block = 3914495 # Defaults at CryptoPunks creation block
    url = f"https://api.etherscan.io/api?module=contract&action=getcontractcreation&contractaddresses={collection['contract_address']}&apikey={etherscan_api_key}"
    response = requests.get(url)
    data = response.json()
    creation_hash = data['result'][0]['txHash']
    creation_tx = w3.eth.get_transaction(creation_hash)
    start_block = creation_tx['blockNumber']
    block = w3.eth.get_block('latest')
    last_block = str(block['number'])
    total_nft_owned = total_mint_amount = total_buy_amount = total_sell_amount = 0
    total_eth_spent = total_eth_gained = total_eth_gas_spent = 0

    eth_price = get_eth_price_now()
    for wallet in wallets:
        nft_per_tx_dict, nft_owned, mint_amount, buy_amount, sell_amount = await get_erc721_transactions(wallet, collection['contract_address'],start_block, last_block)
        total_nft_owned += nft_owned
        total_mint_amount += mint_amount
        total_buy_amount += buy_amount
        total_sell_amount += sell_amount

        for tx in nft_per_tx_dict:
            details = await get_transaction_details(wallet, tx, start_block, last_block)
            total_eth_spent += details["eth_spent"]
            total_eth_gained += details["eth_gained"]
            total_eth_gas_spent += details["eth_gas_spent"]

    eth_avg_buy_price = total_mint_amount + total_buy_amount and total_eth_spent / (total_mint_amount + total_buy_amount)
    eth_avg_sell_price = total_sell_amount and total_eth_gained / total_sell_amount
    eth_holding_value = total_nft_owned * collection['floor_price']
    realised_pl = total_eth_gained - total_eth_spent
    potential_pl = eth_holding_value + total_eth_gained - total_eth_spent
    roi = total_eth_spent and (eth_holding_value + total_eth_gained - total_eth_spent) / total_eth_spent * 100

    results = { "project_name": collection['name'], 
                "project_floor": collection['floor_price'], 
                "project_floor_usd": collection['floor_price'] * eth_price, 
                "project_image_url": collection['image'],
                "total_nft_owned": total_nft_owned, 
                "total_trade_count": len(nft_per_tx_dict), 
                "total_mint_amount": total_mint_amount, 
                "total_buy_amount": total_buy_amount, 
                "total_sell_amount": total_sell_amount, 
                "eth_gas_spent": total_eth_gas_spent,
                "usd_gas_spent": total_eth_gas_spent * eth_price,
                "eth_spent": total_eth_spent,
                "eth_gained": total_eth_gained,
                "usd_spent": total_eth_spent * eth_price,
                "usd_gained": total_eth_gained * eth_price,
                "eth_avg_buy_price": eth_avg_buy_price,
                "usd_avg_buy_price": eth_avg_buy_price * eth_price,
                "eth_avg_sell_price": eth_avg_sell_price,
                "usd_avg_sell_price": eth_avg_sell_price * eth_price,
                "eth_holding_value": eth_holding_value,
                "usd_holding_value": eth_holding_value * eth_price,
                "realised_pl_eth": realised_pl,
                "realised_pl_usd": realised_pl * eth_price,
                "potential_pl_eth": potential_pl,
                "potential_pl_usd": potential_pl * eth_price,
                "roi": roi, }
    for k, v in results.items():
        if not isinstance(results[k], str):
            if "usd" in k:
                results[k] = round(v)
            if "eth" in k:
                results[k] = round(v, 3)
    # print(results)
    return results


if __name__ == "__main__":
    # test: offer taken
    # asyncio.run(get_pl_from_wallets("https://opensea.io/collection/elemental-fang-lijun", ["0x7d93491bE90281479be4e1128fc9b028Fd69d697"]))
    # test: gem swept
    # asyncio.run(get_pl("https://opensea.io/collection/san-origin", ["0x4e435D2d6fCe29Ab31f9841b98D09872869C6bC0"]))

    # !pl https://opensea.io/collection/elemental-fang-lijun 0x7d93491bE90281479be4e1128fc9b028Fd69d697

    asyncio.run(get_pl("https://opensea.io/collection/san-origin", ["0x50042aC52aE6143caCC0f900f5959c4B69eF1963"]))
    # !pl https://opensea.io/zh-CN/collection/san-origin 0x50042aC52aE6143caCC0f900f5959c4B69eF1963
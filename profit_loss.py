from dotenv import dotenv_values
import requests, os, aiohttp, asyncio
from web3 import Web3

here = os.path.dirname(os.path.abspath(__file__))
config = dotenv_values(os.path.join(here, ".env"))
w3 = Web3(Web3.HTTPProvider(config["http_rpc"]))
etherscan_api_key = config["etherscan_api_key"]
start_block = 3914495 # Defaults at CryptoPunks creation block
block = w3.eth.get_block('latest')
last_block = block['number']

gem_contract = "0x83C8F28c26bF6aaca652Df1DbBE0e1b56F8baBa2".lower() # Gem: GemSwap 2
weth_contract = "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2" # WETH Token Contract

class Fetch:
    def __init__(self, limit, rate):
        self.limit = limit
        self.rate = rate

    async def make_request(self, url):
        async with self.limit:
            async with aiohttp.ClientSession() as session:
                async with session.request(method = 'GET', url = url) as response:
                    print(f"Making request for {url}")
                    json = await response.json()
                    if response.status != 200:
                        response.raise_for_status()
                    await asyncio.sleep(self.rate)
                    return json['result']

def to_ether(wei):
    return w3.fromWei(int(wei), 'ether')

def get_eth_price_now():
    url = "https://api.coinbase.com/v2/exchange-rates?currency=ETH"
    res = requests.get(url)
    data = res.json()
    return round(float(data["data"]['rates']['USDC']), 1)

def os_link_to_api(url):
    return url.lower().replace("www.", "").replace("zh-cn/", "").replace("zh-tw/", "").replace("https://opensea.io/collection/", "https://api.opensea.io/collection/")

def os_link_to_os_graph(url):
    return url.lower().replace("www.", "").replace("zh-CN/", "").replace("zh-TW/", "").replace("https://opensea.io/collection/", "https://open-graph.opensea.io/v1/collections/")

# def get_eth_price_with_timestamp(timestamp):
#     # CoinGecko
#     date = datetime.fromtimestamp(int(timestamp)).strftime("%d-%m-%Y")
#     url = f"https://api.coingecko.com/api/v3/coins/ethereum/history?date={date}"
#     print(url)
#     response = requests.get(url)
#     data = response.json()
#     return round(data['market_data']['current_price']['usd'], 2)

async def get_pl_from_wallets(os_link: str, wallets: list) -> dict:
    # Returns
    # None when project is not found

    wallets = [s.lower() for s in wallets]
    # fetch and init data from os
    project_contract_address = ""
    project_name = ""
    project_image_url = os_link_to_os_graph(os_link)
    project_floor = 0
    if "opensea.io" in os_link:
        url = os_link_to_api(os_link)
        response = requests.get(url)
        data = response.json()
        project_contract_address = data['collection']['primary_asset_contracts'][0]['address']
        project_name = data['collection']['name']
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
    gem_tx_hashes = []
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
            if record['from'] == gem_contract:
                buy_count += 1
                if record['hash'] not in gem_tx_hashes:
                    gem_tx_hashes.append(record['hash'])
                continue
            if record['from'] in wallets:
                sell_count += 1
            if record['to'] in wallets:
                buy_count += 1
            trade_tx_hashes.append(record['hash'])
    total_trade_count = sell_count + buy_count
    total_nft_count = free_and_mint_count + buy_count - sell_count

    # eth calculation
    print(f"Fetching {len(trade_tx_hashes) + len(gem_tx_hashes)} internal txns from etherscan api...")
    cost_eth = sale_eth = 0

    # prcoess weth transaction first because they do not have internal tx, then remove them from trade hashes
    weth_txs_hashes = []
    url = f"https://api.etherscan.io/api?module=account&action=tokentx&contractaddress={weth_contract}&address=0x7d93491bE90281479be4e1128fc9b028Fd69d697&startblock={start_block}&endblock={last_block}&sort=asc&apikey={etherscan_api_key}"
    response = requests.get(url)
    data = response.json()
    weth_txs = data['result']
    for weth_tx in weth_txs:
        if weth_tx['hash'] in trade_tx_hashes:
            if weth_tx['hash'] not in weth_txs_hashes:
                weth_txs_hashes.append(weth_tx['hash'])
            # find out who initiated the weth transaction w/ tx details
            tx_detail = w3.eth.get_transaction(weth_tx['hash'])
            amount = to_ether(weth_tx['value'])
            if tx_detail['from'].lower() in wallets:
                # sell case
                if weth_tx['to'] in wallets:
                    print(f"[{weth_tx['hash']}] Accepted offer, sold 1x {project_name} for {amount} ETH")
                    sale_eth += amount
                    continue
                if weth_tx['from'] in wallets:
                    # paying royalties
                    print(f"[{weth_tx['hash']}] Accepted offer, paying {amount} ETH royalties")
                    sale_eth -= amount
                    continue
            if tx_detail['from'] not in wallets:
                # buy case
                print(f"[{weth_tx['hash']}] Offer accepted, buying 1x {project_name} for {amount} ETH")
                if weth_tx['from'] in wallets:
                    cost_eth += amount

    for weth_tx in weth_txs_hashes:
        trade_tx_hashes.remove(weth_tx)

    # get internal txs for all txs
    # async request task
    f = Fetch(limit=asyncio.Semaphore(4), rate=1)
    task_urls = []
    tasks = []
    for hash in trade_tx_hashes:
        task_urls.append(f"https://api.etherscan.io/api?module=account&action=txlistinternal&txhash={hash}&apikey={etherscan_api_key}")
    for url in task_urls:
        tasks.append(f.make_request(url=url))
    all_internal_txs_trades = await asyncio.gather(*tasks)

    task_urls = []
    tasks = []
    for hash in gem_tx_hashes:
        task_urls.append(f"https://api.etherscan.io/api?module=account&action=txlistinternal&txhash={hash}&apikey={etherscan_api_key}")
    for url in task_urls:
        tasks.append(f.make_request(url=url))
    all_internal_txs_gems = await asyncio.gather(*tasks)

    print(f"Trading Details of {project_name}: ")
    for internal_txs in all_internal_txs_trades:
        total_amount_eth_in_tx = 0
        type_of_tx = ''
        for tx in internal_txs:
            total_amount_eth_in_tx += to_ether(tx['value'])
            if tx['to'] in wallets:
                type_of_tx = 'sale'
                amount = to_ether(tx['value'])
                print(f"[{hash}] Sold 1x {project_name} for {amount} ETH")
                # print(f"[{hash}] Sold for {amount} ETH (${float(amount) * eth_price_on_day_of_tx})")
                sale_eth += amount
                # sale_usd += float(amount) * eth_price_on_day_of_tx

        if type_of_tx != 'sale':
                print(f"[{hash}] Bought 1x {project_name} for {total_amount_eth_in_tx} ETH")
                # print(f"[{hash}] Bought for {total_amount_eth_in_tx} ETH (${float(total_amount_eth_in_tx) * eth_price_on_day_of_tx})")
                cost_eth += total_amount_eth_in_tx
                # cost_usd += float(total_amount_eth_in_tx) * eth_price_on_day_of_tx

    for internal_txs in all_internal_txs_gems:
        total_amount_eth_in_tx = 0
        amount_of_nft_in_tx = 0
        for tx in internal_txs:
            print(tx)
            if tx['from'] == gem_contract:
                total_amount_eth_in_tx += to_ether(tx['value'])
                amount_of_nft_in_tx += 1
                cost_eth += to_ether(tx['value'])
            if tx['to'] in wallets: # gem return eth when on failed buys
                total_amount_eth_in_tx -= to_ether(tx['value'])
                cost_eth -= to_ether(tx['value'])
        
        print(f"[{hash}] Gem Swept {amount_of_nft_in_tx}x {project_name} for {total_amount_eth_in_tx} ETH")


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

if __name__ == "__main__":
    asyncio.run(get_pl_from_wallets("https://opensea.io/collection/elemental-fang-lijun", ["0x7d93491bE90281479be4e1128fc9b028Fd69d697"]))
    # !pl https://opensea.io/collection/elemental-fang-lijun 0x7d93491bE90281479be4e1128fc9b028Fd69d697
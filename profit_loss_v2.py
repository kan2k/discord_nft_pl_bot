from dotenv import dotenv_values
import requests, os, aiohttp, asyncio
from web3 import Web3

class Fetch:
    def __init__(self, limit, rate):
        self.limit = limit
        self.rate = rate

    async def make_request(self, url, hash):
        async with self.limit:
            async with aiohttp.ClientSession() as session:
                async with session.request(method = 'GET', url = url) as response:
                    json = await response.json()
                    if response.status != 200:
                        response.raise_for_status()
                    await asyncio.sleep(self.rate)
                    return [hash, json['result']]

here = os.path.dirname(os.path.abspath(__file__))
config = dotenv_values(os.path.join(here, ".env"))
w3 = Web3(Web3.HTTPProvider(config['http_rpc']))
etherscan_api_key = config['etherscan_api_key']
null_address = "0x0000000000000000000000000000000000000000"
weth_contract = "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"

os_headers = {
    "accept": "application/json",
    "X-API-KEY": config['opensea_api_key']
}

def to_ether(wei):
    return float(w3.fromWei(int(wei), 'ether'))

def get_eth_price_now():
    url = "https://api.coinbase.com/v2/exchange-rates?currency=ETH"
    res = requests.get(url)
    data = res.json()
    return round(float(data["data"]['rates']['USDC']), 1)

def get_collection_data(arg: str) -> dict:
    """
    returns collection data in dict
    """
    if '/' in arg:
        slug = arg.lower().replace("www.", "").replace("zh-cn/", "").replace("zh-tw/", "").replace("https://opensea.io/collection/", "")
    elif arg.startswith('0x'):
        response = requests.get(f"https://api.opensea.io/api/v1/asset_contract/{arg}", headers=os_headers)
        data = response.json()
        slug = data['collection']['slug']
    response = requests.get(f"https://api.opensea.io/collection/" + slug)
    data = response.json()
    name = data['collection']['name']
    contract_address = data['collection']['primary_asset_contracts'][0]['address']
    floor_price = data["collection"]["stats"]["floor_price"]
    image = "https://open-graph.opensea.io/v1/collections/" + slug
    return {"name": name, "contract_address": contract_address, "floor_price": floor_price, "image": image}


async def get_transaction_details(wallet_address, tx_hash, weth_txs, internal_txs):
    """
    returns
    from_address, to_address, gas_spent, eth_spent
    """
    wallet_address = wallet_address.lower()
    tx = w3.eth.get_transaction(tx_hash)
    from_address = tx['from'].lower()
    to_address = tx['to'].lower()

    # Transaction fee in ETH = gasPrice * gasUsed, only calculated when the wallet is the one who initiate the tx
    # figure out eth spent and gain with internal txs
    receipt = w3.eth.get_transaction_receipt(tx_hash)
    eth_gas_spent = eth_mint_spent = eth_spent = eth_gained = 0
    if to_address == '0x05da517b1bf9999b7762eaefa8372341a1a47559'.lower():
        eth_mint_spent += tx['value']
    elif from_address == wallet_address:
        eth_gas_spent = tx['gasPrice'] * receipt['gasUsed']
        eth_spent += tx['value']
        

    if internal_txs == []:
        # no internal txs and weth, taking contract value
        amount = int(tx['value'])
        if weth_txs == []:
            # if from_address == wallet_address:
            #     eth_spent += amount
            if to_address == wallet_address:
                eth_gained += amount
        else:
            for weth_tx in weth_txs:
                amount = int(weth_tx['value'])
                if weth_tx['hash'] != tx_hash:
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

    if eth_spent >= eth_gained:
        return {"eth_gas_spent": to_ether(eth_gas_spent),
                "eth_mint_spent": to_ether(eth_mint_spent),
                "eth_spent": to_ether(eth_spent) - to_ether(eth_gained), 
                "eth_gained": 0,} 
    else:
        return {"eth_gas_spent": to_ether(eth_gas_spent),
                "eth_mint_spent": to_ether(eth_mint_spent),
                "eth_spent": 0, 
                "eth_gained": to_ether(eth_gained) - to_ether(eth_spent),} 


    

async def get_erc721_transactions(query_wallets, query_wallet: str, collection_contract_address: str, start_block: str, last_block: str):
    """
    returns 
    a dict of erc721 transfer count and total num of that collection owned currently
        e.g. total nft in (denoted as positive num) and total nft out (negative) per transcation
    """
    wallet_address = query_wallet.lower()
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

        if transaction['from'] == null_address: # token is minted
            nft_per_tx_dict[hash] += 1
            mint_amount += 1
            nft_owned += 1
            continue

        elif transaction['to'] == wallet_address and transaction['from'] not in query_wallets: # token transfer in
            nft_per_tx_dict[hash] += 1
            buy_amount += 1
            nft_owned += 1
            continue

        elif transaction['from'] == wallet_address and transaction['to'] not in query_wallets: # token transfer out
            nft_per_tx_dict[hash] -= 1
            sell_amount += 1
            nft_owned -= 1
            continue

    return nft_per_tx_dict, nft_owned, mint_amount, buy_amount, sell_amount

async def get_tx(os_url: str, wallets: list) -> dict:

    wallets = [s.lower() for s in wallets]
    collection = get_collection_data(os_url)


async def get_pl(os_url: str, wallets: list) -> dict:
    
    wallets = [s.lower() for s in wallets]
    collection = get_collection_data(os_url)

    # fetch start and last block
    # set start block as contract creation block
    start_block = 3914495 # Defaults at CryptoPunks creation block
    response = requests.get(f"https://api.etherscan.io/api?module=contract&action=getcontractcreation&contractaddresses={collection['contract_address']}&apikey={etherscan_api_key}")
    data = response.json()
    creation_hash = data['result'][0]['txHash']
    creation_tx = w3.eth.get_transaction(creation_hash)
    start_block = creation_tx['blockNumber']
    block = w3.eth.get_block('latest')
    last_block = str(block['number'])
    total_nft_owned = total_mint_amount = total_buy_amount = total_sell_amount = 0
    total_eth_buy_spent = total_eth_gained = total_eth_gas_spent = total_eth_mint_spent = 0

    eth_price = get_eth_price_now()
    for wallet in wallets:
        # print(f"Working on {wallet}...")
        # print(f"Processing transactions related to the collection")
        nft_per_tx_dict, nft_owned, mint_amount, buy_amount, sell_amount = await get_erc721_transactions(wallets, wallet, collection['contract_address'], start_block, last_block)
        if not nft_per_tx_dict:
            continue
        total_nft_owned += nft_owned
        total_mint_amount += mint_amount
        total_buy_amount += buy_amount
        total_sell_amount += sell_amount

        # print(f"Processing offers")

        api_url = f"https://api.etherscan.io/api?module=account&action=tokentx&contractaddress={weth_contract}&address={wallet}&startblock={start_block}&endblock={last_block}&sort=asc&apikey={etherscan_api_key}"
        response = requests.get(api_url)
        data = response.json()
        weth_txs = data['result']

        # print(f"Processing internal txs")

        f = Fetch(limit=asyncio.Semaphore(4), rate=1)
        tasks = []
        for tx_hash in nft_per_tx_dict:
            tasks.append(f.make_request(url=f"https://api.etherscan.io/api?module=account&action=txlistinternal&txhash={tx_hash}&apikey={etherscan_api_key}", hash=tx_hash))
        internal_txs = await asyncio.gather(*tasks)

        for tx in internal_txs:
            tx_hash = tx[0]
            internal_tx = tx[1]
            details = await get_transaction_details(wallet, tx_hash, weth_txs, internal_tx)
            if details["eth_mint_spent"] > 0:
                print(f"[{tx_hash}] MINTED {nft_per_tx_dict[tx_hash]} for {details['eth_mint_spent'] + details['eth_gas_spent']}")
            elif details["eth_spent"] > 0:
                print(f"[{tx_hash}] BOUGHT {nft_per_tx_dict[tx_hash]} for {details['eth_spent']}")
            elif details["eth_gained"] > 0:
                print(f"[{tx_hash}] SOLD {nft_per_tx_dict[tx_hash]} for {details['eth_gained']}")
            else:
                print(f"[{tx_hash}] UNKNOWN {nft_per_tx_dict[tx_hash]}")
            # print(f"[{tx_hash}] {total_eth_gained - total_eth_buy_spent - total_eth_mint_spent - total_eth_gas_spent}")
            total_eth_buy_spent += details["eth_spent"]
            total_eth_gained += details["eth_gained"]
            total_eth_gas_spent += details["eth_gas_spent"]
            total_eth_mint_spent += details["eth_mint_spent"]

    total_eth_spent = total_eth_buy_spent + total_eth_mint_spent + total_eth_gas_spent 
    total_eth_mint_spent = total_eth_mint_spent
    eth_avg_mint_price = total_mint_amount and total_eth_mint_spent / total_mint_amount
    eth_avg_buy_price = total_buy_amount and total_eth_buy_spent / total_buy_amount
    eth_avg_sell_price = total_sell_amount and total_eth_gained / total_sell_amount
    eth_holding_value = total_nft_owned * collection['floor_price']
    realised_pl = total_eth_gained - total_eth_spent
    break_even_amount = break_even_price = 0
    if realised_pl < 0:
        realised_pl = 0
        break_even_amount = round((total_eth_spent - total_eth_gained) / collection['floor_price'])
        if break_even_amount > total_nft_owned:
            break_even_price = total_nft_owned and (total_eth_spent - total_eth_gained) / total_nft_owned
    potential_pl = eth_holding_value + total_eth_gained - total_eth_spent

    if total_eth_spent == 0:
        roi = eth_holding_value + total_eth_gained * 100
    else:
        roi = (eth_holding_value + total_eth_gained - total_eth_spent) / (total_eth_spent + total_eth_gas_spent) * 100

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
                "eth_mint_spent": total_eth_mint_spent,
                "usd_mint_spent": total_eth_mint_spent * eth_price,
                "eth_buy_spent": total_eth_buy_spent,
                "usd_buy_spent": total_eth_buy_spent * eth_price,
                "eth_total_spent": total_eth_spent,
                "usd_total_spent": total_eth_spent * eth_price,
                "eth_gained": total_eth_gained,
                "usd_gained": total_eth_gained * eth_price,
                "eth_avg_mint_price": eth_avg_mint_price,
                "usd_avg_mint_price": eth_avg_mint_price * eth_price,
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
                "roi": roi, 
                "break_even_amount": break_even_amount,
                "break_even_price": break_even_price 
                }
    for k, v in results.items():
        if not isinstance(results[k], str):
            if "usd" in k:
                results[k] = round(v)
            if "eth" in k:
                results[k] = round(v, 3)
    return results

if __name__ == "__main__":
    print('Testing...')

    # test: nft was moved to a staking contract
    # print(asyncio.run(get_pl("https://opensea.io/collection/ethernalelves", ["0x608C57F77D2FFEf584bd61f19D229432475d00f7", "0x8EB0Ba946E03847E9D23B5BE2Ac0Ca397BC59a72", "0x9f90Ab8517Bb89A612FfeBe92E5CcF2Db99Ab6a5", "0xb7B28e1171f32a46A2425A9558A6e7fA053E5b3E", "0x743280c1CF6194DA4E8BF818691efE95Bfcba266", "0xA98C0f13343d034904049acA9Cf702c763eb2FEF", "0x581650e95f2601E832Bf8c9722ccCE672f9Dd8e0", "0x1c6387D26b6B8d73cD512661A6746e236DB0b1C4", "0x16775dC3c55Fcb7E272F1027fF68118f360f3D85", "0x754EF2969A3Fd57fccAEa07322b4Ea70C9E62F2c", "0xA70a9F530Ce78BdFf59A59388Cf88Ff825c68160", "0x8cf3BF4a523DB74b6A639CE00E932D97d10E645F", "0x78955B46C788Ba04F11867701c255a8AcD7d15C0", "0xB1E6DeA5F280C8cA5d49a911284f3002be351ce7", "0x000c987F621B3788F84112fa7a1E8B42AB8CC212"])))

    # test: minted 2 for 0.2 each
    print(asyncio.run(get_pl("https://opensea.io/collection/kprverse", ["0x83Bff380D2c59F88F3132542fb23B40AfCf361d7"])))

    # test: free mint, big ROI %
    # print(asyncio.run(get_pl("https://opensea.io/collection/castaways-the-islands", ["0x14f69c8c334c4c6ea526c58ae94b1431826ace94"])))

    # test: offer taken
    # asyncio.run(get_pl_from_wallets("https://opensea.io/collection/elemental-fang-lijun", ["0x7d93491bE90281479be4e1128fc9b028Fd69d697"]))

    # test: gem swept
    # asyncio.run(get_pl("https://opensea.io/collection/san-origin", ["0x4e435D2d6fCe29Ab31f9841b98D09872869C6bC0"]))
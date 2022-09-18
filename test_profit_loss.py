import pytest
from profit_loss_2 import get_collection_data, get_erc721_transactions, get_transaction_details, get_eth_price_with_date

@pytest.fixture
def example_fixture():
    return 1

def test_with_fixture(example_fixture):
    assert example_fixture == 1

def test_get_collection_data():
    data = get_collection_data("https://opensea.io/collection/azuki")
    assert data['name'] == "Azuki"
    assert data['contract_address'] == "0xed5af388653567af2f388e6224dc7c4b3241c544"
    assert isinstance(data['floor_price'], float)
    assert data['banner_graphic'] == "https://open-graph.opensea.io/v1/collections/azuki"

def test_get_erc721_count_per_transaction():
    nft_per_tx_dict, total_owned, mint_amount, buy_amount, sell_amount = get_erc721_transactions("0x4e435D2d6fCe29Ab31f9841b98D09872869C6bC0", "0x39ee2c7b3cb80254225884ca001f57118c8f21b6")
    assert nft_per_tx_dict['0x2f3b246f5cf9bc4fd136fd27cfee6178c72537185c272d75d26d21322ae88e70'] == 1
    assert nft_per_tx_dict['0x997542bdc8c3c5618c8315c287a24ddb7b121f6f3169eb15b38417c8d9fb50c3'] == 1
    assert nft_per_tx_dict['0xc40e917ad77fac7405ba7bd2d1ae8cb2e506d43375e97f851fcb761e74bc3d94'] == -1
    assert nft_per_tx_dict['0xd1c83b6850d45f2eb213c7563f010b68cb82a4dbc59d567a0a373c038d95d0df'] == -1
    assert total_owned == 0
    assert mint_amount == 0
    assert buy_amount == 2
    assert sell_amount == 2

def test_get_transaction_details():
    # normal case of selling a single nft
    details = get_transaction_details("0x4e435D2d6fCe29Ab31f9841b98D09872869C6bC0", "0xc40e917ad77fac7405ba7bd2d1ae8cb2e506d43375e97f851fcb761e74bc3d94")
    assert details["gas_spent"] == 0
    assert details["eth_spent"] == 0
    assert details["eth_gained"] == 0.8756

    # weth offers taken
    details = get_transaction_details("0x7d93491bE90281479be4e1128fc9b028Fd69d697", "0x3ea74c3e5b563b5dd51d325c3f4708978152b87d8d83fb2e052b83f549663177")
    assert details["gas_spent"] == 0.006471744
    assert details["eth_spent"] == (0.0725 + 0.2175)
    assert details["eth_gained"] == 2.9

    # gem sweep, buying 6 nft
    details = get_transaction_details("0x4e435d2d6fce29ab31f9841b98d09872869c6bc0", "0xa6fdd02a408ee7ec904da4bc51d114847925acc43dbc4e1982aeae5855acbeb4")
    assert details["gas_spent"] == 0.011991168982773305
    assert details["eth_spent"] == 0.236976
    assert details["eth_gained"] == 0

    # mint 10 nfts for 0.1 eth
    details = get_transaction_details("0x4e435d2d6fce29ab31f9841b98d09872869c6bc0", "0x5ebbf1bb0b9216ebbb843d65f4d29210b731ebc8e9cc5e88b2d9f859be7904bb")
    assert details["gas_spent"] == 0.06703817116182656
    assert details["eth_spent"] == 0.1
    assert details["eth_gained"] == 0

def test_get_eth_price_with_date():
    test_dates = ["21-07-2022", "23-07-2022", "24-07-2022"]
    test_results = [1527.41, 1536.12, 1552.5]
    for index, date in enumerate(test_dates):
        result = get_eth_price_with_date(date)
        assert result == test_results[index]
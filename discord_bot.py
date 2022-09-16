from profit_loss import get_pl_from_wallets
from dotenv import dotenv_values
import discord
import os

here = os.path.dirname(os.path.abspath(__file__))
config = dotenv_values(os.path.join(here, ".env"))

eth_decimal = 3

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'{client.user} is now running.')

@client.event
async def on_message(message):
    username = str(message.author).split("#")[0]
    user_id = int(message.author.id)
    user_message = str(message.content)
    if message.author == client.user:
        return
    if message.channel.id == int(config['discord_target_channel']):
        # chat logging
        print(f"[{message.channel.id}] {username}: {user_message}") 
        args = user_message.lower().split(" ")
        if args[0][0] != "!":
            return
        if len(args) < 3:
            await message.reply("⚠️ 指令錯誤！")
            return
        if args[0] == "!pl":
            os_link = args[1]
            wallets = args[2:]
            clean_wallets = []
            for wallet in wallets:
                if len(wallet) != 42 or wallet[:2] != "0x":
                    await message.reply(f"⚠️ 錢包無效！ ({wallet})")
                    return
                if wallet not in clean_wallets:
                    clean_wallets.append(wallet)
            if len(clean_wallets) > 5:
                await message.reply(f"⚠️ 太多錢包！ ({wallet})")
                return
            loading_msg = await message.reply(f"⏳ 正在從區塊鏈取得數據，請稍等...")
            data = {}
            try:
                # eth_price_today, project_name, project_floor, project_image_url, total_nft_count, total_trade_count, free_and_mint_count, buy_count, sell_count, mint_eth, buy_eth, cost_eth, sale_eth
                data = await get_pl_from_wallets(os_link, clean_wallets)
            except:
                await message.reply("⚠️ 數據取得錯誤！")
                return
            if data == None:
                await message.reply("⚠️ 錯誤！")
                return

            eth = data["eth_price_today"]

            tokens_minted = data['free_and_mint_count']
            mint_costs_eth = float(data['mint_eth'])
            mint_costs_usd = int(mint_costs_eth * eth)
            avg_mint_costs_eth = tokens_minted and mint_costs_eth / tokens_minted
            avg_mint_costs_usd = int(avg_mint_costs_eth * eth)

            tokens_bought = data['buy_count']
            buy_costs_eth = float(data['cost_eth'])
            buy_costs_usd = int(buy_costs_eth * eth)
            avg_buy_costs_eth = tokens_bought and buy_costs_eth / tokens_bought
            avg_buy_costs_usd = int(avg_buy_costs_eth * eth)

            tokens_sold = data['sell_count']
            total_sold_amount_eth = float(data['sale_eth'])
            total_sold_amount_usd = int(total_sold_amount_eth * eth)
            avg_sold_price_eth = tokens_sold and total_sold_amount_eth / tokens_sold
            avg_sold_price_usd = int(avg_sold_price_eth * eth)

            tokens_held = data['total_nft_count']
            floor_price_eth = data['project_floor']
            floor_price_usd = int(data['project_floor'] * eth)
            est_value_eth = floor_price_eth * tokens_held
            est_value_usd = est_value_eth * eth

            current_pl_eth = total_sold_amount_eth - buy_costs_eth - mint_costs_eth
            current_pl_usd = int(current_pl_eth * eth)

            potential_pl_eth = est_value_eth + current_pl_eth
            potential_pl_usd = int(potential_pl_eth * eth)

            roi = buy_costs_eth + mint_costs_eth and round(((current_pl_eth) / (buy_costs_eth + mint_costs_eth) * 100), 1)

            if roi == 0:
                roi = "GAS ONLY 🔥"
                
            wallet_msg = "> 錢包:"
            for wallet in wallets:
                wallet_msg += f"\n> {wallet[:10]}...{wallet[-10:]}"

            embed = discord.Embed(title=f"{username} 在 {data['project_name']} 的 P&L", description=wallet_msg, color=discord.Colour.purple())
            embed.set_footer(text="Powered by https://twitter.com/Jaasonft", icon_url="https://i.imgur.com/6ZaSEwK.png")
            embed.add_field(name="鑄造 \u200B \u200B \u200B \u200B", value=f"`{tokens_minted}`", inline=True)
            embed.add_field(name="鑄造價 \u200B \u200B \u200B \u200B", value=f"`Ξ{round(mint_costs_eth, eth_decimal)}  (${mint_costs_usd})`")
            embed.add_field(name="平均鑄造價", value=f"`Ξ{round(avg_mint_costs_eth, eth_decimal)} (${avg_mint_costs_usd})`")
            embed.add_field(name="買入", value=f"`{tokens_bought}`")
            embed.add_field(name="買入價", value=f"`Ξ{round(buy_costs_eth, eth_decimal)} (${buy_costs_usd})`")
            embed.add_field(name="平均買入價", value=f"`Ξ{round(avg_buy_costs_eth, eth_decimal)} (${avg_buy_costs_usd})`")
            embed.add_field(name="賣出", value=f"`{tokens_sold}`")
            embed.add_field(name="賣出價", value=f"`Ξ{round(total_sold_amount_eth, eth_decimal)} (${total_sold_amount_usd})`")
            embed.add_field(name="平均賣出價", value=f"`Ξ{round(avg_sold_price_eth, eth_decimal)} (${avg_sold_price_usd})`")
            embed.add_field(name="持有", value=f"`{tokens_held}`")
            embed.add_field(name="估值", value=f"`Ξ{round(est_value_eth, eth_decimal)} (${est_value_usd})`")
            embed.add_field(name="地板價", value=f"`Ξ{round(floor_price_eth, eth_decimal)} (${floor_price_usd})`")
            embed.add_field(name="目前 P&L", value=f"`Ξ{round(current_pl_eth, eth_decimal)} (${current_pl_usd})`")
            embed.add_field(name="潛在 P&L", value=f"`Ξ{round(potential_pl_eth, eth_decimal)} (${potential_pl_usd})`")
            embed.add_field(name="已實現 ROI", value=f"`{roi}%`")
            embed.set_image(url=data['project_image_url'])
            embed.set_thumbnail(url="https://i.imgur.com/FqJzlGW.png")
            await message.reply(embed=embed)
            await loading_msg.delete()

def start_bot():
    client.run(config["discord_bot_token"])

if __name__ == '__main__':
    start_bot()
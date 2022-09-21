from profit_loss import get_pl_from_wallets
from dotenv import dotenv_values
import discord
import os

from profit_loss_v2 import get_pl

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
                await message.reply(f"⚠️ 超過五個錢包！ ({wallet})")
                return
            loading_msg = await message.reply(f"⏳ 正在從區塊鏈取得數據，請稍等...")
            data = {}
            try:
                data = await get_pl(os_link, clean_wallets)
            except:
                await message.reply("⚠️ 數據取得錯誤！")
                print(data)
                return
            if data == None:
                await message.reply("⚠️ 錯誤！沒有數據。")
                return
            wallet_msg = "> 錢包:"
            for wallet in wallets:
                wallet_msg += f"\n> {wallet[:10]}...{wallet[-10:]}"

            embed = discord.Embed(title=f"P&L 數據 - {data['project_name']}", description=wallet_msg, color=discord.Colour.purple())
            embed.set_footer(text="Powered by https://twitter.com/Jaasonft", icon_url="https://i.imgur.com/6ZaSEwK.png")
            embed.add_field(name="鑄造數 \u200B \u200B \u200B \u200B", value=f"`{data['total_mint_amount']}`", inline=True)
            embed.add_field(name="地板價", value=f"`Ξ{round(data['project_floor'], eth_decimal)} (${data['project_floor_usd']})`")
            embed.add_field(name="合共氣費", value=f"`Ξ{round(data['eth_gas_spent'], eth_decimal)} (${data['usd_gas_spent']})`")
            embed.add_field(name="買入數", value=f"`{data['total_buy_amount']}`")
            embed.add_field(name="合共買入", value=f"`Ξ{round(data['eth_spent'], eth_decimal)} (${data['usd_spent']})`")
            embed.add_field(name="平均買入價", value=f"`Ξ{round(data['eth_avg_buy_price'], eth_decimal)} (${data['usd_avg_buy_price']})`")
            embed.add_field(name="賣出數", value=f"`{data['total_sell_amount']}`")
            embed.add_field(name="合共賣出", value=f"`Ξ{round(data['eth_gained'], eth_decimal)} (${data['usd_gained']})`")
            embed.add_field(name="平均賣出價", value=f"`Ξ{round(data['eth_avg_sell_price'], eth_decimal)} (${data['usd_avg_sell_price']})`")
            embed.add_field(name="持有數", value=f"`{data['total_nft_owned']}`")
            embed.add_field(name="持有估值", value=f"`Ξ{round(data['eth_holding_value'], eth_decimal)} (${data['usd_holding_value']})`")
            embed.add_field(name="潛在 P&L", value=f"`Ξ{round(data['potential_pl_eth'], eth_decimal)} (${data['potential_pl_usd']})`")
            embed.add_field(name="目前 P&L", value=f"`Ξ{round(data['realised_pl_eth'], eth_decimal)} (${data['realised_pl_usd']})`")
            embed.add_field(name="已實現 ROI", value=f"`{round(data['roi'], 2)}%`")
            embed.set_image(url=data['project_image_url'])
            embed.set_thumbnail(url="https://i.imgur.com/FqJzlGW.png")
            await message.reply(embed=embed)
            await loading_msg.delete()

def start_bot():
    client.run(config["discord_bot_token"])

if __name__ == '__main__':
    start_bot()
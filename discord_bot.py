from image_generation import profit_image
from profit_loss_v2 import get_pl
from discord import app_commands
from discord.ext import commands
from dotenv import dotenv_values
import discord, os, json, i18n
from io import BytesIO

here = os.path.dirname(os.path.abspath(__file__))
config = dotenv_values(os.path.join(here, ".env"))

bot = commands.Bot(command_prefix = "!", intents=discord.Intents.default())

i18n.load_path.append(os.path.join(here, "locale"))
i18n.set('filename_format', '{locale}.{format}')
i18n.set('file_format', 'json')

@bot.event
async def on_ready():
    print(f'>>> Loading commands...')
    try:
        synced = await bot.tree.sync()
        print(f">>> Synced {len(synced)} command(s)")
        print(f'>>> Bot running...')
    except Exception as e:
        print(e)

@bot.tree.command(name="pl_bot")
@commands.has_permissions(administrator=True)
@app_commands.describe(option="Option", value="Value")
async def language(interaction: discord.Integration, option: str, value: str=None):
    if option.lower() == "show":
        settings = get_settings(interaction.guild_id)
        await interaction.response.send_message(f"{settings}")
    elif option.lower() == "set":
        await interaction.response.send_message(f"Soon")

def get_settings(guild_id):
    with open(os.path.join(here, "settings.json"), "r") as f:
        settings = json.load(f)
    return settings[str(guild_id)]

def set_settings(guild_id, value):
    with open(os.path.join(here, "settings.json"), "r") as f:
        settings = json.load(f)
    settings[str(guild_id)] = {}
    settings[str(guild_id)]["language"] = value["language"]
    settings[str(guild_id)]["eth_decimal"] = value["eth_decimal"]
    with open(os.path.join(here, "settings.json"), "w") as f:
        json.dump(settings, f)

@bot.event
async def on_guild_join(guild):
    default_settings = {"language": "en", "eth_decimal": 3, "brand_image": "", "template": "", "font": "", "bold_font": "", "magic": []}
    set_settings(str(guild.id), default_settings)

@bot.tree.command(name="profit")
@app_commands.describe(os_link="Opensea URL", wallet_addresses="Wallet Address")
async def profit(interaction: discord.Integration, os_link: str, wallet_addresses: str):
    await interaction.response.defer(ephemeral=True)
    user = await bot.fetch_user(interaction.user.id)
    print(f"> [{interaction.guild.name}] {interaction.user.name} requested {os_link} for wallets {wallet_addresses}")
    settings = get_settings(interaction.guild_id)
    i18n.set('locale', settings['language'])

    if "opensea.io" not in os_link:
        await interaction.followup.send(f"{i18n.t('invalid_os_url', os_url=os_link)}", ephemeral=True)
        return
    clean_wallets = []
    for wallet in wallet_addresses.split(" "):
        if len(wallet) != 42 or wallet[:2] != "0x":
            await interaction.followup.send(f"{i18n.t('invalid_wallet', wallet=wallet)}", ephemeral=True)
            return
        if wallet not in clean_wallets:
            clean_wallets.append(wallet.lower())
    
    
    try:
        data = await get_pl(os_link, clean_wallets)
    except:
        await interaction.followup.send(f"{i18n.t('data_error')}", ephemeral=True)
        print(data)
        return
    
    eth_decimal = settings['eth_decimal']
    embed = discord.Embed(title=f"{i18n.t('embed_title', project_name=data['project_name'])}", description=f"{i18n.t('amount_of_wallets', total_wallets=len(clean_wallets))}", color=discord.Colour.purple())
    embed.set_footer(text="Powered by https://twitter.com/Jaasonft", icon_url="https://i.imgur.com/6ZaSEwK.png")
    embed.add_field(name=f"{i18n.t('mint_amount')} \u200B \u200B \u200B \u200B", value=f"`{data['total_mint_amount']}`", inline=True)
    embed.add_field(name=f"{i18n.t('floor_price')}", value=f"`Ξ{round(data['project_floor'], eth_decimal)} (${data['project_floor_usd']})`")
    embed.add_field(name=f"{i18n.t('gas_spent')}", value=f"`Ξ{round(data['eth_gas_spent'], eth_decimal)} (${data['usd_gas_spent']})`")
    embed.add_field(name=f"{i18n.t('buy_amount')}", value=f"`{data['total_buy_amount']}`")
    embed.add_field(name=f"{i18n.t('buy_value')}", value=f"`Ξ{round(data['eth_spent'], eth_decimal)} (${data['usd_spent']})`")
    embed.add_field(name=f"{i18n.t('avg_buy_price')}", value=f"`Ξ{round(data['eth_avg_buy_price'], eth_decimal)} (${data['usd_avg_buy_price']})`")
    embed.add_field(name=f"{i18n.t('sell_amount')}", value=f"`{data['total_sell_amount']}`")
    embed.add_field(name=f"{i18n.t('sell_value')}", value=f"`Ξ{round(data['eth_gained'], eth_decimal)} (${data['usd_gained']})`")
    embed.add_field(name=f"{i18n.t('avg_sell_price')}", value=f"`Ξ{round(data['eth_avg_sell_price'], eth_decimal)} (${data['usd_avg_sell_price']})`")
    embed.add_field(name=f"{i18n.t('amount_holding')}", value=f"`{data['total_nft_owned']}`")
    embed.add_field(name=f"{i18n.t('holding_value')}", value=f"`Ξ{round(data['eth_holding_value'], eth_decimal)} (${data['usd_holding_value']})`")
    embed.add_field(name=f"{i18n.t('potential_pl')}", value=f"`Ξ{round(data['potential_pl_eth'], eth_decimal)} (${data['potential_pl_usd']})`")
    embed.add_field(name=f"{i18n.t('current_pl')}", value=f"`Ξ{round(data['realised_pl_eth'], eth_decimal)} (${data['realised_pl_usd']})`")
    embed.add_field(name=f"{i18n.t('overall_gain')}", value=f"`Ξ{round(data['potential_pl_eth'] + data['eth_holding_value'], eth_decimal)} (${data['potential_pl_usd'] + data['usd_holding_value']})`")
    embed.add_field(name=f"{i18n.t('realised_pl')}", value=f"`{round(data['roi'], 2)}%`")
    embed.set_thumbnail(url=settings['brand_image'])

    if settings['template'] == "":
        embed.set_image(url=data['project_image_url'])
        await interaction.followup.send(embed=embed, ephemeral=True)
    else:
        bytes = BytesIO()
        img = profit_image(user, data, settings)
        img.save(bytes, 'jpeg', quality=100)
        bytes.seek(0)
        image = discord.File(bytes, filename="image.jpg")
        # embed.set_image(url="attachment://image.jpg")
        await interaction.followup.send(embed=embed, file=image, ephemeral=True)

def start_bot():
    bot.run(config["discord_bot_token"])

if __name__ == '__main__':
    start_bot()
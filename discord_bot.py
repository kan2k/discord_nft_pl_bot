from image_generation import profit_image
from profit_loss_v2 import get_pl
from discord import app_commands
from discord.ext import commands
from dotenv import dotenv_values
import discord, os, json, i18n, requests, traceback
from io import BytesIO
from sqlalchemy import create_engine, Column, String, Integer, CHAR, PickleType
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import sessionmaker

here = os.path.dirname(os.path.abspath(__file__))

Base = declarative_base()

class User(Base):
    __tablename__ = "wallets"
    discord_id = Column("discord_id", Integer, primary_key=True)
    profile = Column("profile", MutableDict.as_mutable(PickleType))

    def __init__(self, discord_id, profile):
        self.discord_id = discord_id
        self.profile = profile
    def __repr__(self):
        return f"{self.discord_id} {self.profile}"

engine = create_engine("sqlite:///" + os.path.join(here, "database.db"))
Base.metadata.create_all(bind=engine)

Session = sessionmaker(bind=engine)
session = Session()


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

@bot.tree.command(name="wallet")
@app_commands.describe(action="action", profile="profile", wallets="wallets")
async def profit(interaction: discord.Integration, action: str, profile: str=None, wallets: str=None):
    await interaction.response.defer(ephemeral=True)
    discord_user = await bot.fetch_user(interaction.user.id)
    print(f"> [{interaction.guild.name}] {interaction.user.name} {action} {profile} {wallets}")
    settings = get_settings(interaction.guild_id)
    i18n.set('locale', settings['language'])
    user = session.query(User).get(discord_user.id)
    if action.lower() == 'view':
        if not profile:
            embed = discord.Embed(title=f"{i18n.t('wallet_embed_title', discord_name=discord_user.name)}", description=f"", color=discord.Colour.purple())
            embed.set_footer(text="Powered by Jaason#4444 (https://twitter.com/Jaasonft)", icon_url="https://i.imgur.com/bOEIgEn.png")
            wallet_message = ""
            for profile_key in user.profile.keys():
                wallet_count = len(user.profile[profile_key])
                wallet_message += f"`{profile_key} ({wallet_count} wallets)` "
            embed.add_field(name=f"{i18n.t('wallet_profile')}", value=f"{wallet_message}")
            embed.set_thumbnail(url=settings['brand_image'])
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            embed = discord.Embed(title=f"{i18n.t('wallet_embed_title', discord_name=discord_user.name)}", description=f"", color=discord.Colour.purple())
            embed.set_footer(text="Powered by Jaason#4444 (https://twitter.com/Jaasonft)", icon_url="https://i.imgur.com/bOEIgEn.png")
            wallet_message = ""
            try:
                for wallet in user.profile[profile]:
                    wallet_message += f"`{wallet}`\n"
            except:
                await interaction.followup.send(f"{i18n.t('profile_does_not_exist', profile=profile)}", ephemeral=True)
                return
            wallet_message += f"\n`{i18n.t('total_wallets', count=len(user.profile[profile]))}`"
            embed.add_field(name=f"{i18n.t('wallets_for_profile', profile=profile)}", value=f"{wallet_message}")
            embed.set_thumbnail(url=settings['brand_image'])
            await interaction.followup.send(embed=embed, ephemeral=True)
        return
    elif action.lower() == 'add':
        if not profile or not wallets:
            await interaction.followup.send(f"{i18n.t('missing_parameter')}", ephemeral=True)
            return
        
        try:
            wallets = clean_wallets(wallets.split(" "))
        except Exception as e:
            await interaction.followup.send(f"{i18n.t('invalid_wallet', wallet=e)}", ephemeral=True)
            return

        if user:
            try:
                # profile wallet edit
                user.profile[profile] = list(set(user.profile[profile] + wallets))
                await interaction.followup.send(f"{i18n.t('profile_edited', profile=profile)}", ephemeral=True)
            except:
                # profile wallet add
                user.profile[profile] = wallets
                await interaction.followup.send(f"{i18n.t('profile_created', profile=profile)}", ephemeral=True)
        else:
            # profile wallet create
            new_profile = {}
            new_profile[profile] = wallets
            new_user = User(discord_user.id, new_profile)
            session.add(new_user)
            await interaction.followup.send(f"{i18n.t('profile_created', profile=profile)}", ephemeral=True)

    elif action.lower() == 'delete':
        if not profile and not wallets:
            await interaction.followup.send(f"{i18n.t('missing_parameter')}", ephemeral=True)
            return

        if profile and not wallets:
            try:
                del user.profile[profile]
            except:
                await interaction.followup.send(f"{i18n.t('profile_does_not_exist', profile=profile)}", ephemeral=True)
                return
            await interaction.followup.send(f"{i18n.t('deleted_profile', profile=profile)}", ephemeral=True)
            return

        try:
            wallets = clean_wallets(wallets.split(" "))
        except Exception as e:
            await interaction.followup.send(f"{i18n.t('invalid_wallet', wallet=e)}", ephemeral=True)
            return

        if profile and wallets:
            message = ""
            for wallet in wallets:
                try:
                    user.profile[profile].remove(wallet)
                    message += f"`{wallet}` "
                except:
                    continue
            await interaction.followup.send(f"{i18n.t('deleted_wallets_profile', message=message, profile=profile)}", ephemeral=True)
    try:
        session.commit()
    except Exception as e:
        print("DATABASE ERROR:",e)
        session.rollback()
        
# @bot.tree.command(name="tx")
# @app_commands.describe(collection="contract address or Opensea URL", wallet_profile="Wallet Profile")

@bot.tree.command(name="profit")
@app_commands.describe(collection="contract address or Opensea URL", wallet_profile="Wallet Profile")
async def profit(interaction: discord.Integration, collection: str, wallet_profile: str):
    await interaction.response.defer(ephemeral=True)
    discord_user = await bot.fetch_user(interaction.user.id)
    print(f"> [{interaction.guild.name}] {interaction.user.name} requested {collection} for wallets {wallet_profile}")
    settings = get_settings(interaction.guild_id)

    tracking = requests.get(f"https://api.countapi.xyz/hit/{settings['tracking_id']}")

    i18n.set('locale', settings['language'])

    if "opensea.io" not in collection and not collection.startswith('0x') and len(collection) != 42:
        await interaction.followup.send(f"{i18n.t('invalid_collection', collection=collection)}", ephemeral=True)
        return

    user = session.query(User).get(discord_user.id)
    try:
        wallets = user.profile[wallet_profile]
    except:
        await interaction.followup.send(f"{i18n.t('invalid_profile', profile=wallet_profile)}", ephemeral=True)
        return

    try:
        # data = await run_blocking(get_pl, collection, clean_wallets)
        data = await get_pl(collection, wallets)
    except Exception as e:
        print(traceback.format_exc())
        await interaction.followup.send(f"{i18n.t('data_error')} `({e})`", ephemeral=True)
        return

    eth_decimal = settings['eth_decimal']

    message_1 = i18n.t('amount_of_wallets', total_wallets=len(wallets))
    message_2 = ""

    if data['break_even_amount'] > 0:
        message_2 = i18n.t('break_even_amount', break_even_amount=round(data['break_even_amount'])) + "\n"
    if data['break_even_amount'] > data['total_nft_owned']:
        message_2 = ""
    if data['break_even_amount'] < 0:
        message_2 = i18n.t('already_break_even')

    if data['break_even_price'] > 0:
        message_2 += i18n.t('break_even_price', break_even_price=round(data['break_even_price'], eth_decimal))

    embed = discord.Embed(title=f"{i18n.t('embed_title', project_name=data['project_name'])}", description=f"{message_1}\n{message_2}", color=discord.Colour.purple())
    embed.set_footer(text="Powered by Jaason#4444 (https://twitter.com/Jaasonft)", icon_url="https://i.imgur.com/bOEIgEn.png")
    embed.add_field(name=f"{i18n.t('mint_amount')} \u200B \u200B \u200B \u200B", value=f"`{data['total_mint_amount']}`", inline=True)
    embed.add_field(name=f"{i18n.t('mint_spent')}", value=f"`Ξ{round(data['eth_mint_spent'], eth_decimal)} (${data['usd_mint_spent']})`")
    embed.add_field(name=f"{i18n.t('avg_mint_spent')}", value=f"`Ξ{round(data['eth_avg_mint_price'], eth_decimal)} (${data['usd_avg_mint_price']})`")
    embed.add_field(name=f"{i18n.t('buy_amount')}", value=f"`{data['total_buy_amount']}`")
    embed.add_field(name=f"{i18n.t('buy_value')}", value=f"`Ξ{round(data['eth_buy_spent'], eth_decimal)} (${data['usd_buy_spent']})`")
    embed.add_field(name=f"{i18n.t('avg_buy_price')}", value=f"`Ξ{round(data['eth_avg_buy_price'], eth_decimal)} (${data['usd_avg_buy_price']})`")
    embed.add_field(name=f"{i18n.t('gas_spent')}", value=f"`Ξ{round(data['eth_gas_spent'], eth_decimal)} (${data['usd_gas_spent']})`")
    embed.add_field(name=f"{i18n.t('total_spent')}", value=f"`Ξ{round(data['eth_total_spent'], eth_decimal)} (${data['usd_total_spent']})`")
    embed.add_field(name=f"\u200B", value=f"\u200B")
    embed.add_field(name=f"{i18n.t('sell_amount')}", value=f"`{data['total_sell_amount']}`")
    embed.add_field(name=f"{i18n.t('sell_value')}", value=f"`Ξ{round(data['eth_gained'], eth_decimal)} (${data['usd_gained']})`")
    embed.add_field(name=f"{i18n.t('avg_sell_price')}", value=f"`Ξ{round(data['eth_avg_sell_price'], eth_decimal)} (${data['usd_avg_sell_price']})`")
    embed.add_field(name=f"{i18n.t('amount_holding')}", value=f"`{data['total_nft_owned']}`")
    embed.add_field(name=f"{i18n.t('floor_price')}", value=f"`Ξ{round(data['project_floor'], eth_decimal)} (${data['project_floor_usd']})`")
    embed.add_field(name=f"{i18n.t('holding_value')}", value=f"`Ξ{round(data['eth_holding_value'], eth_decimal)} (${data['usd_holding_value']})`")
    embed.add_field(name=f"{i18n.t('potential_pl')}", value=f"`Ξ{round(data['potential_pl_eth'], eth_decimal)} (${data['potential_pl_usd']})`")
    embed.add_field(name=f"{i18n.t('current_pl')}", value=f"`Ξ{round(data['realised_pl_eth'], eth_decimal)} (${data['realised_pl_usd']})`")
    embed.add_field(name=f"{i18n.t('roi')}", value=f"`{round(data['roi'], 2)}%`")
    embed.set_thumbnail(url=settings['brand_image'])

    if settings['template'] == "":
        embed.set_image(url=data['project_image_url'])
        await interaction.followup.send(embed=embed, ephemeral=True)
    else:
        bytes = BytesIO()
        img = profit_image(discord_user, data, settings)
        img.save(bytes, 'jpeg', quality=100)
        bytes.seek(0)
        image = discord.File(bytes, filename="image.jpg")
        # embed.set_image(url="attachment://image.jpg")
        await interaction.followup.send(embed=embed, file=image, ephemeral=True)

# async def run_blocking(blocking_func: typing.Callable, *args, **kwargs) -> typing.Any:
#     """Runs a blocking function in a non-blocking way"""
#     func = functools.partial(blocking_func, *args, **kwargs) # `run_in_executor` doesn't support kwargs, `functools.partial` does
#     return await bot.loop.run_in_executor(None, func)


def clean_wallets(list_of_wallets):
    clean_wallets = []
    for wallet in list_of_wallets:
        if len(wallet) != 42 or wallet[:2] != "0x":
            raise Exception(f"{wallet}")
        if wallet not in clean_wallets:
            clean_wallets.append(wallet.lower())
    return clean_wallets

if __name__ == '__main__':
    bot.run(config["discord_bot_token"])
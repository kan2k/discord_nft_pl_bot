import os
import base64
import pandas as pd
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import requests

here = os.path.dirname(os.path.abspath(__file__))

def profit_image(user, data, template_filename, font, magic, eth_decimal):
    avatar_url = str(user.avatar)
    discord_name = str(user.name)
    avatar_url = avatar_url.replace("size=1024", "size=256")
    try:
        response = requests.get(avatar_url)
    except:
        return
    icon = Image.open(BytesIO(response.content))
    font_location = os.path.join(here, "resources", "fonts", font)

    mega_font = ImageFont.truetype(font_location, size=120)
    big_font = ImageFont.truetype(font_location, size=70)
    medium_font = ImageFont.truetype(font_location, size=50)
    small_font = ImageFont.truetype(font_location, size=40)

    template = Image.open(os.path.join(here, "resources", "templates", template_filename))
    
    template = template.resize((1000, 1000), Image.ANTIALIAS)
    W, H = template.size

    # crop to circle and draw discord icon
    icon = icon.resize(magic[0], Image.ANTIALIAS)
    mask_im = Image.new("L", icon.size, 0)
    draw = ImageDraw.Draw(mask_im)
    draw.ellipse((0, 0, icon.size), fill=255)
    img = template.copy()
    img.paste(icon, magic[1], mask_im)

    # draw discord name
    draw = ImageDraw.Draw(img)
    draw.text(magic[2], str(discord_name), font=small_font, fill='white')

    # draw project name
    draw.text(magic[3], str(data['project_name']), font=medium_font, fill='white')

    # draw data
    draw.text(magic[4], str(data['total_buy_amount']), font=small_font, fill='white')
    draw.text(magic[5], f"{round(data['eth_spent'], eth_decimal)} ETH (${data['usd_spent']})", font=small_font, fill='white')
    draw.text(magic[6], f"{round(data['eth_avg_sell_price'], eth_decimal)} ETH (${data['usd_avg_sell_price']})", font=small_font, fill='white')

    draw.text(magic[7], str(data['total_nft_owned']), font=medium_font, fill='white')
    draw.text(magic[8], f"{round(data['eth_gained'], eth_decimal)} ETH (${data['usd_gained']})", font=medium_font, fill='white')
    draw.text(magic[9], f"{round(data['eth_holding_value'], eth_decimal)} ETH (${data['usd_holding_value']})", font=medium_font, fill='white')
    draw.text(magic[10], f"{round((data['eth_gained'] + data['eth_holding_value']), eth_decimal)} ETH", font=big_font, fill='white')

    return img


if __name__ == '__main__':
    # magic = [(icon size, icon size), (icon x, icon y), (name x, name y), (project name x, project name y), 
    # (buy amount x, buy amount y), (eth_spent x, eth_spent y), (eth_avg_sell_price x, eth_avg_sell_price y),
    # (total_nft_owned x, total_nft_owned y), (eth_gained x, eth_gained y), (eth_holding_value x, eth_holding_value y),
    # (potential_pl_eth x, potential_pl_eth y)]
    magic = [[175, 175], [45, 755], [240, 830], [80, 120], [360, 230], [360, 292], [360, 352], [370, 425], [530, 492], [530, 562], [635, 632]]
    data = {'project_name': 'SAN Origin', 'project_floor': 0.0587, 'project_floor_usd': 75, 'project_image_url': 'https://open-graph.opensea.io/v1/collections/san-origin', 'total_nft_owned': 3, 'total_trade_count': 4, 'total_mint_amount': 0, 'total_buy_amount': 6, 'total_sell_amount': 3, 'eth_gas_spent': 0.012, 'usd_gas_spent': 15, 'eth_spent': 0.237, 'eth_gained': 0.203, 'usd_spent': 305, 'usd_gained': 261, 'eth_avg_buy_price': 0.039, 'usd_avg_buy_price': 51, 'eth_avg_sell_price': 0.068, 'usd_avg_sell_price': 87, 'eth_holding_value': 10.176, 'usd_holding_value': 226, 'realised_pl_eth': -0.034, 'realised_pl_usd': -44, 'potential_pl_eth': 0.142, 'potential_pl_usd': 182, 'roi': 14.432685166430362}
    response = requests.get("https://cdn.discordapp.com/avatars/214359518740611072/095fe73005641221f8e6fac67fe7f579.png?size=256")
    icon = Image.open(BytesIO(response.content))
    img = profit_image("Jaason#4444", icon, data, "origins_en_template.jpg", "PowerGrotesk-Regular.ttf", magic, 2)
    img.save('test.jpg')
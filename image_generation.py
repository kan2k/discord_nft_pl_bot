import os
import base64
import pandas as pd
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import requests

here = os.path.dirname(os.path.abspath(__file__))
font_location = os.path.join(here, "resources", "PowerGrotesk-Regular.ttf")

def profit_image(user, data):
    print(user.avatar)
    avatar_url = str(user.avatar)
    discord_name = str(user.name)
    avatar_url = avatar_url.replace("size=1024", "size=128")
    try:
        response = requests.get(avatar_url)
    except:
        return
    icon = Image.open(BytesIO(response.content))
    return generate_pil_image(discord_name, icon, data)

def generate_pil_image(discord_name, icon, data):
    big_font = ImageFont.truetype(font_location, size=120)
    font_100 = ImageFont.truetype(font_location, size=100)
    font_58 = ImageFont.truetype(font_location, size=58)
    font_40 = ImageFont.truetype(font_location, size=40)

    template = Image.open(os.path.join(here, "resources", "potential_template.jpg"))

    if data['potential_pl_eth'] < data['realised_pl_eth']:
        template = Image.open(os.path.join(here, "resources", "realised_template.jpg"))
    
    template = template.resize((1000, 1000), Image.ANTIALIAS)
    W, H = template.size

    # crop to circle and draw discord icon
    icon = icon.resize((180, 180), Image.ANTIALIAS)
    mask_im = Image.new("L", icon.size, 0)
    draw = ImageDraw.Draw(mask_im)
    draw.ellipse((0, 0, icon.size), fill=255)
    img = template.copy()
    img.paste(icon, (30, 745), mask_im)

    # draw project name
    draw = ImageDraw.Draw(img)
    draw.text((55, 80), str(data['project_name']), font=big_font, fill='white')

    # draw discord name
    draw.text((240, 813), str(discord_name), font=font_40, fill='white')

    # draw data
    draw.text((240, 227), str(data['total_buy_amount']), font=font_40, fill='white')
    draw.text((240, 227 + 60), f"{data['eth_spent']} ETH (${data['usd_spent']})", font=font_40, fill='white')
    draw.text((240, 227 + 118), f"{data['eth_avg_sell_price']} ETH (${data['usd_avg_sell_price']})", font=font_40, fill='white')
    draw.text((330, 418), f"{data['eth_gained']} ETH (${data['usd_gained']})", font=font_58, fill='white')
    draw.text((280, 478), str(data['total_nft_owned']), font=font_58, fill='white')
    draw.text((350, 560), f"{data['potential_pl_eth']} ETH", font=font_100, fill='white')

    return img


def serve_pil_image(discord_name, discord_id, projects, roi, total):
    img = generate_pil_image(discord_name, discord_id, projects, roi, total)
    bytes = BytesIO()
    img.save(bytes, 'jpeg', quality=100)
    bytes.seek(0)
    img = base64.b64encode(bytes.getvalue()).decode('ascii')
    img_tag = f'<img src="data:image/jpg;base64,{img}" class="img-fluid"/>'
    return img_tag, img

import os
import base64
import pandas as pd
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import requests

here = os.path.dirname(os.path.abspath(__file__))

def profit_image(user, data, settings):
    avatar_url = str(user.avatar)
    discord_name = f"{user.name}#{user.discriminator}"
    avatar_url = avatar_url.replace("size=1024", "size=256")
    try:
        response = requests.get(avatar_url)
    except:
        return
    icon = Image.open(BytesIO(response.content))
    return generate_image(discord_name, icon, data, settings)


def generate_image(discord_name, icon, data, settings):
    template = settings['template']
    font = settings["font"]
    bold_font = settings["bold_font"]
    magic = settings["magic"]
    eth_decimal = settings["eth_decimal"]
    width = settings["width"]
    height = settings["height"]
    font = os.path.join(here, "resources", "fonts", font)
    bfont = os.path.join(here, "resources", "fonts", bold_font)

    template = Image.open(os.path.join(here, "resources", "templates", template))
    
    template = template.resize((width, height), Image.ANTIALIAS)

    # crop accordingly and draw discord icon onto template
    img = template.copy()
    icon = icon.resize((magic[2][0], magic[2][1]), Image.ANTIALIAS)
    mask_im = Image.new("L", icon.size, 0)
    draw = ImageDraw.Draw(mask_im)
    if magic[2][2] == "circle":
        draw.ellipse((0, 0, icon.size), fill=255)
    elif magic[2][2] == "tbp_special":
        # icon.size = 155 , 155
        points = [(20, 0), (0, 20), (0, 154), (134, 154), (154, 134), (154, 0), (20, 0)]
        draw.polygon(points, fill=255)
    img.paste(icon, magic[3], mask_im)

    # draw data
    draw = ImageDraw.Draw(img)
    draw_text(draw, magic[4][0], str(discord_name), magic[4][1], ImageFont.truetype(font, size=magic[4][2]), magic[4][3])
    draw_text(draw, magic[5][0], str(data['project_name']), magic[5][1], ImageFont.truetype(bfont, size=magic[5][2]), magic[5][3])

    eth_symbol = magic[0]
    e = eth_symbol

    draw_text(draw, magic[6][0], str( data['total_buy_amount'] + data['total_mint_amount']), magic[6][1], ImageFont.truetype(font, size=magic[6][2]), magic[6][3], magic[6][4])
    draw_text(draw, magic[9][0], f"{data['total_nft_owned']}", magic[9][1], ImageFont.truetype(font, size=magic[9][2]), magic[9][3], magic[9][4])

    if magic[1] == 'eth_only':
        draw_text(draw, magic[7][0], f"{round(data['eth_avg_buy_price'], eth_decimal)}{e}", magic[7][1], ImageFont.truetype(font, size=magic[7][2]), magic[7][3], magic[7][4])
        draw_text(draw, magic[8][0], f"{round(data['eth_avg_sell_price'], eth_decimal)}{e}", magic[8][1], ImageFont.truetype(font, size=magic[8][2]), magic[8][3], magic[8][4])
        draw_text(draw, magic[10][0], f"{round(data['realised_pl_eth'], eth_decimal)}{e}", magic[10][1], ImageFont.truetype(font, size=magic[10][2]), magic[10][3], magic[10][4])
        draw_text(draw, magic[11][0], f"{round(data['eth_holding_value'], eth_decimal)}{e}", magic[11][1], ImageFont.truetype(font, size=magic[11][2]), magic[11][3], magic[11][4])
        draw_text(draw, magic[12][0], f"{round((data['potential_pl_eth']), eth_decimal)}{e}", magic[12][1], ImageFont.truetype(bfont, size=magic[12][2]), magic[12][3], magic[12][4])
    else:
        draw_text(draw, magic[7][0], f"{round(data['eth_avg_buy_price'], eth_decimal)}{e} (${data['usd_avg_buy_price']})", magic[7][1], ImageFont.truetype(font, size=magic[7][2]), magic[7][3], magic[7][4])
        draw_text(draw, magic[8][0], f"{round(data['eth_avg_sell_price'], eth_decimal)}{e} (${data['usd_avg_sell_price']})", magic[8][1], ImageFont.truetype(font, size=magic[8][2]), magic[8][3], magic[8][4])
        draw_text(draw, magic[10][0], f"{round(data['realised_pl_eth'], eth_decimal)}{e} (${data['realised_pl_usd']})", magic[10][1], ImageFont.truetype(font, size=magic[10][2]), magic[10][3], magic[10][4])
        draw_text(draw, magic[11][0], f"{round(data['eth_holding_value'], eth_decimal)}{e} (${data['usd_holding_value']})", magic[11][1], ImageFont.truetype(font, size=magic[11][2]), magic[11][3], magic[11][4])
        draw_text(draw, magic[12][0], f"{round((data['potential_pl_eth']), eth_decimal)}{e}", magic[12][1], ImageFont.truetype(font, size=magic[12][2]), magic[12][3], magic[12][4])

    if round(data['roi']) >= 0:
        draw_text(draw, magic[13][0], f"+{round(data['roi'])}%", "green", ImageFont.truetype(bfont, size=magic[13][2]), magic[13][3], magic[13][4])
    else:
        draw_text(draw, magic[13][0], f"{round(data['roi'])}%", "red", ImageFont.truetype(bfont, size=magic[13][2]), magic[13][3], magic[13][4])

    return img

def draw_text(draw, xy, text, color, font, spacing, align="left"):
    gap_width = spacing
    xpos = xy[0]
    if align == "right":
        text = text[::-1]
    for letter in text:
        draw.text((xpos, xy[1]), letter, color, font=font)
        letter_width, letter_height = draw.textsize(letter, font=font)
        if align == "right":
            xpos -= letter_width - gap_width
        else:
            xpos += letter_width + gap_width


if __name__ == '__main__':
    # legacy but for reference
    # magic = [(icon size, icon size), (icon x, icon y), (name x, name y), (project name x, project name y), (buy amount x, buy amount y), (eth_spent x, eth_spent y), (eth_avg_sell_price x, eth_avg_sell_price y), (total_nft_owned x, total_nft_owned y), (eth_gained x, eth_gained y), (eth_holding_value x, eth_holding_value y), (potential_pl_eth x, potential_pl_eth y), (roi x, roi y)]

    data = {'project_name': 'SAN Origin', 'project_floor': 0.0587, 'project_floor_usd': 75, 'project_image_url': 'https://open-graph.opensea.io/v1/collections/san-origin', 'total_nft_owned': 3, 'total_trade_count': 4, 'total_mint_amount': 0, 'total_buy_amount': 6, 'total_sell_amount': 3, 'eth_gas_spent': 0.012, 'usd_gas_spent': 15, 'eth_spent': 0.237, 'eth_gained': 0.203, 'usd_spent': 305, 'usd_gained': 261, 'eth_avg_buy_price': 0.039, 'usd_avg_buy_price': 51, 'eth_avg_sell_price': 0.068, 'usd_avg_sell_price': 87, 'eth_holding_value': 10.176, 'usd_holding_value': 226, 'realised_pl_eth': -0.034, 'realised_pl_usd': -44, 'potential_pl_eth': 190.142, 'potential_pl_usd': 182, 'roi': 140.432685166430362}

    response = requests.get("https://i.imgur.com/LOe8LRd.png")
    icon = Image.open(BytesIO(response.content))

    settings = {"language": "en", "eth_decimal": 3, "brand_image": "https://i.imgur.com/GUDsN8I.jpg", "template": "tbp_template.jpg", "width": 724, "height": 1024, "font": "monoMMM-5-1.ttf", "bold_font": "monoMMM-5-1.ttf", "magic": ["", "eth_only", [155, 155, "tbp_special"], [64, 95], [[240, 220], "white", 26, 0, "left"], [[240, 145], "white", 40, 0, "left"], [[650, 354], "white", 26, 0, "right"], [[650, 390], "white", 26, 0, "right"], [[650, 426], "white", 26, 0, "right"], [[650, 462], "white", 26, 0, "right"], [[650, 500], "white", 26, 0, "right"], [[650, 538], "white", 26, 0, "right"], [[180, 700], "white", 52, 0, "left"], [[650, 700], "green", 52, 0, "right"]]}

    img = generate_image("Jaason", icon, data, settings)
    img.save('test.jpg')
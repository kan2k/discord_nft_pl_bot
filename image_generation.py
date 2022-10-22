import os
import base64
import pandas as pd
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import requests

here = os.path.dirname(os.path.abspath(__file__))

def profit_image(user, data, settings):
    avatar_url = str(user.avatar)
    discord_name = str(user.name)
    avatar_url = avatar_url.replace("size=1024", "size=256")
    try:
        response = requests.get(avatar_url)
    except:
        return
    icon = Image.open(BytesIO(response.content))
    return generate_image(discord_name, icon, data, settings['template'], settings["font"], settings["bold_font"], settings["magic"], settings["eth_decimal"])


def generate_image(discord_name, icon, data, template, font, bold_font, magic, eth_decimal):
    font = os.path.join(here, "resources", "fonts", font)
    bfont = os.path.join(here, "resources", "fonts", bold_font)

    template = Image.open(os.path.join(here, "resources", "templates", template))
    
    template = template.resize((1000, 1000), Image.ANTIALIAS)
    W, H = template.size

    # crop to circle and draw discord icon
    icon = icon.resize(magic[2], Image.ANTIALIAS)
    mask_im = Image.new("L", icon.size, 0)
    draw = ImageDraw.Draw(mask_im)
    draw.ellipse((0, 0, icon.size), fill=255)
    img = template.copy()
    img.paste(icon, magic[3], mask_im)
    
    # draw data

    draw = ImageDraw.Draw(img)
    draw_text(draw, magic[4][0], str(discord_name), magic[4][1], ImageFont.truetype(font, size=magic[4][2]), magic[4][3])
    draw_text(draw, magic[5][0], str(data['project_name']), magic[5][1], ImageFont.truetype(bfont, size=magic[5][2]), magic[5][3])

    eth_symbol = magic[0]
    e = eth_symbol

    draw_text(draw, magic[6][0], str(data['total_buy_amount']), magic[6][1], ImageFont.truetype(font, size=magic[6][2]), magic[6][3], magic[6][4])
    draw_text(draw, magic[9][0], f"{data['total_nft_owned']}", magic[9][1], ImageFont.truetype(font, size=magic[9][2]), magic[9][3], magic[9][4])

    if magic[1] == 'eth_only':
        draw_text(draw, magic[7][0], f"{round(data['eth_avg_buy_price'], eth_decimal)}{e}", magic[7][1], ImageFont.truetype(font, size=magic[7][2]), magic[7][3], magic[7][4])
        draw_text(draw, magic[8][0], f"{round(data['eth_avg_sell_price'], eth_decimal)}{e}", magic[8][1], ImageFont.truetype(font, size=magic[8][2]), magic[8][3], magic[8][4])
        draw_text(draw, magic[10][0], f"{round(data['eth_gained'], eth_decimal)}{e}", magic[10][1], ImageFont.truetype(font, size=magic[10][2]), magic[10][3], magic[10][4])
        draw_text(draw, magic[11][0], f"{round(data['eth_holding_value'], eth_decimal)}{e}", magic[11][1], ImageFont.truetype(font, size=magic[11][2]), magic[11][3], magic[11][4])
        draw_text(draw, magic[12][0], f"{round((data['eth_gained'] + data['eth_holding_value']), eth_decimal)}{e}", magic[12][1], ImageFont.truetype(bfont, size=magic[12][2]), magic[12][3], magic[12][4])
    else:
        draw_text(draw, magic[7][0], f"{round(data['eth_avg_buy_price'], eth_decimal)}{e} (${data['usd_avg_buy_price']})", magic[7][1], ImageFont.truetype(font, size=magic[7][2]), magic[7][3], magic[7][4])
        draw_text(draw, magic[8][0], f"{round(data['eth_avg_sell_price'], eth_decimal)}{e} (${data['usd_avg_sell_price']})", magic[8][1], ImageFont.truetype(font, size=magic[8][2]), magic[8][3], magic[8][4])
        draw_text(draw, magic[10][0], f"{round(data['eth_gained'], eth_decimal)}{e} (${data['usd_gained']})", magic[10][1], ImageFont.truetype(font, size=magic[10][2]), magic[10][3], magic[10][4])
        draw_text(draw, magic[11][0], f"{round(data['eth_holding_value'], eth_decimal)}{e} (${data['usd_holding_value']})", magic[11][1], ImageFont.truetype(font, size=magic[11][2]), magic[11][3], magic[11][4])
        draw_text(draw, magic[12][0], f"{round((data['eth_gained'] + data['eth_holding_value']), eth_decimal)}{e}", magic[12][1], ImageFont.truetype(font, size=magic[12][2]), magic[12][3], magic[12][4])

    if round(data['roi']) > 0:
        draw_text(draw, magic[13][0], f"+{round(data['roi'])}%", "green", ImageFont.truetype(bfont, size=magic[13][2]), magic[13][3], True)
    else:
        draw_text(draw, magic[13][0], f"{round(data['roi'])}%", "red", ImageFont.truetype(bfont, size=magic[13][2]), magic[13][3], True)

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
    # magic = [(icon size, icon size), (icon x, icon y), (name x, name y), (project name x, project name y), (buy amount x, buy amount y), (eth_spent x, eth_spent y), (eth_avg_sell_price x, eth_avg_sell_price y), (total_nft_owned x, total_nft_owned y), (eth_gained x, eth_gained y), (eth_holding_value x, eth_holding_value y), (potential_pl_eth x, potential_pl_eth y), (roi x, roi y)]
    magic = [" ETH", "", [175, 175], [45, 755], [[240, 830], "white", 40, 0, "left"], [[80, 120], "white", 50, 0, "left"], [[300, 230], "white", 40, 0, "left"], [[300, 292], "white", 40, 0, "left"], [[300, 352], "white", 40, 0, "left"], [[350, 425], "white", 50, 0, "left"], [[350, 492], "white", 50, 0, "left"], [[350, 562], "white", 50, 0, "left"], [[420, 632], "white", 70, 0, "left"], [[-500, 0], "green", 50, 0, "left"]]
    data = {'project_name': 'SAN Origin', 'project_floor': 0.0587, 'project_floor_usd': 75, 'project_image_url': 'https://open-graph.opensea.io/v1/collections/san-origin', 'total_nft_owned': 3, 'total_trade_count': 4, 'total_mint_amount': 0, 'total_buy_amount': 6, 'total_sell_amount': 3, 'eth_gas_spent': 0.012, 'usd_gas_spent': 15, 'eth_spent': 0.237, 'eth_gained': 0.203, 'usd_spent': 305, 'usd_gained': 261, 'eth_avg_buy_price': 0.039, 'usd_avg_buy_price': 51, 'eth_avg_sell_price': 0.068, 'usd_avg_sell_price': 87, 'eth_holding_value': 10.176, 'usd_holding_value': 226, 'realised_pl_eth': -0.034, 'realised_pl_usd': -44, 'potential_pl_eth': 0.142, 'potential_pl_usd': 182, 'roi': 14.432685166430362}
    response = requests.get("https://cdn.discordapp.com/avatars/214359518740611072/095fe73005641221f8e6fac67fe7f579.png?size=256")
    icon = Image.open(BytesIO(response.content))
    img = generate_image("Jaason#4444", icon, data, "origins_template.jpg", "PowerGrotesk-Regular.ttf", "PowerGrotesk-Regular.ttf", magic, 2)
    img.save('test.jpg')
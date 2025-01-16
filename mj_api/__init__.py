from PIL import Image
import base64
import requests
from io import BytesIO
import json


def get_skin_url(uuid: str) -> str:
    player_info_url: str = (
        f"https://sessionserver.mojang.com/session/minecraft/profile/{uuid}"
    )
    response = requests.get(player_info_url)
    base64_data: str = response.json()["properties"][0]["value"]
    decoded_data = base64.b64decode(base64_data).decode("utf-8")
    data_json = json.loads(decoded_data)

    return data_json["textures"]["SKIN"]["url"]


def get_player_uuid(name: str) -> tuple:
    player_profile_url: str = (
        f"https://api.mojang.com/users/profiles/minecraft/{name}"
    )
    response = requests.get(player_profile_url)
    if response.status_code == 200:
        data = response.json()
        uuid: str = data['id']
        name: str = data['name']
        return name, uuid
    return None


def image_to_binary(image: Image):
    img_byte_arr = BytesIO()
    image.save(img_byte_arr, format="PNG")
    img_byte_arr = img_byte_arr.getvalue()
    return img_byte_arr


def get_profile_pic(uuid: str):
    skin_url: str = get_skin_url(uuid)
    skin_img = requests.get(skin_url).content
    tmp = BytesIO(skin_img)
    img = Image.open(tmp)

    # 裁剪图片(左，上，右，下)
    x = 8
    y = 8
    w = 8
    h = 8
    img2 = img.crop((x, y, x + w, y + h))

    return image_to_binary(img2)

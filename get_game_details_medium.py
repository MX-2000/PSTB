import requests
import datetime
import json
import re
import csv
import time

with open("id_list_final.json", "r") as f:
    id_list = json.loads(f.read())

details_endpoint = (
    "https://store.steampowered.com/api/appdetails?appids={0}&json=1&cc=ID"
)
keys = [
    "categories",
    "controller_support",
    "developers",
    "dlc",
    "genres",
    "is_free",
    "name",
    "platforms",
    "price_overview",
    "publishers",
    "release_date",
    "required_age",
    "steam_appid",
    "supported_languages",
    "type",
]

# Some fields are full of html
CLEANR = re.compile("<.*?>|&([a-z0-9]+|#[0-9]{1,6}|#x[0-9a-f]{1,6});")


def clean_html(raw_html):
    clean_text = re.sub(CLEANR, "", raw_html)
    return clean_text


def flatten_list(l):
    ls = [str(x).replace(",", "") for x in l]
    return ",".join(ls)


def details_flatten_list(details):
    return {k: flatten_list(v) if type(v) is list else v for k, v in details.items()}


game_info = {}
print(f"{datetime.datetime.now()} - Starting")
for id in id_list:

    trials = 0
    url = details_endpoint.format(id)

    while trials < 10:

        response = requests.get(url)
        if response.status_code != 200:
            print(f"Couldn't get game info {id}, retrying ...")
            trials += 1
            time.sleep(2)
        else:
            break

    if response.status_code != 200:
        print(f"Couldnt get {id} infos after 10 trials, skipping")
        continue

    details = response.json()

    details = details[str(id)]
    details = details["data"]
    details = {k: details[k] for k in keys if k in details}
    if "categories" in details:
        details["categories"] = [x["description"] for x in details["categories"]]
    if "genres" in details:
        details["genres"] = [x["description"] for x in details["genres"]]
    if "price_overview" in details:
        details["price_currency"] = details["price_overview"]["currency"]
        details["price_initial"] = details["price_overview"]["initial"]
        del details["price_overview"]
    if "release_date" in details and type(details["release_date"]) is dict:
        if "coming_soon" in details["release_date"]:
            details["coming_soon"] = details["release_date"]["coming_soon"]
        if "date" in details["release_date"]:
            details["release_date"] = details["release_date"]["date"]
    details["platforms"] = [k for k, v in details["platforms"].items() if v]

    if "supported_languages" in details:
        langs = details["supported_languages"]
        langs = (
            clean_html(langs).replace("*languages with full audio support", "").strip()
        )
        langs = [x.strip() for x in langs.split(",")]
        details["supported_languages"] = langs

    if type(details["release_date"]) is str:
        try:
            details["release_date"] = datetime.datetime.strptime(
                details["release_date"], "%d %b, %Y"
            ).strftime("%Y-%m-%d")
        except ValueError:
            pass

    details = details_flatten_list(details)

    game_info[id] = details

    if len(game_info) % 50 == 0:

        with open("game_info.json", "w") as f:
            f.write(json.dumps(game_info))

        print(
            f"{datetime.datetime.now()} - Wrote {len(game_info)} games infos into json ! "
        )

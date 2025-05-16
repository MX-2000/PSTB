import asyncio
import aiohttp
import datetime
import json
import re
import time

# Read ID list from file
with open("id_list_final.json", "r") as f:
    id_list = json.loads(f.read())

id_list = id_list[1000:]
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

# Regex to remove HTML tags and entities
CLEANR = re.compile(r"<.*?>|&([a-z0-9]+|#[0-9]{1,6}|#x[0-9a-f]{1,6});")


def clean_html(raw_html):
    return re.sub(CLEANR, "", raw_html)


def flatten_list(l):
    """Flatten list as comma-separated string without commas in list items."""
    ls = [str(x).replace(",", "") for x in l]
    return ",".join(ls)


def details_flatten_list(details):
    """Flatten any list values within a dictionary."""
    return {
        k: flatten_list(v) if isinstance(v, list) else v for k, v in details.items()
    }


async def fetch_details(session, sem, app_id, max_retries=10):
    """
    Fetch details for a single game ID.
    Retries up to `max_retries` times on non-200 responses.
    Returns the parsed details dict or None if failed.
    """
    url = details_endpoint.format(app_id)

    for attempt in range(max_retries):
        async with sem:
            try:
                async with session.get(url) as response:
                    if response.status != 200:
                        # Retry if we didn't get a 200
                        print(f"Couldn't get game info {app_id}, retrying ...")
                        data = await response.json()
                        print(data, response.status)
                        if response.status == 429:  # Too Many Requests
                            retry_after = response.headers.get("Retry-After")
                            if retry_after is not None:
                                print(
                                    f"Rate limit hit. Retry after {retry_after} seconds."
                                )
                            else:
                                print(
                                    "Rate limit hit, but no 'Retry-After' header found."
                                )
                                retry_after = 60
                            await asyncio.sleep(retry_after)

                        await asyncio.sleep(2)
                        continue
                    data = await response.json()
            except Exception as e:
                # Network or JSON decode error; wait and retry
                print(
                    f"Error fetching {app_id}: {e} (attempt {attempt+1}/{max_retries})"
                )
                await asyncio.sleep(2)
                continue

        # If we got here, we (likely) have a successful response
        # Extract the relevant details from the JSON
        if str(app_id) not in data:
            print(f"No data for {app_id} in response: \n{data}, skipping.")
            # await asyncio.sleep(60)
            return None

        app_data = data[str(app_id)]
        if "data" not in app_data:
            print(f"No 'data' in the response for {app_id} \n{app_data}, skipping.")
            # await asyncio.sleep(60)
            return None

        details = app_data["data"]
        # Filter only the keys we want
        details = {k: details[k] for k in keys if k in details}

        # Parse categories
        if "categories" in details:
            details["categories"] = [x["description"] for x in details["categories"]]

        # Parse genres
        if "genres" in details:
            details["genres"] = [x["description"] for x in details["genres"]]

        # Parse price
        if "price_overview" in details:
            details["price_currency"] = details["price_overview"].get("currency", "")
            details["price_initial"] = details["price_overview"].get("initial", 0)
            del details["price_overview"]

        # Parse release_date
        if "release_date" in details and isinstance(details["release_date"], dict):
            if "coming_soon" in details["release_date"]:
                details["coming_soon"] = details["release_date"]["coming_soon"]
            if "date" in details["release_date"]:
                details["release_date"] = details["release_date"]["date"]

        # Parse platforms
        if "platforms" in details:
            details["platforms"] = [k for k, v in details["platforms"].items() if v]

        # Parse supported languages
        if "supported_languages" in details:
            langs = clean_html(details["supported_languages"])
            # Remove any leftover text like "*languages with full audio support"
            langs = langs.replace("*languages with full audio support", "").strip()
            langs = [x.strip() for x in langs.split(",")]
            details["supported_languages"] = langs

        # Convert release_date to YYYY-MM-DD if possible
        if isinstance(details.get("release_date"), str):
            try:
                details["release_date"] = datetime.datetime.strptime(
                    details["release_date"], "%d %b, %Y"
                ).strftime("%Y-%m-%d")
            except ValueError:
                pass

        # Flatten any list fields
        details = details_flatten_list(details)
        return details

    # If we have exhausted all retries with no success, return None
    print(
        f"Could not fetch details for {app_id} after {max_retries} retries, skipping."
    )
    return None


async def main():
    print(f"{datetime.datetime.now()} - Starting")
    game_info = {}
    no_details = []

    # Concurrency limit: adjust as needed
    sem = asyncio.Semaphore(1)

    # We'll store after each chunk of IDs
    chunk_size = 50

    async with aiohttp.ClientSession() as session:
        # Process IDs in small batches
        for start_index in range(0, len(id_list), chunk_size):
            batch_ids = id_list[start_index : start_index + chunk_size]

            tasks = [fetch_details(session, sem, app_id) for app_id in batch_ids]
            results = await asyncio.gather(*tasks)

            # Collect results
            for app_id, details in zip(batch_ids, results):
                if details:
                    game_info[app_id] = details
                else:
                    no_details.append(app_id)

            # Write partial results to file
            with open("game_info2.json", "w", encoding="utf-8") as f:
                f.write(json.dumps(game_info, ensure_ascii=False))
            print(
                f"{datetime.datetime.now()} - Processed {start_index + len(batch_ids)} apps, saved partial data."
            )

            if len(no_details) > 0:
                with open("no_detail_app2.json", "w") as f:
                    f.write(json.dumps(no_details))

    print(f"{datetime.datetime.now()} - Finished!")
    print(f"Total games gathered: {len(game_info)}")


if __name__ == "__main__":
    asyncio.run(main())

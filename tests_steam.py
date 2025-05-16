import requests
from bs4 import BeautifulSoup
import time

FILE_NAME = "id_list_scrape_2.json"

MAX_PAGE = 8209


def scrape_steam_ids(num_ids):
    """
    Scrapes the Steam store search page to collect at least `num_ids` game IDs.
    Returns a list of game IDs as strings.
    """
    base_url = "https://store.steampowered.com/search/"
    collected_ids = []
    page = 2460

    while len(collected_ids) < num_ids:
        time.sleep(0.1)
        # Paginate by appending "?page=N"
        url = f"{base_url}?page={page}"

        response = requests.get(url)
        if not response.ok:
            print(
                f"Failed to retrieve page {page}. HTTP status: {response.status_code}"
            )
            time.sleep(2)
            continue

        soup = BeautifulSoup(response.text, "html.parser")
        # The selector for the result rows
        result_rows = soup.select("#search_resultsRows a")

        # If there are no results on this page, stop
        if not result_rows:
            print(f"No more results at page {page}.")
            time.sleep(1)
            page += 1
            continue

        # Extract the data-ds-appid attribute from each row
        for row in result_rows:
            appid = row.get("data-ds-appid")
            if appid:
                collected_ids.append(appid)
                if len(collected_ids) >= num_ids:
                    break

        if page % 30 == 0:
            print(f"Page: {page}")

            print(f"{len(collected_ids)} Ids.")

            with open(FILE_NAME, "w") as f:
                f.write(json.dumps(collected_ids))

        page += 1

    return collected_ids, page


if __name__ == "__main__":
    import json

    # Example usage: scrape 100 game IDs
    number_of_ids_to_scrape = 150_000
    game_ids, end_page = scrape_steam_ids(number_of_ids_to_scrape)
    print(f"Collected {len(game_ids)} IDs:")
    print(f"Stopped at page: {end_page}")

    with open(FILE_NAME, "w") as f:
        f.write(json.dumps(game_ids))

import json

tot = set()

# with open("id_list_scrape_2.json", "r") as f:
#     data = json.loads(f.read())
#     tot.update(data)
# with open("id_list_scrape.json", "r") as f:
#     data = json.loads(f.read())
#     tot.update(data)
# with open("id_list.json", "r") as f:
#     data = json.loads(f.read())
#     data = list(map(str, data))
#     tot.update(data)

# print(len(tot))

# with open("id_list_final.json", "w") as f:
#     f.write(json.dumps(list(tot)))


with open("game_info.json", "r", encoding="utf-8") as f:
    data = json.loads(f.read())
    print(len(data))

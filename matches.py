import json
import time
from glob import glob  # type: ignore
from pathlib import Path

import pandas as pd  # type: ignore
import requests
from tqdm import tqdm  # type: ignore


def get_match_data(match_id: int):
    time.sleep(1)
    try:
        print(f"[REQUEST!!] https://api.opendota.com/api/matches/{match_id}")
        response = requests.get(
            url=f"https://api.opendota.com/api/matches/{match_id}",
        )
        print(
            "Response HTTP Status Code: {status_code}".format(
                status_code=response.status_code
            )
        )
        return response.content
    except requests.exceptions.RequestException:
        print("HTTP Request failed")


def build_match_list_csv(matches_list_json_path: str):
    with open(matches_list_json_path, "r") as rf:
        data = json.load(rf)

    rows = data["rows"]
    df = pd.DataFrame(rows)
    df.to_csv("./data/100k-matches.csv")
    return df


def get_match_ids():
    df = pd.read_csv("data/100k-matches-09JUL22.csv")
    ids = df["match_id"].to_list()
    return ids


def get_ranked_match_ids():
    df = pd.read_csv("data/100k-matches-09JUL22.csv")
    ids = df[df["game_mode"] == 22]["match_id"].to_list()
    return ids


def get_pro_match_ids():
    df = pd.read_csv("data/pros-matches-30AUG22.csv")
    ids = df["Match ID"].to_list()
    return ids


def save_match_data_if_not_exists(match_id: int):
    # match_data_path = Path(f"./data/matches/09JUL22/{match_id}.json")
    match_data_path = Path(f"./data/matches/30AUG22/{match_id}.json")
    print(f"Processing {match_data_path}..")
    if not match_data_path.exists():
        match_data = get_match_data(match_id)
        with open(match_data_path, "wb") as wf:
            wf.write(match_data)
    else:
        print(f"Already exists, skipping")


def get_heroes_data():
    with open("data/heroes.json", "r") as rf:
        return json.load(rf)


HEROES = dict([(h["id"], h["localized_name"]) for h in get_heroes_data()])


def extract_match_stats(match_data_path: str):
    # match_data_path = Path(f"./data/matches/09JUL22/{match_id}.json")
    match_data = json.load(open(match_data_path, "rb"))
    match_hero_data = [
        (
            {
                "match_id": match_data["match_id"],
                "normalized-hero": f"{HEROES[x['hero_id']]}: {'Won' if (x['team'] == 0 and match_data['radiant_win'] == True) or (x['team'] == 1 and match_data['radiant_win'] == False) else 'Lost'}",
                "hero": HEROES[x["hero_id"]],
                "team": x["team"],
                "pick_order": x["order"],
                "did_win": (x["team"] == 0 and match_data["radiant_win"] == True)
                or (x["team"] == 1 and match_data["radiant_win"] == False),
            }
        )
        for x in match_data["picks_bans"]
        if x["is_pick"]
    ]
    return match_hero_data


def make_hero_match_matrix():
    # match_files = glob("./data/matches/09JUL22/**.json")
    match_files = glob("./data/matches/30AUG22/**.json")
    rows = []
    for match_file in match_files:
        try:
            hero_stats = extract_match_stats(match_file)
            row = {"match_id": hero_stats[0]["match_id"]}
            for hero in hero_stats:
                row[hero["normalized-hero"]] = 1
            rows += [row]
        except Exception:
            print(f"Bad file: {match_file}")
            continue
    df = pd.DataFrame(rows).set_index("match_id")
    dft = df.transpose()
    dft.to_csv("./data/matrices/30AUG22/hero-game.csv")
    return dft


def make_pairwise_win_matrix():
    # match_files = glob("./data/matches/09JUL22/**.json")
    match_files = glob("./data/matches/30AUG22/**.json")
    with open("./data/matrices/30AUG22/pairwise-wins.csv", "w") as wf:
        wf.write("match_id,winning_hero,losing_hero\n")
        for match_file in match_files:
            try:
                match_data = json.load(open(match_file, "rb"))
                match_hero_data = [
                    (
                        {
                            "match_id": match_data["match_id"],
                            "hero": HEROES[x["hero_id"]],
                            "pick_order": x["order"],
                            "did_win": (
                                x["team"] == 0 and match_data["radiant_win"] == True
                            )
                            or (x["team"] == 1 and match_data["radiant_win"] == False),
                        }
                    )
                    for x in match_data["picks_bans"]
                    if x["is_pick"]
                ]
                winning_hero_names = [
                    h["hero"] for h in match_hero_data if h["did_win"]
                ]
                losing_hero_names = [
                    h["hero"] for h in match_hero_data if not h["did_win"]
                ]
                for winning_hero_name in winning_hero_names:
                    for losing_hero_name in losing_hero_names:
                        wf.write(
                            f"{match_hero_data[0]['match_id']},{winning_hero_name},{losing_hero_name}\n"
                        )
            except Exception:
                print(f"Bad file: {match_file}")
                continue


def make_probability_win_dict():
    df = pd.read_csv("./data/matrices/30AUG22/pairwise-wins.csv")
    prob_win = {}
    all_heroes = sorted(
        list(set(df["winning_hero"].to_list() + df["losing_hero"].to_list()))
    )
    with open("./data/matrices/30AUG22/win-probabilities.csv", "w") as wf:
        wf.write(
            f"winning_hero,losing_hero,num_games,num_wins,probability_of_winning\n"
        )
        for hero in all_heroes:
            prob_win[hero] = {}
            df_games_for_hero = df[
                (df["winning_hero"] == hero) | (df["losing_hero"] == hero)
            ]
            for opposing_hero in all_heroes:
                if hero == opposing_hero:
                    continue
                df_games_with_opposing_hero = df_games_for_hero[
                    (df_games_for_hero["winning_hero"] == opposing_hero)
                    | (df_games_for_hero["losing_hero"] == opposing_hero)
                ]
                total_games = df_games_with_opposing_hero.shape[0]
                total_wins = df_games_with_opposing_hero[
                    df_games_with_opposing_hero["winning_hero"] == hero
                ].shape[0]
                if total_games == 0:
                    probability_hero_wins_vs_opposing_hero = 0.0
                else:
                    probability_hero_wins_vs_opposing_hero = round(
                        100.0 * float(total_wins) / float(total_games), 2
                    )
                prob_win[hero][opposing_hero] = {
                    "probability_of_winning": probability_hero_wins_vs_opposing_hero,
                    "number_of_games": total_games,
                    "number_of_wins": total_wins,
                }
                wf.write(
                    f"{hero},{opposing_hero},{total_games},{total_wins},{probability_hero_wins_vs_opposing_hero}\n"
                )
    return prob_win


if __name__ == "__main__":
    # extract_match_stats(6653832858)

    # match_ids = get_ranked_match_ids()
    match_ids = get_pro_match_ids()
    for match_id in tqdm(match_ids):
        save_match_data_if_not_exists(match_id)

    make_hero_match_matrix()
    make_pairwise_win_matrix()
    make_probability_win_dict()

    # 429's around this match_id data/matches/09JUL22/6418446401.json..

    # match_list_df = build_match_list_csv("./data/100k-public-matches-09JUL22.json")
    # match_ids = get_match_ids()
    # first_match_id = ranked_match_ids[0]
    # save_match_data_if_not_exists(first_match_id)
    # save_match_data_if_not_exists(6653832858)
    # get_match_data(match_id=6586795202)

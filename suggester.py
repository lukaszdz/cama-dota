import json

import numpy as np
import pandas as pd  # type: ignore
from numpy.linalg import norm


def get_heroes_data():
    with open("data/heroes.json", "r") as rf:
        return json.load(rf)


def cosine_similarity(a, b):
    cos_sim = np.dot(a, b) / (norm(a) * norm(b))
    return cos_sim


def find_hero(name):
    heroes_data = get_heroes_data()
    for hero_data in heroes_data:
        if name in hero_data["localized_name"].lower():
            return hero_data["localized_name"]
    raise Exception(f"Could not find hero named {name}")


def get_hero_game_matrix():
    # return pd.read_csv("data/matrices/hero-game-matrix-09JUL22.csv", index_col=0)
    return pd.read_csv("data/matrices/30AUG22/hero-game.csv", index_col=0)


def suggest_heros(your_team, enemy_team):
    hero_names = [f"{find_hero(h)}: Won" for h in your_team]
    hero_names += [f"{find_hero(h)}: Lost" for h in enemy_team]
    hero_game_matrix_df = get_hero_game_matrix()
    target_vector = list(
        map(lambda x: 1 if x else 0, hero_game_matrix_df.index.isin(hero_names))
    )
    cosine_to_target = lambda x: cosine_similarity(np.nan_to_num(x), target_vector)
    similarities_series = hero_game_matrix_df.apply(cosine_to_target, axis=0)
    similarities_series_sorted = similarities_series.sort_values(ascending=False)
    top_5_similar_games = hero_game_matrix_df[similarities_series_sorted.head().index]
    return (
        top_5_similar_games.iloc[:, 0].dropna(),
        top_5_similar_games.iloc[:, 1].dropna(),
        top_5_similar_games.iloc[:, 2].dropna(),
        top_5_similar_games.iloc[:, 3].dropna(),
        top_5_similar_games.iloc[:, 4].dropna(),
    )


if __name__ == "__main__":
    suggested_heroes_list = suggest_heros(
        ["lina"], ["viper", "axe", "weaver", "sniper", "spectre"]
    )
    suggested_heroes_list[0]
    suggested_heroes_list[1]
    suggested_heroes_list[2]
    suggested_heroes_list[3]
    suggested_heroes_list[4]
    print("done")

import time
import json
from update_gist import sanitize_name, enrich_character_info, PATH_MAP, ELEM_MAP
import requests

def run_benchmark():
    # Mock data
    en_data = {str(i): {"name": f"Character {i}"} for i in range(1000)}
    cht_data = {str(i): {"name": f"角色 {i}", "path": "Hunt", "element": "Fire"} for i in range(1000)}
    wiki_char_cache = {}
    session = requests.Session()

    start_time = time.time()
    for i in range(500):
        # Searching from end so loop goes longer
        enrich_character_info(f"Character {999-i}", en_data, cht_data, wiki_char_cache, session)
    baseline_time = time.time() - start_time
    print(f"Baseline Time: {baseline_time:.4f} seconds")

if __name__ == "__main__":
    run_benchmark()

import time
from update_gist import sanitize_name, enrich_character_info, execute_auto_update
import requests
from unittest.mock import patch, MagicMock

def test_performance():
    # We will benchmark the exact loop where enrich_character_info is called.
    en_data = {str(i): {"name": f"Character {i}"} for i in range(2000)}
    cht_data = {str(i): {"name": f"角色 {i}", "path": "Hunt", "element": "Fire"} for i in range(2000)}
    wiki_char_cache = {}
    session = requests.Session()

    sanitized_en_dict = {sanitize_name(info.get("name", "")): cid for cid, info in en_data.items()}

    start_time = time.time()
    for i in range(1000):
        # f"Character {1999-i}" is the name
        enrich_character_info(f"Character {1999-i}", en_data, cht_data, wiki_char_cache, session, sanitized_en_dict)
    baseline_time = time.time() - start_time
    print(f"New Time: {baseline_time:.4f} seconds")

if __name__ == "__main__":
    test_performance()

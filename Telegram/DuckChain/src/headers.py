from src.agent import generate_random_user_agent

def headers(authorization):
    return {
            "accept": "*/*",
            "if-none-match": 'W/"155-94Gyjrb7r8ocCFlWoI0Yu20QKHI"',
            "authorization": f"tma {authorization}",
            "origin": "https://preapi.duckchain.io",
            "priority": "u=1, i",
            "referer": "https://preapi.duckchain.io/",
            "sec-ch-ua": "\"Not)A;Brand\";v=\"99\", \"Android WebView\";v=\"127\", \"Chromium\";v=\"127\"",
            "sec-ch-ua-mobile": "?1",
            "sec-ch-ua-platform": "\"Android\"",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "user-agent": generate_random_user_agent()
    }

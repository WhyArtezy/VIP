import json
import time
import os
import sys
import random
from datetime import datetime, timedelta
import urllib.parse
import cloudscraper
from colorama import init
from dateutil import parser
from pytz import timezone
from src.deeplchain import read_config, log, countdown_timer, _clear, _banner, htm, hju, pth, kng, bru, mrh, log_line, log_error
from src.headers import headers

init(autoreset=True)
config = read_config()

class VooiDC:
    def __init__(self):
        self.base_url = "https://api-tg.vooi.io/api"
        self.open_position = config.get('open_position', False)
        self.auto_play_game = config.get('auto_play_game', False)
        self.auto_complete_task = config.get('auto_complete_task', False)
        self.account_delay = config.get('account_delay', 5)
        self.countdown_loop = config.get('countdown_loop', 3800)
        self.base_headers = headers()
        self.access_token = None
        self.use_proxies = config.get('use_proxy', False)
        self.proxies = self.load_proxies() if self.use_proxies else []
        self.session = self.create_session()

    def load_proxies(self):
        proxies_file = os.path.join(os.path.dirname(__file__), './proxies.txt')
        formatted_proxies = []
        with open(proxies_file, 'r') as file:
            for line in file:
                proxy = line.strip()
                if proxy:
                    if proxy.startswith("socks5://"):
                        formatted_proxies.append(proxy)
                    elif not (proxy.startswith("http://") or proxy.startswith("https://")):
                        formatted_proxies.append(f"http://{proxy}")
                    else:
                        formatted_proxies.append(proxy)
        return formatted_proxies

    def create_session(self, proxy=None):
        session = cloudscraper.create_scraper()
        if proxy:
            session.proxies = {
                "http": proxy,
                "https": proxy
            }
        return session

    def get_headers(self):
        headers = self.base_headers.copy()
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    def login_new_api(self, init_data, proxy=None):
        url = f"{self.base_url}/v2/auth/login"
        payload = {
            "initData": init_data,
            "inviterTelegramId": ""
        }

        try:
            session = self.create_session(proxy)
            response = session.post(url, json=payload, headers=self.get_headers())

            if response.status_code == 201:
                self.access_token = response.json()['tokens']['access_token']
                return {"success": True, "data": response.json()}
            else:
                return {"success": False, "error": 'Unexpected response status'}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def make_check_request(self, proxy=None):
        url = f"{self.base_url}/autotrade"
        try:
            session = self.create_session(proxy)
            response = session.get(url, headers=self.get_headers())
            if response.status_code in [200, 201]:
                return response.json()
            else:
                return None
        except Exception as e:
            return None

    def make_start_request(self, proxy=None):
        url = f"https://api-tg.vooi.io/api/autotrade/start"
        data = {}
        try:
            session = self.create_session(proxy)
            response = session.post(url, headers=self.get_headers(), json=data)
            
            if response.status_code in [200, 201]:
                return response.json()
            else:
                log(f"Unexpected status code for start request: {response.status_code}. Response: {response.text}")
                if response.status_code == 500:
                    log(mrh + f"Server Error (500) - message on last.log")
                    log_error(f"{response.json().get('message', 'No message provided')}")
                return None
        except Exception as e:
            log(mrh + f"Error during start - message on last.log")
            log_error(f"{str(e)}")
            return None

    def make_claim_request(self, autoTradeId, proxy=None):
        url = f"{self.base_url}/autotrade/claim"
        payload = {"autoTradeId": autoTradeId}
        try:
            session = self.create_session(proxy)
            response = session.post(url, json=payload, headers=self.get_headers())
            if response.status_code in [200, 201]:
                return response.json()
            else:
                log(mrh + f"an error occured - message on last.log")
                log_error(f"{response.status_code} - {response.text}")
                return None
        except Exception as e:
            log(f"Error during claim request - message on last.log")
            log_error(f"{str(e)}")
            return None

    def autotrade(self, proxy=None):
        autotrade_data = self.make_check_request(proxy=proxy)
        
        if not autotrade_data:
            log(kng + f"No ongoing autotrade found. Starting autotrade.")
            autotrade_data = self.make_start_request(proxy=proxy)

        if autotrade_data:
            log(hju + f"Autotrade state: {pth}{autotrade_data['status']}")
            if autotrade_data['status'] == 'finished':
                log(hju + f"Autotrade finished. Claiming rewards...")

                claim_result = self.make_claim_request(autotrade_data['autoTradeId'], proxy=proxy)
                if claim_result:
                    log(hju + f"Autotrade reward {pth}{claim_result['reward']['virtMoney']} {hju}vUSD & {pth}{claim_result['reward']['virtPoints']} {hju}VT.")
                    log(hju + f"Total balance: {pth}{claim_result['balance']['virt_money']} {hju}USDT | {pth}{claim_result['balance']['virt_points']} {hju}VT")
                else:
                    log(mrh + f"Unable to claim autotrade rewards.")

                log(hju + f"Starting a new autotrade...")
                new_autotrade_data = self.make_start_request(proxy=proxy)
                if new_autotrade_data:
                    self.log_autotrade_info(new_autotrade_data)
                else:
                    log(mrh + f"Unable to start a new autotrade.")
            
            else:
                end_time = parser.parse(autotrade_data['endTime'])
                current_time = datetime.now(timezone('UTC'))
                time_left = end_time - current_time

                if time_left.total_seconds() < 0:
                    log(hju + f"Autotrade has already completed.")
                    log(hju + f"Starting a new autotrade...")
                    new_autotrade_data = self.make_start_request(proxy=proxy)
                    if new_autotrade_data:
                        self.log_autotrade_info(new_autotrade_data)
                    else:
                        log(mrh + f"Unable to start a new autotrade.")
                else:
                    self.log_autotrade_info(autotrade_data, time_left)
        else:
            log(mrh + f"Unable to start or check autotrade.")

    def log_autotrade_info(self, autotrade_data, time_left=None):
        end_time = parser.parse(autotrade_data['endTime'])
        if time_left is None:
            current_time = datetime.now(timezone('UTC'))
            time_left = end_time - current_time

        hours, remainder = divmod(time_left.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)
        rounded_time_left = f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"

        log(hju + f"Time left: {pth}{rounded_time_left} | {pth}{end_time.strftime('%Y-%m-%d %H:%M:%S')}")

    def play_tapping_game(self, proxy=None):
        max_game = config.get('max_game_to_play', 6)
        for game_number in range(1, max_game):
            log(hju + f"Starting play tap coin {pth}{game_number}/{max_game}")

            url_start = f"{self.base_url}/tapping/start_session"
            try:
                session = self.create_session(proxy)
                response = session.post(url_start, json={}, headers=self.get_headers())

                if response.status_code not in [200, 201]:
                    log(mrh + f"Unable to start game {game_number}. Skipping this game.")
                    continue

                session_data = response.json()
                virt_money_limit = int(session_data['config']['virtMoneyLimit'])
                virt_points_limit = int(session_data['config']['virtPointsLimit'])

            except Exception as e:
                log(mrh + f"Error starting game - message on last.log")
                log_error(f"{str(e)}")
                continue

            log(hju + f"Playing the game for 30s please wait..")
            countdown_timer(30)

            virt_money = random.randint(max(1, int(virt_money_limit * 0.5)), int(virt_money_limit * 0.8))
            virt_money = virt_money - (virt_money % 1) 

            virt_points = virt_points_limit if virt_points_limit > 0 else 0
            url_finish = f"{self.base_url}/tapping/finish"
            payload = {
                "sessionId": session_data['sessionId'],
                "tapped": {
                    "virtMoney": virt_money,
                    "virtPoints": virt_points
                }
            }

            try:
                response = session.post(url_finish, json=payload, headers=self.get_headers())

                if response.status_code in [200, 201]:
                    result = response.json()
                    log(hju + f"Success get {pth}{result['tapped']['virtMoney']} {hju}vUSD & {pth}{result['tapped']['virtPoints']} {hju}VT from game")
                else:
                    log(mrh + f"Failed completing tapping session for game {game_number}: {response.status_code}")

            except Exception as e:
                log(mrh + f"Error finishing tapping session for game {game_number}: {str(e)}")

            if game_number < 5:
                time.sleep(3)

    def complete_quest(self, proxy=None):
        url = f"{self.base_url}/tasks?limit=200&skip=0"
        try:
            session = self.create_session(proxy)
            response = session.get(url, headers=self.get_headers())

            if response.status_code != 200:
                log(mrh + f"Unexpected status code when getting quest: {response.status_code}")
                return
            quest_data = response.json()

            if not quest_data or 'nodes' not in quest_data or not quest_data['nodes']:
                log(kng + f"Currently no quest available to complete.")
                return

        except Exception as e:
            log(mrh + f"Error getting quest: {str(e)}")
            return

        new_quest = [task for task in quest_data['nodes'] if task['status'] == 'new' and task['id'] != 71]
        if not new_quest:
            log(kng + f"No new available quest available to start.")
        
        for task in new_quest:
            task_url = f"{self.base_url}/tasks/start/{task['id']}"
            try:
                response = session.post(task_url, json={}, headers=self.get_headers())
                if response.status_code in [200, 201]:
                    result = response.json()
                    if result.get('status') == 'in_progress':
                        log(hju + f"Successfully started task {pth}{task['description']}")
                        countdown_timer(3)
                    else:
                        log(mrh + f"Unable to start task {task['description']}")
                else:
                    log(mrh + f"Unexpected status code when starting task {task['description']}: {response.status_code}")
            except Exception as e:
                log(mrh + f"Error starting task - message on last.log")
                log_error(f"{task['description']}: {str(e)}")

        completed_quest = [task for task in quest_data['nodes'] if task['status'] == 'done' and task['id'] != 71]
        if not completed_quest:
            log(kng + f"No completed quest available to claim.")

        for task in completed_quest:
            task_url = f"{self.base_url}/tasks/claim/{task['id']}"
            try:
                response = session.post(task_url, json={}, headers=self.get_headers())
                if response.status_code in [200, 201]:
                    result = response.json()
                    if 'claimed' in result:
                        virt_money = result['claimed']['virt_money']
                        virt_points = result['claimed']['virt_points']
                        log(hju + f"Task {pth}{task['description']} {hju}completed")
                        log(hju + f"Reward from this quest {pth}{virt_money} {hju}vUSD | {pth}{virt_points} {hju}VT")
                        countdown_timer(3)
                    else:
                        log(mrh + f"Unable to claim reward for task {task['description']}")
                else:
                    log(mrh + f"Unexpected status code when claiming task {task['description']}: {response.status_code}")
            except Exception as e:
                log(mrh + f"Error claiming task {task['description']}: {str(e)}")

    def get_open_positions(self, proxy=None):
        url_positions = f"{self.base_url}/trades/positions?limit=10&skip=0&statuses=open"
        try:
            session = self.create_session(proxy)
            response_positions = session.get(url_positions, headers=self.get_headers())
            
            if response_positions.status_code == 200:
                positions_data = response_positions.json()
                if positions_data['count'] > 0:
                    for position in positions_data['nodes']:
                        log(hju + f"Position ID: {pth}{position['id']}")
                        log(hju + f"Open Date: {pth}{position['openDate']}", flush=True)
                        log(hju + f"Order type {pth}{position['type']} {hju}at price: {pth}{position['openRate']}")
                    return {"success": True, "data": positions_data}
                else:
                    log(kng + f"No open positions or trade found", flush=True)
                    return {"success": False, "message": "No open positions"}
            else:
                log(mrh + f"Failed to fetch open positions, status code: {response_positions.status_code}", flush=True)
                if response_positions.status_code == 500:
                    log(mrh + f"Internal server error (500) occurred.", flush=True)
                return {"success": False, "error": f"Failed to fetch open positions, status code: {response_positions.status_code}"}

        except Exception as e:
            log(mrh + f"Error fetching open positions: {str(e)}", flush=True)
            return {"success": False, "error": str(e)}
        
    def get_current_price(self, proxy=None, pair_ticker="ETHUSD"):
        pair_mapping = {"BTCUSD": 1, "ETHUSD": 2, "TONUSD": 3}
        pair_id = pair_mapping.get(pair_ticker)
        if not pair_id:
            log(mrh + "Invalid ticker provided", flush=True)
            return {"success": False, "error": "Invalid ticker provided"}

        url = f"https://api-tg.vooi.io/api/rates/0?pairId={pair_id}"
        try:
            session = self.create_session(proxy)
            response = session.get(url, headers=self.get_headers())
            if response.status_code == 200:
                price_data = response.json()
                latest_price = float(price_data['nodes'][-1]['price'])
                return {"success": True, "price": latest_price}
            else:
                log(mrh + f"Failed to fetch current price, status code: {response.status_code}", flush=True)
                return {"success": False, "error": f"Failed to fetch current price, status code: {response.status_code}"}
        except Exception as e:
            log(mrh + f"Error fetching current price: {str(e)}", flush=True)
            return {"success": False, "error": str(e)}

    def trade(self, proxy=None, pair_ticker="BTCUSD", amount="100", leverage=50):
        try:
            profit_threshold = config.get("profit_threshold", 5.0) 
            loss_threshold = config.get("loss_threshold", -2.0) 

            session = self.create_session(proxy)

            def close_position(position_id, proxy=None):
                session = self.create_session(proxy)
                close_url = f"{self.base_url}/trades/close/{position_id}"
                data = {}
                response = session.patch(close_url, headers=self.get_headers(), json=data)
                reward_vt = response['vt']
                pnl = response['pnl']
                if response.status_code == 200:
                    log(hju + f"Position {pth}{pair_ticker} {hju}successfully closed", flush=True)
                    log(hju + f"Reward {pth}{reward_vt} {hju}VT with PNL {pth}{pnl}%", flush=True)
                    return True
                else:
                    log(mrh + f"Failed to close position {position_id}", flush=True)
                    return False

            positions_check = self.get_open_positions(proxy)
            if positions_check.get("success", False) and positions_check["data"]["count"] > 0:
                positions_data = positions_check["data"]

                for position in positions_data["nodes"]:
                    position_id = position['id']
                    open_rate = float(position['openRate'])
                    pair_id = position['pairId']
                    trade_type = position['type']

                    pair_mapping = {1: "BTCUSD", 2: "ETHUSD", 3: "TONUSD"}
                    pair_ticker = pair_mapping.get(pair_id)

                    if not pair_ticker:
                        log(mrh + f"Invalid pairId {pair_id} for position {position_id}", flush=True)
                        continue 

                    current_price_response = self.get_current_price(proxy, pair_ticker)

                    if not current_price_response.get("success", False):
                        return {"success": False, "error": current_price_response.get("error")}

                    current_price = current_price_response["price"]

                    if trade_type == 'long':
                        profit_percentage = ((current_price - open_rate) / open_rate) * 100
                    elif trade_type == 'short':
                        profit_percentage = ((open_rate - current_price) / open_rate) * 100
                    else:
                        profit_percentage = 0

                    log(hju + f"Current price for {pair_ticker}: {pth}{current_price}")
                    log(hju + f"Current profit {pair_ticker}: {pth}{profit_percentage:,.3f}%")

                    if profit_percentage >= profit_threshold:
                        log(hju + f"Profit threshold reached: {pth}{profit_percentage:,.3f}% {hju}| Closing position.", flush=True)
                        if not close_position(position_id, proxy):
                            return {"success": False, "error": mrh + f"Failed to close position {position_id}"}
                        return {"success": True, "message": hju + f"Position closed at {pth}{profit_percentage}% {hju}profit."}
                    elif profit_percentage <= loss_threshold:
                        log(mrh + f"Loss threshold reached: {pth}{profit_percentage:,.3f}% {mrh}| Closing position.", flush=True)
                        if not close_position(position_id, proxy):
                            return {"success": False, "error": mrh + f"Failed to close position {position_id}"}
                        return {"success": True, "message": hju + f"Position closed at {pth}{profit_percentage:,.3f}% {hju}loss."}

                return {"success": False, "message": kng + f"No position has reached the profit or loss threshold."}

            pair_mapping = {"BTCUSD": 1, "ETHUSD": 2, "TONUSD":

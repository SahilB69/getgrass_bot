import asyncio
import argparse
import random
import ssl
import json
import time
import uuid

from sys import stderr
from loguru import logger
from websockets_proxy import Proxy, proxy_connect
from fake_useragent import UserAgent

# Initialize UserAgent outside of the async function to avoid re-initialization on every call
user_agent = UserAgent()

def get_random_desktop_user_agent():
    # Directly select a random user agent string from a predefined list
    desktop_user_agents = [
        user_agent.chrome,
        user_agent.firefox,
        user_agent.edge,
    ]
    # Randomly choose among the desktop user agent strings
    random_desktop_user_agent = random.choice(desktop_user_agents)
    return random_desktop_user_agent

async def connect_to_wss(socks5_proxy, user_id):
    device_id = str(uuid.uuid3(uuid.NAMESPACE_DNS, socks5_proxy))
    logger.info(device_id)

    # Use the function to get a random desktop browser user agent
    random_user_agent = get_random_desktop_user_agent()
    while True:
        try:
            await asyncio.sleep(random.randint(1, 10) / 10)

            custom_headers = {
                "User-Agent": random_user_agent
            }
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            uri = "wss://proxy.wynd.network:4650/"
            server_hostname = "proxy.wynd.network"
            proxy = Proxy.from_url(socks5_proxy)
            async for websocket in proxy_connect(uri, proxy=proxy, ssl=ssl_context, server_hostname=server_hostname,
                                                           extra_headers=custom_headers):
                async def send_ping():
                    try:
                        while True:
                            send_message = json.dumps(
                                {"id": str(uuid.uuid4()), "version": "1.0.0", "action": "PING", "data": {}})
                            logger.debug(send_message)
                            await websocket.send(send_message)
                            await asyncio.sleep(20)
                    except Exception as e:
                        logger.error(e)
                        logger.error(socks5_proxy)

                await asyncio.sleep(1)
                asyncio.create_task(send_ping())

                while True:
                    response = await websocket.recv()
                    message = json.loads(response)
                    logger.info(message)
                    if message.get("action") == "AUTH":
                        auth_response = {
                            "id": message["id"],
                            "origin_action": "AUTH",
                            "result": {
                                "browser_id": device_id,
                                "user_id": user_id,
                                "user_agent": custom_headers['User-Agent'],
                                "timestamp": int(time.time()),
                                "device_type": "extension",
                                "version": "4.0.2"
                            }
                        }
                        logger.debug(auth_response)
                        await websocket.send(json.dumps(auth_response))

                    elif message.get("action") == "PONG":
                        pong_response = {"id": message["id"], "origin_action": "PONG"}
                        logger.debug(pong_response)
                        await websocket.send(json.dumps(pong_response))
        except Exception as e:
            logger.error(e)
            logger.error(socks5_proxy)


async def main():
    try:
        with open('user_id', 'r') as file:
            _user_id = file.readline().rstrip()
            file.close()
        
        with open('proxy_list', 'r') as file:
            socks5_proxy_list = file.read().splitlines()
            file.close()
    except Exception as e:
        logger.error(e)

    tasks = [asyncio.ensure_future(connect_to_wss(i, _user_id)) for i in socks5_proxy_list]
    await asyncio.gather(*tasks)


if __name__ == '__main__':
    # Logger setup
    logger.remove(0)
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', action='store_true', help='enable debug output')
    parser.add_argument('--debug', action='store_true', help='enable debug output')
    args = parser.parse_args()
    if args.debug or args.d:
        logger.add(sink=stderr, level='DEBUG')
        logger.debug('DEBUG enabled')
    else:
        logger.add(sink=stderr, level='INFO')
    
    asyncio.run(main())

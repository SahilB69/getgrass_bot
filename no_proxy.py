import asyncio
import argparse
import random
import ssl
import json
import time
import uuid
import websockets

from sys import stderr
from loguru import logger
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

async def connect_to_wss(user_id):
    device_id = str(uuid.uuid4())
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
            uri = "wss://proxy2.wynd.network:4650/"
            server_hostname = "proxy2.wynd.network"
            async for websocket in websockets.connect(uri, ssl=ssl_context, extra_headers=custom_headers,
                                                      server_hostname=server_hostname):
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
                        return

                await asyncio.sleep(1)
                task = asyncio.create_task(send_ping())

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
                                "version": "4.0.3"
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
            task.cancel()


async def main():
    try:
        with open("user_id", 'r') as file:
            _user_id = file.readline().rstrip()
            file.close()
    except Exception as e:
        logger.error(e)

    await connect_to_wss(_user_id)


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

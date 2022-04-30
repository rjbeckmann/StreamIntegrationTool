import json
import requests
import socket
import time

from app import App, Logger
from next_list import NextList, NextListException

logger = Logger(__name__)


class StreamLootsMonitor:

    url_base = "https://widgets.streamloots.com/alerts/"
    NEXT_LIST_ERR_SMALL = "Error updating Next List, check logs when possible."
    TIMEOUT_ERR = "No data received from feed within timeout period, reconnecting..."

    @staticmethod
    def get_username(data):
        for entry in data.get("fields", []):
            if isinstance(entry, dict):
                if entry.get('name') == 'username':
                    return entry.get('value', '')
        return ''
    
    @staticmethod
    def _get_game_id(redeem_fields):
        redeem = next(item for item in redeem_fields if item['label'] == 'Message')
        val = redeem.get('value', '')
        return next((item for item in val.split(' ') if item.startswith('#')), '')

    @staticmethod
    def _get_votes(desc):
        vote_string = ''.join(char for char in desc.split(' ')[0] if char.isdigit())
        return int(vote_string) if vote_string else 0

    @classmethod
    def _handle_next_list(cls, desc, data):
        username = cls.get_username(data)
        if redeem_fields := data.get('redeemFields'):

            game_id_segment = cls._get_game_id(redeem_fields)
            votes = cls._get_votes(desc)

            try:
                NextList().update(game_id=game_id_segment, votes=votes, username=username)
            except NextListException:
                # Don't bother with error itself, failure already recorded.
                print(cls.NEXT_LIST_ERR_SMALL)
                logger.error(
                    f"Failed to update NextList - raw game id: {game_id_segment}, "
                    f"votes: {votes}, full message: {data}"
                )
            except Exception as err:
                print(cls.NEXT_LIST_ERR_SMALL)
                logger.error(
                    f"Unexpected error while updating NextList: {str(err)}"
                    f"Original message: {data}"
                )
        else:
            uhoh = "STREAMLOOTS HAS CHANGED SCHEMA. MANUAL RECORDING NEEDED."
            print(uhoh)
            logger.error(uhoh)

    @classmethod
    def parse_message(cls, info):
        if data := info.get('data'):

            if desc := data.get("description"):
                if 'nextlist' in desc.replace(" ","").lower():
                    cls._handle_next_list(desc, data)
            else:
                username = data.get("message")
                settings = data.get("settings")
                sub_alert = False
                if settings:
                    sdata = settings.get("data")
                    if sdata:
                        sub_alert = True if sdata.get("isSubscriptionAlert") else False
                if sub_alert:
                    print(f"Sub alert for {username}")

    @classmethod
    def execute(cls):
        print("Initializing connection to Streamloots...")
        
        streamloots_id = App.config().main.streamloots_id
        url = f"{cls.url_base}{streamloots_id}/media-stream"
        # Streamloots updates are sent every 30 seconds if no active message is
        # sent.
        # If we a make it a full minute with no message, timeout and reconnect.
        with requests.get(url, stream=True, timeout=60) as data_stream:
            if not data_stream:
                print("Failed to establish connection")
                return

            print("Connection to Streamloots data stream successful.")
            App.config().connection_attempts = 0
            for line in data_stream.iter_lines():
                if line:
                    if decoded := line.decode("utf-8"):
                        # Streamloots string usually starts with "data: "
                        # For some reason this is not included inside a standard set of curly
                        # braces even though the rest of it is valid json.
                        decoded = decoded[6:] if len(decoded) > 6 else decoded
                        try:
                            if decoded.strip() == ":":
                                # empty data that just populates every so often
                                continue
                            logger.debug(decoded)
                            cls.parse_message(json.loads(decoded))
                        except Exception as err:
                            logger.error(f"Error {str(err)} parsing streamloots message: {decoded}")

    @classmethod
    def execute_with_retry(cls):
       
        max_retries = App.config().main.get('max_retries') or 3
        reconnect_wait = App.config().main.get('connection_retry_wait_seconds') or 10
        App.config().connection_attempts = 0

        while App.config().connection_attempts < max_retries:
            try:
                App.config().connection_attempts += 1
                cls.execute()
            except requests.exceptions.ConnectionError as err:
                if 'Read timed out' in str(err):
                    print(cls.TIMEOUT_ERR)
                else:
                    print("Unexpected connection error with Streamloots, reconnecting...")
                logger.error(f"Error with Streamloots Connection: {err}")
            except requests.exceptions.ReadTimeout as err:
                print(cls.TIMEOUT_ERR)
                logger.error(str(err))
            except socket.timeout:
                logger.error(f"Socket timeout to Streamloots")
            except Exception as err:
                logger.error(f"Unknown error - reconnecting: {err}")
            time.sleep(reconnect_wait)
        else:
            print(f"Unable to connect to Streamloots after {max_retries} attempts.")


StreamLootsMonitor.execute_with_retry()
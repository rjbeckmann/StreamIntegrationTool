import json
import requests
from app import App, Logger
from next_list import NextList, NextListException

logger = Logger(__name__)


class StreamLootsMonitor:

    url_base = "https://widgets.streamloots.com/alerts/"
    NEXT_LIST_ERR_SMALL = "Error updating Next List, check logs when possible."
    @classmethod
    def initiate_connection(cls):
        try:
            sess = requests.Session()
            streamloots_id = App.config().main.streamloots_id
            url = f"{cls.url_base}{streamloots_id}/media-stream"
            req = requests.Request("GET", url).prepare()
            return sess.send(req, stream=True)
        except Exception as err:
            sess.close()
            logger.error(err)

    @classmethod
    def _handle_next_list(cls, desc, data):
        if redeems := data.get('redeemFields'):
            redeem = next(item for item in redeems if item['label'] == 'Message')
            val = redeem.get('value', '')
            segment = next(item for item in val.split(' ') if item.startswith('#'))
            votes = int(desc.split(' ')[0])
            try:
                NextList().update(game_id=segment, votes=votes)
                print("Next List updated")
            except NextListException:
                # Don't bother with error itself, failure already recorded.
                print(cls.NEXT_LIST_ERR_SMALL)
                logger.error(
                    f"Failed to update NextList - raw game id: {segment}, "
                    f"votes: {votes}, full message: {data}"
                )
            except Exception as err:
                print(cls.NEXT_LIST_ERR_SMALL)
                logger.error(
                    f"Unexpected error while updating NextList: {str(err)}"
                    f"Original message: {data}"
                )

    @classmethod
    def parse_message(cls, info):
        if data := info.get('data'):
            desc = data.get('description')
            if 'next list' in desc.lower():
                cls._handle_next_list(desc, data)

    @classmethod
    def execute(cls):
        data_stream = cls.initiate_connection()
        if not data_stream:
            print ("Failed to establish connection")
            return 

        print("Connection to Streamloots data stream successful.")
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

StreamLootsMonitor.execute()
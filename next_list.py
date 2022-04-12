import gspread
from app import App, Logger


class NextListException(Exception):
    pass


class NextList:

    VOTE_COLUMN = 4

    def __init__(self):
        
        try:
            self.gc = gspread.service_account()
            self.sheet = self.gc.open_by_key(App.config().nextlist.spreadsheet_id)
            self.ws = self.sheet.get_worksheet(0)
            self.logger = Logger(__name__)
        except Exception as err:
            raise NextListException(f"Unable to connect to NextList worksheet - {str(err)}")

    def _get_prior_votes(self, cell):
        try:
            return self.ws.cell(cell.row, self.VOTE_COLUMN).value
        except Exception as err:
            raise NextListException(
               "Failed to pull prior votes for row {cell.row}, column {self.VOTE_COLUMN}."
            )

    def _get_game_cell(self, game_id):
        if game_cell := self.ws.find(game_id):
           return game_cell
        raise NextListException(f"Unable to locate row for game {game_id}.")

    def _update(self, game_id, cell, prior_votes, votes):
       try:
            self.ws.update_cell(cell.row, self.VOTE_COLUMN, int(prior_votes) + votes)
            self.logger.info(
                f"Updated game {game_id} from {prior_votes} by {votes}." 
            )
       except Exception as err:
            msg = (
               f"Unable to update NextList for game {game_id} on row "
               f"{cell.row}. Error: {str(err)}"
            )
            self.logger.error(msg)
            raise NextListException(msg)

    def update(self, game_id, votes):
        # Auto left pad the number with 0s if the user omitted them.
        no_num = game_id[1:].zfill(3)
        game_id = f'#{no_num}'
        game_cell = self._get_game_cell(game_id) 
        prior_votes = self._get_prior_votes(game_cell) or 0
        self._update(game_id, game_cell, prior_votes, votes)
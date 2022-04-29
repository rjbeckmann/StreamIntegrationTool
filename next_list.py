import gspread
import string
from gspread.utils import a1_range_to_grid_range
from app import App, Logger


class NextListException(Exception):
    pass


class NextList:

    # Remember that excel is written by inhuman monsters
    # so col and row start with 1 rather than 0

    def __init__(self):
        try:
            self.gc = gspread.service_account()
            self.sheet = self.gc.open_by_key(App.config().nextlist.spreadsheet_id)
            self.ws = self.sheet.get_worksheet(0)
            self.logger = Logger(__name__)
            self._vote_column = None
            self._name_column = None
        except Exception as err:
            raise NextListException(f"Unable to connect to NextList worksheet - {str(err)}")

    @property
    def vote_column(self):
        if self._vote_column:
            return self._vote_column
        self._vote_column = self.ws.find(query="Votes", in_row=0).col
        return self._vote_column

    @property
    def name_column(self):
        if self._name_column:
            return self._name_column
        self._name_column = self.ws.find(query="Game", in_row=0).col
        return self._name_column

    def _get_prior_votes(self, cell):
        try:
            return self.ws.cell(cell.row, self.vote_column).value
        except Exception:
            raise NextListException(
               "Failed to pull prior votes for row {cell.row}, column {self.VOTE_COLUMN}."
            )

    def _get_game_cell(self, game_id):
        if game_cell := self.ws.find(game_id):
            return game_cell
        raise NextListException(f"Unable to locate row for game {game_id}.")

    def _update(self, game_id, cell, prior_votes, votes, username):
       try:
            self.ws.update_cell(cell.row, self.vote_column, prior_votes + votes)
            msg = (
               f"Updated game {game_id} for {username} from "
               f"{prior_votes} by {votes} to {prior_votes + votes}."
            )
            print(msg + "\n")
            self.logger.info(msg)
       except Exception as err:
            msg = (
               f"Unable to update NextList for game {game_id} on row "
               f"{cell.row}. Error: {str(err)}"
            )
            print(msg + "\n")
            self.logger.error(msg)
            raise NextListException(msg)

    def _sort(self):
        end = '{vote_col}{last_row}'.format(
            vote_col=string.ascii_uppercase[self.vote_column - 1],
            last_row=len(self.ws.col_values(1))
        )
        vote_asc = (self.vote_column, 'des')
        name_desc = (self.name_column, 'asc')
        sort_range = f'A2:{end}'
        self.ws.sort(vote_asc, name_desc, range=sort_range)

    def update(self, game_id, votes, username):
        # Auto left pad the number with 0s if the user omitted them.
        no_num = game_id[1:].zfill(3)
        game_id = f'#{no_num}'
        game_cell = self._get_game_cell(game_id)

        if prior_votes := self._get_prior_votes(game_cell):
            prior_votes = int(prior_votes)
        else:
            prior_votes = 0

        self._update(game_id, game_cell, prior_votes, votes, username)
        self._sort()
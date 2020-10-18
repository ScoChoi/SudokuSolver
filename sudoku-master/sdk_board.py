"""Scott Choi

A Sudoku board holds a matrix of tiles.
Each row and column and also sub-blocks
are treated as a group (sometimes called
a 'nonet'); when solved, each group must contain
exactly one occurrence of each of the
symbol choices.
"""

import enum
from typing import Sequence, List, Set
from sdk_config import CHOICES, UNKNOWN, ROOT
from sdk_config import NROWS, NCOLS
import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

# --------------------------------
#  The events for MVC
# --------------------------------

class Event(object):
    """Abstract base class of all events, both for MVC
    and for other purposes.
    """
    pass

# ---------------
# Listeners (base class)
# ---------------

class Listener(object):
    """Abstract base class for listeners.
    Subclass this to make the notification do
    something useful.
    """

    def __init__(self):
        """Default constructor for simple listeners without state"""
        pass

    def notify(self, event: Event):
        """The 'notify' method of the base class must be
        overridden in concrete classes.
        """
        raise NotImplementedError("You must override Listener.notify")

# --------------------------------------
# Events and listeners for Tile objects
# --------------------------------------

class EventKind(enum.Enum):
    TileChanged = 1
    TileGuessed = 2

class TileEvent(Event):
    """Abstract base class for things that happen
    to tiles. Always indicates the tile.  Concrete
    subclasses indicate the nature of the event.
    """

    def __init__(self, tile: 'Tile', kind: EventKind):
        self.tile = tile
        self.kind = kind
        # Note 'Tile' type is a forward reference;
        # Tile class is defined below

    def __str__(self):
        """Printed representation includes name of concrete subclass"""
        return f"{repr(self.tile)}"

class TileListener(Listener):
    def notify(self, event: TileEvent):
        """raises an error if subclasses don't override notify method"""
        raise NotImplementedError(
            "TileListener subclass needs to override notify(TileEvent)")

class Listenable:
    """Objects to which listeners (like a view component) can be attached"""

    def __init__(self):
        self.listeners = [ ]

    def add_listener(self, listener: Listener):
        """adds another listener to the list listeners"""
        self.listeners.append(listener)

    def notify_all(self, event: Event):
        """notifies all listeners"""
        for listener in self.listeners:
            listener.notify(event)

# ----------------------------------------------
#      Tile class
# ----------------------------------------------

class Tile(Listenable):
    """One tile on the Sudoku grid.
    Public attributes (read-only): value, which will be either
    UNKNOWN or an element of CHOICES; candidates, which will
    be a set drawn from CHOICES.  If value is an element of
    CHOICES,then candidates will be the singleton containing
    value.  If candidates is empty, then no tile value can
    be consistent with other tile values in the grid.
    value is a public read-only attribute; change it
    only through the access method set_value or indirectly
    through method remove_candidates.
    """

    def __init__(self, row: int, col: int, value=UNKNOWN):
        super().__init__()
        assert value == UNKNOWN or value in CHOICES
        self.row = row
        self.col = col
        self.set_value(value)

    def set_value(self, value: str):
        """determines whether or not a value is an integer 1-9 and
        initializes self.value and sets self.candidates accordingly"""
        if value in CHOICES:
            self.value = value
            self.candidates = {value}
        else:
            self.value = UNKNOWN
            self.candidates = set(CHOICES)
        self.notify_all(TileEvent(self, EventKind.TileChanged))

    def __hash__(self) -> int:
        """Hash on position only (not value)"""
        return hash((self.row, self.col))

    def __str__(self) -> str:
        return f"{self.value}"

    def __repr__(self) -> str:
        return f"Tile({self.row}, {self.col}, '{self.value}')"

    def could_be(self, value: str) -> bool:
        """True iff value is a candidate value for this tile"""
        return value in self.candidates

    def remove_candidates(self, used_values: Set[str]):
        """The used values cannot be a value of this unknown tile.
        Remove those possibilities from the list of candidates.
        If there is exactly one candidate left, set the
        value of the tile.
        Returns:  True means it eliminated at least one candidate,
        False means nothing changed (none of the 'used_values' was
        in the candidates set).
        """
        new_candidates = self.candidates.difference(used_values)
        if new_candidates == self.candidates:
            # Didn't remove any candidates
            return False
        self.candidates = new_candidates
        if len(self.candidates) == 1:
            self.set_value(new_candidates.pop())
        self.notify_all(TileEvent(self, EventKind.TileChanged))
        return True

# ------------------------------
#  Board class
# ------------------------------

class Board(object):
    """A board has a matrix of tiles"""

    def __init__(self):
        """The empty board"""
        # Row/Column structure: Each row contains columns
        self.tiles: List[List[Tile]] = [ ]
        self.groups = []
        for row in range(NROWS):
            cols = [ ]
            for col in range(NCOLS):
                cols.append(Tile(row, col))
            self.tiles.append(cols)
        for row in self.tiles:
            self.groups.append(row)
        for col in range(NCOLS):
            col_group = []
            for row in range(NROWS):
                col_group.append(self.tiles[row][col])
            self.groups.append(col_group)
        for block_row in range(ROOT):
            for block_col in range(ROOT):
                group = []
                for row in range(ROOT):
                    for col in range(ROOT):
                        row_addr = (ROOT * block_row) + row
                        col_addr = (ROOT * block_col) + col
                        group.append(self.tiles[row_addr][col_addr])
                self.groups.append(group)

    def __hash__(self) -> int:
        """Hash on position only (not value)"""
        return hash((self.row, self.col))

    def __str__(self) -> str:
        """In Sadman Sudoku format"""
        return "\n".join(self.as_list())


    def as_list(self) -> List[str]:
        """Tile values in a format compatible with
        set_tiles.
        """
        row_syms = [ ]
        for row in self.tiles:
            values = [tile.value for tile in row]
            row_syms.append("".join(values))
        return row_syms

    def set_tiles(self, tile_values: Sequence[Sequence[str]]):
        """Set the tile values a list of lists or a list of strings"""
        for row_num in range(NROWS):
            for col_num in range(NCOLS):
                tile = self.tiles[row_num][col_num]
                tile.set_value(tile_values[row_num][col_num])

    def is_consistent(self) -> bool:
        """Checks whether a board has any duplicate tiles in row, col, or block"""
        for group in self.groups:
            used_symbols = set()
            for tile in group:
                if tile.value in CHOICES:
                    if tile.value in used_symbols:
                        return False
                    else:
                        used_symbols.add(tile.value)
        return True

    def naked_single(self) -> bool:
        """Eliminate candidates and check for sole remaining possibilities.
        Return value True means it crossed off at least one candidate.
        Return value False means it made no progress.
        """
        value = False
        for group in self.groups:
            used_values = set()
            for tile in group:
                if tile.value != UNKNOWN:
                    used_values.add(tile.value)
            for tile in group:
                if tile.value is UNKNOWN:
                    u = tile.remove_candidates(used_values)
                    value = u or value
        return value

    def hidden_single(self) -> bool:
        """Used alongside naked_single to check if there is a candidate
        where there is only one unknown tile it is a candidate of, then
        replaces that tile value with that candidate
        Return value True means we placed a value into a tile
        Return False otherwise"""
        torf = False
        for group in self.groups:
            leftovers = set(CHOICES)
            for tile in group:
                if tile.value in leftovers:
                    leftovers.discard(tile.value)
            for l_value in leftovers:
                ctr = 0
                for tile in group:
                    if tile.value is UNKNOWN:
                        if l_value in tile.candidates:
                            ctr += 1
                if ctr == 1:
                    torf = True
                    for tile in group:
                        if tile.value is UNKNOWN:
                            if l_value in tile.candidates:
                                tile.set_value(l_value)
        return torf

    def min_choice_tile(self) -> Tile:
        """Returns a tile with value UNKNOWN and
        minimum number of candidates.
        Precondition: There is at least one tile
        with value UNKNOWN.
        """
        least_candidates = 0 #for base case to compare later
        for row in self.tiles:
            for tile in row:
                if tile.value == UNKNOWN:
                    if least_candidates == 0:
                        least_candidates = len(tile.candidates)
                        least_tile = tile
                    if len(tile.candidates) < least_candidates:
                        least_candidates = len(tile.candidates)
                        least_tile = tile
        return least_tile

    def is_complete(self) -> bool:
        """None of the tiles are UNKNOWN.
        Note: Does not check consistency; do that
        separately with is_consistent.
        """
        for row in self.tiles:
            for tile in row:
                if tile.value == UNKNOWN:
                    return False
        return True

    def solve(self) -> bool:
        """General solver; guess-and-check
        combined with constraint propagation.
        """
        self.propagate()
        if self.is_complete():
            return True
        elif not self.is_consistent():
            return False
        else:
            save_state = self.as_list()
            guess_tile = self.min_choice_tile()
            for value in guess_tile.candidates:
                guess_tile.set_value(value)
                if self.solve():
                    return True
                else:
                    self.set_tiles(save_state)
            #Tried all the possibilites none worked
            return False



    def propagate(self):
        """Repeat solution tactics until we
        don't make any progress, whether or not
        the board is solved.
        """
        progress = True
        while progress:
            progress = self.naked_single()
            self.hidden_single()
        return


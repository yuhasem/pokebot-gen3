from typing import Generator

from modules.pokemon import Pokemon
from modules.pokemon_party import Party, get_party
from modules.pokemon_storage import get_pokemon_storage
from modules.pokemon_storage_navigaton import PCMainMenuNavigator, BoxNavigator
from ._interface import BotMode, BotModeError

LOTAD = Pokemon(b'/xBF/xFF/x37/x17/x23/x6A/xAC/x82/xC6/xC9/xCE/xBB/xBE/xFF/x00/x03/xE0/x13/x02/x02/xBC/xC9/xCE/xFF/xFF/xFF/xFF/x00/x8D/x9F/x00/x00/x9C/x84/x1F/xB4/x88/xC3/x67/x30/x9C/x95/x9B/x95/x9C/x95/x9B/x95/x9C/x95/x9B/x95/x9C/x95/x9B/x95/xAA/x94/xB6/x95/x9C/x95/x9B/x95/x93/xBD/x9B/x95/xBB/x94/x9B/x95/xFC/x95/x9B/x95/x9C/xD3/x9B/x95/x00/x00/x00/x00/x04/xFF/x12/x00/x12/x00/x08/x00/x08/x00/x08/x00/x09/x00/x08/x00')

class FrontierGrind(BotMode):
    @staticmethod
    def name() -> str:
        return "Frontier Grind"

    @staticmethod
    def is_selectable() -> bool:
        # TODO: probably shoud make it only selectable in the battle frontier, to make sure that the fly point has been
        # set.
        # And also right in front of a PC?  Otherwise it's going to be hard arranging the party.
        return True

    def __init__(self):
        pass

    def run(self) -> Generator:
        # Step 1: Getting the band back together.
        # We need Lotad, Doduo, and Duskull to be placed in the party, a strong mon that can handle any unforseen
        # battles, a mon with Fly, and the last can be anything.
        def _has_pk(party: Party, pid: int):
            for pk in party:
                if pk.personality_value() == pid:
                    return True
            return False

        party = get_party()
        boxes = get_pokemon_storage()
        if not _has_pk(party, LOTAD.personality_value()):
            if not boxes.contains_pokemon(LOTAD):
                raise BotModeError('Lotad is in netiher Party nor Storage.  Was it un-purged?')
            box, slot = boxes.get_slot_for_pokemon(LOTAD)
            # TODO: path to PC, or force use to start the mode in front of it.
            # Hmm, mayve this would be easier if we used that 6th slot can be anything rule.  Deposit 5, Withdraw the 5 we need.
            box_menu_nav = PCMainMenuNavigator("MOVE_POKEMON")
            yield from box_menu_nav.step()
            box_nav = BoxNavigator(slot, box, "MOVE")
            yield from box_nav.step()



        # Step 2: Train Lotad.

        # Step 3: EV Train Lotad and Doduo together.

        # Step 4: Finish Doduo training.

        # Step 5: Train Duskull.

        # Step 6: Fetch all items needed and equip them.

        # Step 7: Return to Battle Frontier's Battle Tower.
        pass

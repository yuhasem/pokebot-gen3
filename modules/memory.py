import struct
from enum import IntEnum, auto

from modules.context import context
from modules.game import (
    _event_flags,
    _event_vars,
    get_event_flag_offset,
    get_event_var_offset,
    get_symbol,
    get_symbol_name,
    get_symbol_name_before,
)
from modules.state_cache import state_cache


def unpack_sint8(value: bytes | int) -> int:
    if isinstance(value, int):
        value = bytearray([value])
    return struct.unpack("b", value)[0]


def unpack_uint16(value: bytes) -> int:
    return struct.unpack("<H", value)[0]


def unpack_uint32(value: bytes) -> int:
    return struct.unpack("<I", value)[0]


def pack_uint8(value: int) -> bytes:
    return struct.pack("B", value)


def pack_uint16(value: int) -> bytes:
    return struct.pack("<H", value)


def pack_uint32(value: int) -> bytes:
    return struct.pack("<I", value)


def read_symbol(name: str, offset: int = 0x0, size: int = 0x0) -> bytes:
    """
    This function uses the symbol tables from the Pokémon decompilation projects found here: https://github.com/pret
    Symbol tables are loaded and parsed as a dict in the `Emulator` class, the .sym files for each game can be found
    in `modules/data/symbols`.

    Format of symbol tables:
    `020244ec g 00000258 gPlayerParty`
    020244ec     - memory address
    g            - (l,g,,!) local, global, neither, both
    00000258     - size in bytes (base 16) (0x258 = 600 bytes)
    gPlayerParty - name of the symbol

    GBA memory domains: https://corrupt.wiki/consoles/gameboy-advance/bizhawk-memory-domains
    0x02000000 - 0x02030000 - 256 KB EWRAM (general purpose RAM external to the CPU)
    0x03000000 - 0x03007FFF - 32 KB IWRAM (general purpose RAM internal to the CPU)
    0x08000000 - 0x???????? - Game Pak ROM (0 to 32 MB)

    :param name: name of the symbol to read
    :param offset: (optional) add n bytes to the address of symbol
    :param size: (optional) override the size to read n bytes
    :return: (bytes)
    """
    addr, length = get_symbol(name)
    if size <= 0:
        size = length

    return context.emulator.read_bytes(addr + offset, size)


def write_symbol(name: str, data: bytes, offset: int = 0x0) -> bool:
    addr, length = get_symbol(name)
    if len(data) + offset > length:
        raise Exception(
            f"{len(data) + offset} bytes of data provided, is too large for symbol {addr} ({length} bytes)!"
        )

    context.emulator.write_bytes(addr + offset, data)
    return True


def get_callback_for_pointer_symbol(symbol: str, offset: int = 0, pretty_name: bool = True) -> str:
    """
    Reads the value of a symbol (which should be a 4-byte pointer) and returns the nearest symbol that
    matches its value.

    This can be used for callback pointers that point at some game function, such as the two main game
    callbacks or some other callbacks inside of structs.

    :param symbol: The symbol containing the pointer.
    :param offset: (optional) Offset from the start of the symbol where the callback should appear.
    :param pretty_name: Whether to return the symbol name all-uppercase (False) or
                        with 'natural' case (True)
    :return: The symbol name closest to the value.
    """
    pointer = unpack_uint32(read_symbol(symbol, offset, 4))

    if pointer == 0:
        return ""

    # Do a quick sanity check whether the pointer value is even within the memory ranges that the game
    # uses.
    # While the ROM can extend past 0x0900_0000, in practice none of the symbols in our symbol tables
    # are outside the 0x08... range so we limit the lookup to that.
    if (
        (0x0200_0000 <= pointer < 0x0204_0000)
        or (0x0300_0000 <= pointer < 0x0300_8000)
        or (0x0800_0000 <= pointer < 0x0900_0000)
    ):
        return get_symbol_name_before(pointer, pretty_name)
    else:
        raise RuntimeError(
            f"The pointer value we tried to read from `{symbol}` was 0x{hex(pointer)} which is outside the allowed ranges."
        )


def get_save_block(num: int = 1, offset: int = 0, size: int = 0) -> bytes:
    """
    Reads and returns the entirety (or just parts of, if `offset` and/or `size` are set) of
    one of the two 'save blocks'.

    The name 'save block' is a bit misleading as it is not just used when saving the game,
    but rather it is a structure that contains a lot of global data about the player that
    will _also_ be saved as-is but will be regularly accessed by the game when running.

    See also: https://bulbapedia.bulbagarden.net/wiki/Save_data_structure_(Generation_III)

    :param num: Number of the save block (can only be 1 or 2)
    :param offset: Number of bytes to skip from beginning of the save block - when used in
                   conjunction with `size`, this allows reading only a section of the save
                   block and cuts down in the number of bytes that need to be read.
    :param size: Number of bytes to read, starting from `offset`
    :return: The save block data (or the selected portion thereof) -- this may be
             entirely zeroes if the save blocks are not yet initialised (as is the
             case before starting/loading a game.)
    """
    if size <= 0:
        size = get_symbol(f"GSAVEBLOCK{num}")[1]
    if context.rom.is_rs:
        return read_symbol(f"gSaveBlock{num}", offset, size)
    else:
        # In FR/LG as well as Emerald, only the _pointer_ to the save file is in a known
        # memory address.
        save_block_pointer = unpack_uint32(read_symbol(f"gSaveBlock{num}Ptr"))
        if save_block_pointer == 0:
            return b"\00" * size
        return context.emulator.read_bytes(save_block_pointer + offset, size)


def write_to_save_block(data: bytes, num: int = 1, offset: int = 0) -> bool:
    """
    Writes data to one of the two 'save blocks'.

    As with any operation that modifies the in-game memory, this comes with a high
    risk of corrupting some in-game state, so use this with care.

    See comment in `get_save_block` about what 'save blocks' are.

    :param data: Data to write to the save block.
    :param num: Number of the save block to write to (can only be 1 or 2)
    :param offset: Offset from the start of the save block that should be written to.
    :return: Whether writing was successful. It can fail, for example, if the game is
             currently without a loaded game in the title screen.
    """
    if context.rom.is_rs:
        return write_symbol(f"gSaveBlock{num}", data, offset)
    else:
        save_block_pointer = unpack_uint32(read_symbol(f"gSaveBlock{num}Ptr"))
        if save_block_pointer == 0:
            return False
        return context.emulator.write_bytes(save_block_pointer + offset, data)


def get_encryption_key() -> int:
    """
    On Emerald and FR/LG, certain values in memory are 'encrypted' by XORing
    them with a key that is also stored in a save block.
    :return: The encryption key
    """
    if context.rom.is_frlg:
        return unpack_uint32(get_save_block(2, offset=0xF20, size=4))
    elif context.rom.is_emerald:
        return unpack_uint32(get_save_block(2, offset=0xAC, size=4))
    else:
        # R/S does not 'encrypt' save data yet, so the key is effectively `0`.
        # Since the encryption is just XOR, this makes it ia no-op.
        return 0


def decrypt16(value: int, encryption_key: int | None = None) -> int:
    """
    Decrypts (or encrypts, same thing) a 16-bit value using the encryption key
    of the active game.
    :param value: The value to encrypt/decrypt.
    :param encryption_key: An optional encryption key to use. If not provided,
                           the one from the active game will be used.
    :return: The encrypted/decrypted value.
    """
    if encryption_key is None:
        encryption_key = get_encryption_key()
    return value ^ (encryption_key & 0xFFFF)


def decrypt32(value: int, encryption_key: int | None = None) -> int:
    """
    Decrypts (or encrypts, same thing) a 32-bit value using the encryption key
    of the active game.
    :param value: The value to encrypt/decrypt.
    :param encryption_key: An optional encryption key to use. If not provided,
                           the one from the active game will be used.
    :return: The encrypted/decrypted value.
    """
    if encryption_key is None:
        encryption_key = get_encryption_key()
    return value ^ encryption_key


class GameState(IntEnum):
    # Menus
    BAG_MENU = auto()
    CHOOSE_STARTER = auto()
    PARTY_MENU = auto()
    # Battle related
    BATTLE = auto()
    BATTLE_STARTING = auto()
    BATTLE_ENDING = auto()
    # Misc
    OVERWORLD = auto()
    CHANGE_MAP = auto()
    TITLE_SCREEN = auto()
    MAIN_MENU = auto()
    GARBAGE_COLLECTION = auto()
    EVOLUTION = auto()
    EGG_HATCH = auto()
    WHITEOUT = auto()
    NAMING_SCREEN = auto()
    POKE_STORAGE = auto()
    POKEMON_SUMMARY_SCREEN = auto()
    UNKNOWN = auto()
    QUEST_LOG = auto()


def get_game_state_symbol() -> str:
    callback2 = read_symbol("gMain", 4, 4)  # gMain.callback2
    addr = unpack_uint32(callback2) - 1
    callback_name = get_symbol_name(addr)
    state_cache.callback2 = callback_name
    return callback_name


def get_game_state() -> GameState:
    if state_cache.game_state.age_in_frames == 0:
        return state_cache.game_state.value

    match get_game_state_symbol():
        case (
            "CB2_SETUPOVERWORLDFORQLPLAYBACKWITHWARPEXIT"
            | "CB2_SETUPOVERWORLDFORQLPLAYBACK"
            | "CB2_LOADMAPFORQLPLAYBACK"
            | "CB2_ENTERFIELDFROMQUESTLOG"
        ):
            return GameState.QUEST_LOG
        case "CB2_OVERWORLD":
            result = GameState.OVERWORLD
        case "BATTLEMAINCB2":
            result = GameState.BATTLE
        case "CB2_BAGMENURUN" | "SUB_80A3118":
            result = GameState.BAG_MENU
        case "CB2_UPDATEPARTYMENU" | "CB2_PARTYMENUMAIN":
            result = GameState.PARTY_MENU
        case "CB2_INITBATTLE" | "CB2_HANDLESTARTBATTLE" | "CB2_OVERWORLDBASIC":
            result = GameState.BATTLE_STARTING
        case "CB2_ENDWILDBATTLE":
            result = GameState.BATTLE_ENDING
        case "CB2_LOADMAP" | "CB2_LOADMAP2" | "CB2_DOCHANGEMAP" | "SUB_810CC80":
            result = GameState.CHANGE_MAP
        case "CB2_STARTERCHOOSE" | "CB2_CHOOSESTARTER":
            result = GameState.CHOOSE_STARTER
        case (
            "CB2_INITCOPYRIGHTSCREENAFTERBOOTUP"
            | "CB2_WAITFADEBEFORESETUPINTRO"
            | "CB2_SETUPINTRO"
            | "CB2_INTRO"
            | "CB2_INITTITLESCREEN"
            | "CB2_TITLESCREENRUN"
            | "CB2_INITCOPYRIGHTSCREENAFTERTITLESCREEN"
            | "CB2_INITMAINMENU"
            | "MAINCB2"
            | "MAINCB2_INTRO"
        ):
            result = GameState.TITLE_SCREEN
        case "CB2_MAINMENU":
            result = GameState.MAIN_MENU
        case "CB2_EVOLUTIONSCENEUPDATE":
            result = GameState.EVOLUTION
        case "CB2_EGGHATCH" | "CB2_LOADEGGHATCH" | "CB2_EGGHATCH_0" | "CB2_EGGHATCH_1":
            result = GameState.EGG_HATCH
        case "CB2_WHITEOUT":
            result = GameState.WHITEOUT
        case "CB2_LOADNAMINGSCREEN" | "CB2_NAMINGSCREEN" | "SUB_80B5AA0":
            result = GameState.NAMING_SCREEN
        case (
            "CB2_SHOWPOKEMONSUMMARYSCREEN"
            | "CB2_INITSUMMARYSCREEN"
            | "MAINCB2_SUMMARYSCREEN"
            | "CB2_RETURNTOPARTYMENUFROMSUMMARYSCREEN"
            | "CB2_SETUPPSS"
            | "CB2_RUNPOKEMONSUMMARYSCREEN"
            | "SUB_809DE44"
            | "SUB_809D844"
            | "SUB_8089F14"
        ):
            result = GameState.POKEMON_SUMMARY_SCREEN
        case "CB2_POKESTORAGE":
            result = GameState.POKE_STORAGE
        case _:
            result = GameState.UNKNOWN

    state_cache.game_state = result
    return result


def game_has_started() -> bool:
    """
    Reports whether the game has progressed past the main menu (save loaded
    or new game started.)
    """
    return (
        read_symbol("sPlayTimeCounterState") != b"\x00"
        and int.from_bytes(read_symbol("gObjectEvents", 0x10, 9), byteorder="little") != 0
    )


def get_event_flag(flag_name: str) -> bool:
    if flag_name not in _event_flags:
        return False

    flag_offset = get_event_flag_offset(flag_name)
    flag_byte = get_save_block(1, offset=flag_offset[0], size=1)

    return bool((flag_byte[0] >> (flag_offset[1])) & 1)


def get_event_flag_by_number(flag_number: int) -> bool:
    if context.rom.is_rs:
        offset = 0x1220
    elif context.rom.is_emerald:
        offset = 0x1270
    else:
        offset = 0x0EE0

    flag_offset = offset + (flag_number // 8)
    flag_bit = 1 << (flag_number % 8)
    flag_byte = get_save_block(1, offset=flag_offset, size=1)[0]

    return bool(flag_byte & flag_bit)


def set_event_flag(flag_name: str, new_value: bool | None = None) -> bool:
    if flag_name not in _event_flags:
        return False

    flag_offset = get_event_flag_offset(flag_name)
    flag_byte = get_save_block(1, offset=flag_offset[0], size=1)[0]

    if new_value is None:
        new_byte = flag_byte ^ (1 << flag_offset[1])
    elif new_value is True:
        new_byte = flag_byte | (1 << flag_offset[1])
    else:
        new_byte = flag_byte & ((1 << flag_offset[1]) ^ 0xFF)

    write_to_save_block(int.to_bytes(new_byte), 1, offset=flag_offset[0])
    return True


def set_event_flag_by_number(flag_number: int) -> None:
    if context.rom.is_rs:
        offset = 0x1220
    elif context.rom.is_emerald:
        offset = 0x1270
    else:
        offset = 0x0EE0

    flag_offset = offset + (flag_number // 8)
    flag_bit = 1 << (flag_number % 8)
    flag_byte = get_save_block(1, offset=flag_offset, size=1)[0]
    write_to_save_block(bytes([flag_byte ^ flag_bit]), num=1, offset=flag_offset)


def get_event_var(var_name: str) -> int:
    if var_name not in _event_vars:
        return -1
    else:
        return unpack_uint16(get_save_block(1, offset=_event_vars[var_name], size=2))


def get_event_var_by_number(var_number: int) -> int:
    if context.rom.is_rs:
        vars_offset = 0x1340
    elif context.rom.is_emerald:
        vars_offset = 0x139C
    else:
        vars_offset = 0x1000

    return unpack_uint16(get_save_block(1, offset=vars_offset + (var_number * 2), size=2))


def set_event_var(var_name: str, new_value: int) -> bool:
    if var_name not in _event_vars:
        return False

    if new_value < 0 or new_value > 2**16 - 1:
        raise ValueError(f"Event Var values must be between 0 and {2 ** 16 - 1}, but '{new_value}' was given.")

    write_to_save_block(pack_uint16(new_value), 1, offset=get_event_var_offset(var_name))
    return True

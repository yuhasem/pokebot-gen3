from dataclasses import dataclass
from enum import Enum, Flag, KEEP, auto
from typing import Literal

from modules.context import context
from modules.fishing import FishingRod
from modules.game import get_symbol_name_before
from modules.memory import unpack_uint16, unpack_uint32, read_symbol, get_callback_for_pointer_symbol
from modules.player import get_player_avatar, AvatarFlags
from modules.pokemon import (
    Species,
    Ability,
    Type,
    Move,
    LearnedMove,
    Item,
    Nature,
    get_species_by_index,
    get_type_by_index,
    get_move_by_index,
    get_item_by_index,
    get_nature_by_index,
    StatsValues,
    StatusCondition,
    get_opponent,
    get_type_by_name,
    HIDDEN_POWER_MAP,
)
from modules.state_cache import state_cache
from modules.tasks import get_global_script_context


class Weather(Enum):
    Neutral = auto()
    Rain = auto()
    Sandstorm = auto()
    Sunny = auto()
    Hail = auto()


class BattleType(Flag, boundary=KEEP):
    Double = 1 << 0
    Link = 1 << 1
    IsMaster = 1 << 2
    Trainer = 1 << 3
    FirstBattle = 1 << 4
    LinkInBattle = 1 << 5
    Multi = 1 << 6
    Safari = 1 << 7
    BattleTower = 1 << 8
    WallyTutorial = 1 << 9
    Roamer = 1 << 10
    EReaderTrainer = 1 << 11
    KyogreGroudon = 1 << 12
    Legendary = 1 << 13
    Regi = 1 << 14
    TwoOpponents = 1 << 15
    Dome = 1 << 16
    Palace = 1 << 17
    Arena = 1 << 18
    Factory = 1 << 19
    Pike = 1 << 20
    Pyramid = 1 << 21
    InGamePartner = 1 << 22
    TowerLinkMulti = 1 << 23
    Recorded = 1 << 24
    RecordedLink = 1 << 25
    TrainerHill = 1 << 26
    SecretBase = 1 << 27
    Groudon = 1 << 28
    Kyogre = 1 << 29
    Rayquaza = 1 << 30
    RecordedIsMaster = 1 << 31


class TemporaryStatus(Enum):
    Confused = auto()
    Flinched = auto()
    Uproar = auto()
    Bide = auto()
    LockConfuse = auto()
    MultipleTurns = auto()
    Wrapped = auto()
    Infatuated = auto()
    FocusEnergy = auto()
    Transformed = auto()
    Recharging = auto()
    Rage = auto()
    Substitute = auto()
    DestinyBond = auto()
    EscapePrevention = auto()
    Nightmare = auto()
    Cursed = auto()
    Foresight = auto()
    DefenseCurl = auto()
    Torment = auto()

    LeechSeeded = auto()
    AlwaysHits = auto()
    PerishSong = auto()
    InTheAir = auto()
    Underground = auto()
    Minimized = auto()
    ChargedUp = auto()
    Rooted = auto()
    Yawning = auto()
    ImprisonedOthers = auto()
    Grudge = auto()
    CannotCriticalHit = auto()
    Mudsport = auto()
    Watersport = auto()
    Underwater = auto()
    Intimidating = auto()
    Trace = auto()

    @staticmethod
    def from_bitfield(status2: int, status3: int) -> list["TemporaryStatus"]:
        result = []
        if (status2 >> 0) & 0b111:
            result.append(TemporaryStatus.Confused)
        if (status2 >> 3) & 0b1:
            result.append(TemporaryStatus.Flinched)
        if (status2 >> 4) & 0b111:
            result.append(TemporaryStatus.Uproar)
        if (status2 >> 8) & 0b11:
            result.append(TemporaryStatus.Bide)
        if (status2 >> 10) & 0b11:
            result.append(TemporaryStatus.LockConfuse)
        if (status2 >> 12) & 0b1:
            result.append(TemporaryStatus.MultipleTurns)
        if (status2 >> 13) & 0b111:
            result.append(TemporaryStatus.Wrapped)
        if (status2 >> 16) & 0b1111:
            result.append(TemporaryStatus.Infatuated)
        if (status2 >> 20) & 0b1:
            result.append(TemporaryStatus.FocusEnergy)
        if (status2 >> 21) & 0b1:
            result.append(TemporaryStatus.Transformed)
        if (status2 >> 22) & 0b1:
            result.append(TemporaryStatus.Recharging)
        if (status2 >> 23) & 0b1:
            result.append(TemporaryStatus.Rage)
        if (status2 >> 24) & 0b1:
            result.append(TemporaryStatus.Substitute)
        if (status2 >> 25) & 0b1:
            result.append(TemporaryStatus.DestinyBond)
        if (status2 >> 26) & 0b1:
            result.append(TemporaryStatus.EscapePrevention)
        if (status2 >> 27) & 0b1:
            result.append(TemporaryStatus.Nightmare)
        if (status2 >> 28) & 0b1:
            result.append(TemporaryStatus.Cursed)
        if (status2 >> 29) & 0b1:
            result.append(TemporaryStatus.Foresight)
        if (status2 >> 30) & 0b1:
            result.append(TemporaryStatus.DefenseCurl)
        if (status2 >> 31) & 0b1:
            result.append(TemporaryStatus.Torment)

        if (status3 >> 2) & 0b1:
            result.append(TemporaryStatus.LeechSeeded)
        if (status3 >> 3) & 0b111:
            result.append(TemporaryStatus.AlwaysHits)
        if (status3 >> 5) & 0b1:
            result.append(TemporaryStatus.PerishSong)
        if (status3 >> 6) & 0b1:
            result.append(TemporaryStatus.InTheAir)
        if (status3 >> 7) & 0b1:
            result.append(TemporaryStatus.Underground)
        if (status3 >> 8) & 0b1:
            result.append(TemporaryStatus.Minimized)
        if (status3 >> 9) & 0b1:
            result.append(TemporaryStatus.ChargedUp)
        if (status3 >> 10) & 0b1:
            result.append(TemporaryStatus.Rooted)
        if (status3 >> 11) & 0b11:
            result.append(TemporaryStatus.Yawning)
        if (status3 >> 13) & 0b1:
            result.append(TemporaryStatus.ImprisonedOthers)
        if (status3 >> 14) & 0b1:
            result.append(TemporaryStatus.Grudge)
        if (status3 >> 15) & 0b1:
            result.append(TemporaryStatus.CannotCriticalHit)
        if (status3 >> 16) & 0b1:
            result.append(TemporaryStatus.Mudsport)
        if (status3 >> 17) & 0b1:
            result.append(TemporaryStatus.Watersport)
        if (status3 >> 18) & 0b1:
            result.append(TemporaryStatus.Underwater)
        if (status3 >> 19) & 0b1:
            result.append(TemporaryStatus.Intimidating)
        if (status3 >> 20) & 0b1:
            result.append(TemporaryStatus.Trace)

        return result


@dataclass
class StatsModifiers:
    attack: int
    defence: int
    speed: int
    special_attack: int
    special_defence: int
    accuracy: int
    evasion: int

    @staticmethod
    def from_bytes(data: bytes) -> "StatsModifiers":
        return StatsModifiers(
            attack=data[1] - 6,
            defence=data[2] - 6,
            speed=data[3] - 6,
            special_attack=data[4] - 6,
            special_defence=data[5] - 6,
            accuracy=data[6] - 6,
            evasion=data[7] - 6,
        )


class BattleState:
    def __init__(
        self,
        battle_type: bytes,
        side_timers: bytes,
        battler_party_indexes: bytes,
        battler_party_order: bytes,
        battler_count: int,
        battler: bytes,
        battler_status3: bytes,
        battler_disable_structs: bytes,
        absent_battler_flags: int,
        current_turn: int,
        weather: int,
    ):
        self._battle_type = battle_type
        self._side_timers = side_timers
        self._battler_party_indexes = battler_party_indexes
        self._battler_party_order = battler_party_order
        self._battler_count = battler_count
        self._battler = battler
        self._battler_status3 = battler_status3
        self._battler_disable_structs = battler_disable_structs
        self._absent_battler_flags = absent_battler_flags
        self._current_turn = current_turn
        self._weather = weather

    def __eq__(self, other):
        if isinstance(other, BattleState):
            return (
                self._battle_type == other._battle_type
                and self._side_timers == other._side_timers
                and self._battler_party_indexes == other._battler_party_indexes
                and self._battler_count == other._battler_count
                and self._battler == other._battler
                and self._battler_status3 == other._battler_status3
                and self._battler_disable_structs == other._battler_disable_structs
                and self._absent_battler_flags == other._absent_battler_flags
                and self._weather == other._weather
            )
        else:
            return NotImplemented

    @property
    def battling_pokemon(self) -> list["BattlePokemon"]:
        result = []
        for index in range(self._battler_count):
            result.append(
                BattlePokemon(
                    self._battler[0x58 * index : 0x58 * (index + 1)],
                    self._battler_status3[0x4 * index : 0x4 * (index + 1)],
                    self._battler_disable_structs[0x1C * index : 0x1C * (index + 1)],
                    self._battler_party_indexes[index * 2],
                )
            )
        return result

    @property
    def type(self) -> BattleType:
        return BattleType(unpack_uint32(self._battle_type))

    @property
    def is_double_battle(self) -> bool:
        return BattleType.Double in self.type

    @property
    def is_double_battle_with_partner(self) -> bool:
        return BattleType.Double in self.type and BattleType.InGamePartner in self.type

    @property
    def is_trainer_battle(self) -> bool:
        return BattleType.Trainer in self.type

    @property
    def is_safari_zone_encounter(self) -> bool:
        return BattleType.Safari in self.type

    @property
    def own_side(self) -> "BattleStateSide":
        return BattleStateSide(0, self, self._absent_battler_flags, self._side_timers[0:12])

    @property
    def opponent(self) -> "BattleStateSide":
        return BattleStateSide(1, self, self._absent_battler_flags, self._side_timers[12:24])

    @property
    def current_turn(self) -> int:
        return self._current_turn

    @property
    def weather(self) -> Weather | None:
        if self._weather & 0b111:
            return Weather.Rain
        elif self._weather & 0b11000:
            return Weather.Sandstorm
        elif self._weather & 0b1100000:
            return Weather.Sunny
        elif self._weather & 0b10000000:
            return Weather.Hail
        else:
            return Weather.Neutral

    @property
    def type_names(self) -> list[str]:
        result = []
        for item in BattleType:
            if item in self.type:
                result.append(item.name)
        return result

    def map_battle_party_index(self, regular_party_index: int) -> int:
        """
        The party order within a battle may differ from the 'real' party order if Pokémon
        have been switched in and out during the battle.

        In that case, when deciding to switch to a different party member the order in
        the party menu might be different from what `get_party()` returns so we'd have to
        scroll to a different index.

        This function maps party indices to that mid-battle party order.

        :param regular_party_index: Party index as it would be outside the battle.
        :return: Party index of the current in-battle party order.
        """
        for battle_party_index in range(6):
            byte = self._battler_party_order[battle_party_index // 2]
            if battle_party_index % 2 == 0:
                party_index = byte >> 4
            else:
                party_index = byte & 0xF
            if party_index == regular_party_index:
                return battle_party_index
        raise RuntimeError(f"Could not find party index #{regular_party_index} in the battle party order.")


@dataclass
class BattleSideTimer:
    turns_remaining: int
    battler_index: int


class BattleStateSide:
    def __init__(self, side: int, battle_state: BattleState, absent_battler_flags: int, timers: bytes):
        self._side = side
        self._battle_state = battle_state
        self._absent_battler_flags = absent_battler_flags
        self._timers = timers

    def __contains__(self, item):
        if isinstance(item, BattlePokemon):
            for battler in self.active_battlers:
                if item == battler:
                    return True
            return False
        else:
            return NotImplemented

    @property
    def active_battlers(self) -> list["BattlePokemon"]:
        battling_pokemon = self._battle_state.battling_pokemon
        result = []
        if self._side == 0:
            if self._absent_battler_flags & 0b0001 == 0:
                result.append(battling_pokemon[0])
            if len(battling_pokemon) > 2 and self._absent_battler_flags & 0b0100 == 0:
                result.append(battling_pokemon[2])
        else:
            if self._absent_battler_flags & 0b0010 == 0:
                result.append(battling_pokemon[1])
            if len(battling_pokemon) > 2 and self._absent_battler_flags & 0b1000 == 0:
                result.append(battling_pokemon[3])
        return result

    @property
    def left_battler(self) -> "BattlePokemon | None":
        if self._side == 0 and self._absent_battler_flags & 0b0001 == 0:
            return self._battle_state.battling_pokemon[0]
        elif self._side == 1 and self._absent_battler_flags & 0b0010 == 0:
            return self._battle_state.battling_pokemon[1]
        else:
            return None

    @property
    def right_battler(self) -> "BattlePokemon | None":
        battling_pokemon = self._battle_state.battling_pokemon
        if len(battling_pokemon) < (3 if self._side == 0 else 4):
            return None

        if self._side == 0 and self._absent_battler_flags & 0b0100 == 0:
            return self._battle_state.battling_pokemon[2]
        elif self._side == 1 and self._absent_battler_flags & 0b1000 == 0:
            return self._battle_state.battling_pokemon[3]
        else:
            return None

    @property
    def active_battler(self) -> "BattlePokemon":
        """
        This method is meant to be used in solo battles, where there is only one battler.
        In double battles it will return the left side, unless that is absent in which case it will
        return the right side.
        :return: The first active battling Pokémon.
        """
        left_battler = self.left_battler
        if left_battler is None:
            return self.right_battler
        else:
            return left_battler

    def partner_for(self, battle_pokemon: "BattlePokemon") -> "BattlePokemon | None":
        for battler in self.active_battlers:
            if battler != battle_pokemon:
                return battler
        return None

    @property
    def reflect_timer(self) -> BattleSideTimer:
        return BattleSideTimer(self._timers[0], self._timers[1])

    @property
    def lightscreen_timer(self) -> BattleSideTimer:
        return BattleSideTimer(self._timers[2], self._timers[3])

    @property
    def mist_timer(self) -> BattleSideTimer:
        return BattleSideTimer(self._timers[4], self._timers[5])

    @property
    def safeguard_timer(self) -> BattleSideTimer:
        return BattleSideTimer(self._timers[6], self._timers[7])

    @property
    def follow_me_timer(self) -> BattleSideTimer:
        return BattleSideTimer(self._timers[8], self._timers[9])

    @property
    def spikes_amount(self) -> int:
        return self._timers[10]

    @property
    def is_fainted(self) -> bool:
        for battler in self.active_battlers:
            if battler.current_hp == 0:
                return True
        return False

    def has_ability(self, ability: "Ability"):
        return any(battler.ability.name == ability.name for battler in self.active_battlers)


class BattlePokemon:
    def __init__(self, data: bytes, status3: bytes, disable_struct: bytes, party_index: int):
        self._data = data
        self._status3 = status3
        self._disable_struct = disable_struct
        self.party_index = party_index

    def __eq__(self, other):
        if isinstance(other, BattlePokemon):
            return other._data == self._data
        else:
            return NotImplemented

    def __ne__(self, other):
        if isinstance(other, BattlePokemon):
            return other._data != self._data
        else:
            return NotImplemented

    @property
    def species(self) -> Species:
        return get_species_by_index(unpack_uint16(self._data[0x00:0x02]))

    @property
    def stats(self) -> StatsValues:
        return StatsValues(
            hp=self.total_hp,
            attack=unpack_uint16(self._data[0x02:0x04]),
            defence=unpack_uint16(self._data[0x04:0x06]),
            speed=unpack_uint16(self._data[0x06:0x08]),
            special_attack=unpack_uint16(self._data[0x08:0x0A]),
            special_defence=unpack_uint16(self._data[0x0A:0x0C]),
        )

    @property
    def ivs(self) -> StatsValues:
        packed_data = unpack_uint32(self._data[0x14:0x18])
        return StatsValues(
            hp=(packed_data >> 0) & 0b11111,
            attack=(packed_data >> 5) & 0b11111,
            defence=(packed_data >> 10) & 0b11111,
            speed=(packed_data >> 15) & 0b11111,
            special_attack=(packed_data >> 20) & 0b11111,
            special_defence=(packed_data >> 25) & 0b11111,
        )

    @property
    def moves(self) -> list[LearnedMove | None]:
        result = []
        for index in range(4):
            move_offset = 0x0C + (index * 2)
            move_index = unpack_uint16(self._data[move_offset : move_offset + 2])
            if move_index == 0:
                continue

            move = get_move_by_index(move_index)
            current_pp = self._data[0x24 + index]
            pp_bonuses = (self._data[0x3B] >> (2 * index)) & 0b11
            total_pp = move.pp + ((move.pp * 20 * pp_bonuses) // 100)

            result.append(LearnedMove(move, total_pp, current_pp, total_pp - move.pp))
        return result

    def knows_move(self, move: str | Move, with_pp_remaining: bool = False):
        if isinstance(move, Move):
            move = move.name
        for learned_move in self.moves:
            if (
                learned_move is not None
                and learned_move.move.name == move
                and (not with_pp_remaining or learned_move.pp > 0)
            ):
                return True
        return False

    @property
    def is_egg(self) -> bool:
        return bool(self._data[0x17] & 0b0100_0000)

    @property
    def ability(self) -> Ability:
        if len(self.species.abilities) > 1 and self._data[0x17] & 0b1000_0000:
            return self.species.abilities[1]
        else:
            return self.species.abilities[0]

    @property
    def ability_n(self) -> int:
        return self._data[0x20]

    @property
    def types(self) -> list[Type]:
        type1_index = self._data[0x21]
        type2_index = self._data[0x22]

        if type1_index == type2_index:
            return [get_type_by_index(type1_index)]
        else:
            return [get_type_by_index(type1_index), get_type_by_index(type2_index)]

    @property
    def stats_modifiers(self) -> StatsModifiers:
        return StatsModifiers.from_bytes(self._data[0x18:0x20])

    def modified_stats(self) -> StatsValues:
        stats = self.stats
        modifiers = self.stats_modifiers

        stages = [
            {10, 40},
            {10, 35},
            {10, 30},
            {10, 25},
            {10, 20},
            {10, 15},
            {10, 10},
            {15, 10},
            {20, 10},
            {25, 10},
            {30, 10},
            {35, 10},
            {40, 10},
        ]

        def modify(stat: int, modifier: int) -> int:
            return (stat * stages[modifier + 6][0]) // stages[modifier + 6][1]

        return StatsValues(
            hp=self.total_hp,
            attack=modify(stats.attack, modifiers.attack),
            defence=modify(stats.defence, modifiers.defence),
            speed=modify(stats.speed, modifiers.speed),
            special_attack=modify(stats.special_attack, modifiers.special_attack),
            special_defence=modify(stats.special_defence, modifiers.special_defence),
        )

    @property
    def current_hp(self) -> int:
        return unpack_uint16(self._data[0x28:0x2A])

    @property
    def current_hp_percentage(self) -> float:
        if self.total_hp == 0:
            return 0
        return 100 * self.current_hp / self.total_hp

    @property
    def total_hp(self) -> int:
        return unpack_uint16(self._data[0x2C:0x2E])

    @property
    def nature(self) -> Nature:
        return get_nature_by_index(self.personality_value % 25)

    @property
    def gender(self) -> Literal["male", "female", None]:
        ratio = self.species.gender_ratio
        if ratio == 0:
            return "male"

        elif ratio == 254:
            return "female"
        elif ratio == 255:
            return None
        value = self.personality_value & 0xFF
        return "male" if value >= ratio else "female"

    @property
    def level(self) -> int:
        return self._data[0x2A]

    @property
    def friendship(self) -> int:
        return self._data[0x2B]

    @property
    def held_item(self) -> Item | None:
        item_index = unpack_uint16(self._data[0x2E:0x30])
        if item_index != 0:
            return get_item_by_index(item_index)
        else:
            return None

    @property
    def total_exp(self) -> int:
        return unpack_uint32(self._data[0x44:0x48])

    @property
    def personality_value(self) -> int:
        return unpack_uint32(self._data[0x48:0x4C])

    @property
    def hidden_power_type(self) -> Type:
        ivs = self.ivs
        value = (
            ((ivs.hp & 1) << 0)
            + ((ivs.attack & 1) << 1)
            + ((ivs.defence & 1) << 2)
            + ((ivs.speed & 1) << 3)
            + ((ivs.special_attack & 1) << 4)
            + ((ivs.special_defence & 1) << 5)
        )
        value = (value * 15) // 63
        return get_type_by_name(HIDDEN_POWER_MAP[value])

    @property
    def hidden_power_damage(self) -> int:
        ivs = self.ivs
        value = (
            ((ivs.hp & 2) >> 1)
            + ((ivs.attack & 2) << 0)
            + ((ivs.defence & 2) << 1)
            + ((ivs.speed & 2) << 2)
            + ((ivs.special_attack & 2) << 3)
            + ((ivs.special_defence & 2) << 4)
        )
        return (value * 40) // 63 + 30

    @property
    def status_permanent(self) -> StatusCondition:
        return StatusCondition.from_bitfield(unpack_uint32(self._data[0x4C:0x50]))

    @property
    def status_temporary(self) -> list[TemporaryStatus]:
        return TemporaryStatus.from_bitfield(unpack_uint32(self._data[0x50:0x54]), unpack_uint32(self._status3))

    @property
    def ot_id(self) -> int:
        return unpack_uint32(self._data[0x54:0x58])

    @property
    def disabled_move(self) -> Move | None:
        disabled_move_index = unpack_uint16(self._disable_struct[0x04:0x06])
        if disabled_move_index == 0:
            return None
        else:
            return get_move_by_index(disabled_move_index)

    @property
    def transformed_personality_value(self) -> int:
        return unpack_uint32(self._disable_struct[0x00:0x04])

    @property
    def encored_move(self) -> Move | None:
        encored_move_index = unpack_uint16(self._disable_struct[0x04:0x06])
        if encored_move_index == 0:
            return None
        else:
            return get_move_by_index(encored_move_index)

    @property
    def protect_uses(self) -> int:
        return self._disable_struct[0x08]

    @property
    def stockpile_counter(self) -> int:
        return self._disable_struct[0x09]

    @property
    def substitute_hp(self) -> int:
        return self._disable_struct[0x0A]

    @property
    def disabled_turns_remaining(self) -> int:
        return self._disable_struct[0x0B] & 0b1111

    @property
    def encore_turns_remaining(self) -> int:
        return self._disable_struct[0x0E] & 0b1111

    @property
    def perish_song_turns_remaining(self) -> int:
        return self._disable_struct[0x0F] & 0b1111

    @property
    def fury_cutter_counter(self) -> int:
        return self._disable_struct[0x10]

    @property
    def rollout_turns_remaining(self) -> int:
        return self._disable_struct[0x11] & 0b1111

    @property
    def charge_turns_remaining(self) -> int:
        return self._disable_struct[0x12] & 0b1111

    @property
    def taunt_turns_remaining(self) -> int:
        return self._disable_struct[0x13] & 0b1111

    @property
    def battler_preventing_escape(self) -> int:
        return self._disable_struct[0x14]

    @property
    def battler_with_sure_hit(self) -> int:
        return self._disable_struct[0x15]

    @property
    def is_first_turn(self) -> int:
        return self._disable_struct[0x16]

    @property
    def is_loafing_around(self) -> bool:
        return self._disable_struct[0x18] & 1 == 1

    @property
    def truant_switch_in_hack(self) -> bool:
        return self._disable_struct[0x18] & 0b10 != 0

    @property
    def mimicked_moves(self) -> int:
        return (self._disable_struct[0x18] >> 4) & 0b1111

    @property
    def recharge_turns_remaining(self) -> int:
        return self._disable_struct[0x19]

    def __str__(self) -> str:
        return self.species.name


def get_battle_state() -> BattleState:
    if state_cache.battle_state.age_in_frames == 0:
        return state_cache.battle_state.value

    battle_state = BattleState(
        read_symbol("gBattleTypeFlags", size=0x04),
        read_symbol("gSideTimers", size=0x18),
        read_symbol("gBattlerPartyIndexes", size=0x08),
        read_symbol("gBattlePartyCurrentOrder", size=0x03),
        read_symbol("gBattlersCount", size=0x01)[0],
        read_symbol("gBattleMons", size=0x160),
        read_symbol("gStatuses3", size=0x10),
        read_symbol("gDisableStructs", size=0x70),
        read_symbol("gAbsentBattlerFlags", size=0x01)[0],
        read_symbol("gBattleResults", offset=0x13, size=1)[0],
        unpack_uint16(read_symbol("gBattleWeather", size=0x02)),
    )

    state_cache.battle_state = battle_state
    return battle_state


def battle_is_active() -> bool:
    callback1 = get_symbol_name_before(unpack_uint32(read_symbol("gMain", 0, 4))).lower()
    return callback1 == "battlemaincb1"


def get_main_battle_callback() -> str:
    return get_callback_for_pointer_symbol("gBattleMainFunc")


def get_current_battle_script_instruction() -> str:
    return get_callback_for_pointer_symbol("gBattleScriptCurrInstr")


def get_battle_controller_callback(battler_index: int) -> str:
    return get_callback_for_pointer_symbol("gBattlerControllerFuncs", offset=4 * battler_index)


class BattleOutcome(Enum):
    InProgress = 0
    Won = 1
    Lost = 2
    Draw = 3
    RanAway = 4
    PlayerTeleported = 5
    OpponentFled = 6
    Caught = 7
    NoSafariBallsLeft = 8
    Forfeited = 9
    OpponentTeleported = 10
    LinkBattleRanAway = 128


def get_last_battle_outcome() -> BattleOutcome:
    return BattleOutcome(read_symbol("gBattleOutcome", size=1)[0])


def get_battle_type() -> BattleType:
    return BattleType(unpack_uint32(read_symbol("gBattleTypeFlags", size=0x04)))


class EncounterType(Enum):
    Trainer = "trainer"
    Tutorial = "tutorial"
    Roamer = "roamer"
    Static = "static"
    Land = "land"
    Surfing = "surfing"
    FishingWithOldRod = "fishing_old_rod"
    FishingWithGoodRod = "fishing_good_rod"
    FishingWithSuperRod = "fishing_super_rod"
    RockSmash = "rock_smash"
    Hatched = "hatched"
    Gift = "gift"

    @property
    def is_wild(self) -> bool:
        return self is not EncounterType.Trainer and self is not EncounterType.Tutorial

    @property
    def is_fishing(self) -> bool:
        return self in (
            EncounterType.FishingWithOldRod,
            EncounterType.FishingWithGoodRod,
            EncounterType.FishingWithSuperRod,
        )

    @property
    def verb(self) -> str:
        if self is EncounterType.Hatched:
            return "hatched"
        elif self is EncounterType.Gift:
            return "received"
        else:
            return "encountered"


def get_encounter_type() -> EncounterType:
    script_stack = get_global_script_context().stack
    if "EventScript_EggHatch" in script_stack or "S_EggHatch" in script_stack:
        return EncounterType.Hatched

    battle_type = get_battle_type()

    if BattleType.WallyTutorial in battle_type:
        return EncounterType.Tutorial

    if BattleType.Trainer in battle_type:
        return EncounterType.Trainer

    if BattleType.Roamer in battle_type:
        return EncounterType.Roamer

    if (
        BattleType.Regi in battle_type
        or BattleType.Groudon in battle_type
        or BattleType.Kyogre in battle_type
        or BattleType.KyogreGroudon in battle_type
        or BattleType.Rayquaza in battle_type
        or BattleType.Legendary in battle_type
    ):
        return EncounterType.Static

    if context.rom.is_frlg:
        # FR/LG use some of Emerald's battle type flags a bit differently; the following checks
        # stand for: (1) the Ghost in Lavender Tower, (2) Scripted Encounters, (3) Legendary Pokémon
        if (
            BattleType.Palace in battle_type
            or BattleType.TwoOpponents in battle_type
            or BattleType.Arena in battle_type
        ):
            return EncounterType.Static

    if "EventScript_BattleKecleon" in script_stack:
        return EncounterType.Static
    if "BattleFrontier_OutsideEast_EventScript_WaterSudowoodo" in script_stack:
        return EncounterType.Static
    if "EventScript_SmashRock" in script_stack:
        return EncounterType.RockSmash

    if context.stats.last_fishing_attempt is not None and context.stats.last_fishing_attempt.encounter is not None:
        if get_opponent().personality_value == context.stats.last_fishing_attempt.encounter.personality_value:
            if context.stats.last_fishing_attempt.rod is FishingRod.SuperRod:
                return EncounterType.FishingWithSuperRod
            elif context.stats.last_fishing_attempt.rod is FishingRod.GoodRod:
                return EncounterType.FishingWithGoodRod
            else:
                return EncounterType.FishingWithOldRod

    if AvatarFlags.Surfing in get_player_avatar().flags:
        return EncounterType.Surfing
    else:
        return EncounterType.Land

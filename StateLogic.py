from .Data import star_locations
from .Options import StarShuffle
from rule_builder.rules import Has, True_


def super_hammer(state, player):
    return state.has("Progressive Hammer", player, 1)


def super_boots(state, player):
    return state.has("Progressive Boots", player, 1)


def ultra_hammer(state, player):
    return state.has("Progressive Hammer", player, 2)


def ultra_boots(state, player):
    return state.has("Progressive Boots", player, 2)


def tube_curse(state, player):
    return state.has("Paper Mode", player) and state.has("Tube Mode", player)


def sewer_westside(state, player):
    return (tube_curse(state, player) or state.has("Bobbery", player)
            or (state.has("Paper Mode", player) and state.has("Contact Lens", player))
            or (ultra_hammer(state, player) and (state.has("Paper Mode", player)
            or (ultra_boots(state, player) and state.has("Yoshi", player)))))


def sewer_westside_ground(state, player):
    return ((state.has("Contact Lens", player) and state.has("Paper Mode", player))
            or state.has("Bobbery", player) or tube_curse(state, player) or ultra_hammer(state, player))


def twilight_town(state, player):
    return ((sewer_westside(state, player) and state.has("Yoshi", player))
            or (sewer_westside_ground(state, player) and ultra_boots(state, player)))


def fahr_outpost(state, player):
    return ultra_hammer(state, player) and twilight_town(state, player)


def keelhaul_key(state, player):
    return (state.has("Yoshi", player) and tube_curse(state, player)
            and state.has("Old Letter", player))


def riverside(state, player):
    return (state.has("Vivian", player) and state.has("Autograph", player)
            and state.has("Ragged Diary", player) and state.has("Blanket", player)
            and state.has("Vital Paper", player) and state.has("Train Ticket", player))


def pit(state, player):
    return state.has("Paper Mode", player) and state.has("Plane Mode", player)


def ttyd(state, player):
    return (state.has("Plane Mode", player) or super_hammer(state, player)
            or (state.has("Flurrie", player) and (state.has("Bobbery", player) or tube_curse(state, player)
            or (state.has("Contact Lens", player) and state.has("Paper Mode", player)))))


def palace(state, player, chapters: int, star_shuffle: int):
    return ttyd(state, player) and (state.has("stars", player, chapters) if star_shuffle == StarShuffle.option_all else state.has("required_stars", player, chapters))


def riddle_tower(state, player):
    return tube_curse(state, player) and state.has("Palace Key", player) and state.has("Bobbery", player) and state.has("Boat Mode", player) and state.has("Star Key", player) and state.has("Palace Key (Tower)", player, 8)


def key_any(state, player):
    return state.has("Red Key", player) or state.has("Blue Key", player)


def key_both(state, player):
    return state.has("Red Key", player) and state.has("Blue Key", player)


def chapter_completions(state, player, count):
    return len([location for location in star_locations if state.can_reach(location, "Location", player)]) >= count


class Rules:
    """Rule-builder counterparts to the StateLogic functions, for use in static region connection dicts."""

    @staticmethod
    def fallen_pipe():
        """Bobbery, or Paper Mode + Tube Mode."""
        return Has("Bobbery") | (Has("Paper Mode") & Has("Tube Mode"))

    @staticmethod
    def ultra_boots():
        return Has("Progressive Boots", 2)

    @staticmethod
    def ultra_hammer():
        return Has("Progressive Hammer", 2)

    @staticmethod
    def pit():
        return Has("Paper Mode") & Has("Plane Mode")

    @staticmethod
    def partner_press_switch():
        """Koops can activate switches from a distance."""
        return Has("Koops")

    @staticmethod
    def riddle_tower():
        return (Has("Paper Mode") & Has("Tube Mode") & Has("Palace Key") &
                Has("Bobbery") & Has("Boat Mode") & Has("Star Key") &
                Has("Palace Key (Tower)", 8))

    @staticmethod
    def PalaceAccess(star_count: int, star_shuffle: int):
        """Entry condition for the final gate before Shadow Queen."""
        _ttyd = (
            Has("Plane Mode") |
            Has("Progressive Hammer", 2) |
            (Has("Flurrie") & (
                Has("Bobbery") |
                (Has("Paper Mode") & Has("Tube Mode")) |
                (Has("Contact Lens") & Has("Paper Mode"))
            ))
        )
        if star_shuffle == StarShuffle.option_all:
            return _ttyd & Has("stars", star_count)
        return _ttyd & Has("required_stars", star_count)

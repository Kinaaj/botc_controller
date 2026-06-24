from enum import Enum

class AssetsAudio(Enum):
    OTHER = "other"
    # drawing music, blesk, bells
    NIGHT_EFFECTS = "night_effects"
    # vrana, vlci (random efekt pri zvonech)
    NIGHT_BACKGROUND = "night_background"
    # dlouhe zvuky noci
    DAY = "day"
    # zvuk hodin, hlasovani?, zalar, poprava crowd, poprava chop
    SCREAM_WOMAN = "scream_woman"
    # random krik zeny
    SCREAM_MAN = "scream_man"
    # random krik muze
    GOOD_WIN = "good_win"
    # random good hudba
    EVIL_WIN = "evil_win"
    # random evil hudba



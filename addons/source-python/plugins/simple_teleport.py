"""Plugin by Kill, Steam: id/killtmwc."""

# =============================================================================
# >> IMPORTS
# =============================================================================
# Source.Python
from commands import CommandReturn
from commands.typed import TypedSayCommand, TypedClientCommand
from cvars.public import PublicConVar
from events import Event
from filters.players import PlayerIter
from mathlib import Vector
from menus.radio import PagedRadioMenu, PagedRadioOption
from messages import SayText2
from players.dictionary import PlayerDictionary
from players.entity import Player
from plugins.info import PluginInfo
from translations.strings import LangStrings

# =============================================================================
# >> PLUGIN INFO
# =============================================================================
info = PluginInfo("simple_teleport")
info.basename = "simple_teleport"
info.name = "Simple teleport plugin"
info.description = "Easily teleport players"
info.author = "Kill, iPlayer"
info.version = "1.0"
info.url = "https://steamcommunity.com/id/killtmwc | " \
           "https://steamcommunity.com/id/its_iPlayer"

PublicConVar(name=info.basename + "_version", value=info.version,
             description=info.description)


# =============================================================================
# >> CONSTANTS
# =============================================================================
STUCK_RELEASE_TIMEOUT = 4.0
VEC_P2P_OFFSET = Vector(0, 0, 80)


# =============================================================================
# >> GLOBAL VARIABLES
# =============================================================================
saved_locs = PlayerDictionary(lambda index: None)
selected_p2p_first = PlayerDictionary(lambda index: None)


# =============================================================================
# >> TRANSLATION
# =============================================================================
LANG = LangStrings(info.basename)
SAY_PLAYER_DISCONNECT = SayText2(LANG["player_disconnected"])
SAY_LOC_SAVED = SayText2(LANG["loc_saved"])
SAY_NO_LOC_SAVED = SayText2(LANG["no_loc_saved"])
SAY_SELF_TELEPORTED_TO = SayText2(LANG["self_teleported_to"])
SAY_TELEPORTED_TO_ME = SayText2(LANG["teleported_to_me"])
SAY_TELEPORTED_TO_SAVED_RS = SayText2(LANG["teleport_to_saved_rs"])
SAY_TOGGLE_DISABLED = SayText2(LANG["auto_toggle_disable"])
SAY_TOGGLE_ENABLED = SayText2(LANG["auto_toggle_enable"])
SAY_SAVE_LOCATION_FIRST = SayText2(LANG["save_location_first"])


# =============================================================================
# >> FUNCTIONS
# =============================================================================
def save_location(player: Player):
    try:
        auto_tele = True if saved_locs[player.index]['auto_tele'] else False
    except TypeError:
        auto_tele = False
    saved_locs[player.index] = {
        'origin': player.origin,
        'angle': player.view_angle,
        'auto_tele': auto_tele,
    }
    SAY_LOC_SAVED.send(player.index)


def teleport_to_saved_loc(player, loc_owner_index=None):
    if loc_owner_index is None:
        loc_owner_index = player.index

    if saved_locs[loc_owner_index] is None:
        SAY_NO_LOC_SAVED.send(loc_owner_index)
    else:
        player.teleport(
            saved_locs[loc_owner_index]['origin'],
            angle=saved_locs[loc_owner_index]['angle']
        )


def teleport_player_to_player(player_from, player_to):
    player_from.teleport(player_to.origin + VEC_P2P_OFFSET)

    SAY_SELF_TELEPORTED_TO.send(
        player_from.index,
        name=player_to.name
    )

    SAY_TELEPORTED_TO_ME.send(
        player_to.index,
        name=player_from.name
    )


def toggle_auto(player: Player):
    try:
        if saved_locs[player.index]['auto_tele'] is False:
            saved_locs[player.index]['auto_tele'] = True
            return SAY_TOGGLE_ENABLED.send()

        saved_locs[player.index]['auto_tele'] = False
        SAY_TOGGLE_DISABLED.send(player.index)
    except:
        SAY_SAVE_LOCATION_FIRST.send()


# =============================================================================
# >> POPUPS
# =============================================================================
popup_main = PagedRadioMenu(
    [
        PagedRadioOption(LANG["menu_teleport_to_player"], 1),
        PagedRadioOption(LANG["menu_teleport_to_me"], 2),
        PagedRadioOption(LANG["menu_save_location"], 3),
        PagedRadioOption(LANG["menu_teleport_to_saved"], 4),
        PagedRadioOption(LANG["menu_teleport_others"], 5),
        PagedRadioOption(LANG["menu_teleport_p2p"], 6),
        PagedRadioOption(LANG["menu_toggle_auto"], 7)
    ],
    title="Simple Teleport"
)
popup_to_player = PagedRadioMenu(
    parent_menu=popup_main,
    title=LANG["menu_teleport_to_player"]
)
popup_to_me = PagedRadioMenu(
    parent_menu=popup_main,
    title=LANG["menu_teleport_to_me"]
)
popup_others_to_loc = PagedRadioMenu(
    parent_menu=popup_main,
    title=LANG["menu_teleport_to_saved"]
)
popup_p2p_first = PagedRadioMenu(
    parent_menu=popup_main,
    title=LANG["menu_teleport_p2p_dest"]
)
popup_p2p_second = PagedRadioMenu(
    parent_menu=popup_p2p_first,
    title=LANG["menu_teleport_p2p_target"]
)


main_popup_option_actions = {
    1: (lambda index: None, popup_to_player),
    2: (lambda index: None, popup_to_me),
    3: (lambda index: save_location(Player(index)), popup_main),
    4: (lambda index: teleport_to_saved_loc(Player(index)), popup_main),
    5: (lambda index: None, popup_others_to_loc),
    6: (lambda index: None, popup_p2p_first),
    7: (lambda index: toggle_auto(Player(index)), popup_main)
}


# =============================================================================
# >> POPUP BUILD CALLBACKS
# =============================================================================
@popup_p2p_first.register_build_callback
@popup_p2p_second.register_build_callback
@popup_to_player.register_build_callback
@popup_others_to_loc.register_build_callback
@popup_to_me.register_build_callback
def callback(popup, index):
    popup[:] = list(
        PagedRadioOption(player.name, value=player.userid) for
        player in PlayerIter('alive') if player.index != index)


# =============================================================================
# >> POPUP SELECT CALLBACKS
# =============================================================================
@popup_main.register_select_callback
def callback(popup, index, option):
    action, next_popup = main_popup_option_actions[option.value]

    action(index)
    return next_popup


@popup_p2p_first.register_select_callback
def callback(popup, index, option):
    selected_p2p_first[index] = option.value
    return popup_p2p_second


@popup_p2p_second.register_select_callback
def callback(popup, index, option):
    userid_from, userid_to = option.value, selected_p2p_first.pop(index)

    try:
        player_from = Player.from_userid(userid_from)
        player_to = Player.from_userid(userid_to)
    except ValueError:
        SAY_PLAYER_DISCONNECT.send(index)

    else:
        teleport_player_to_player(player_from, player_to)


@popup_to_me.register_select_callback
def callback(popup, index, option):
    player_to = Player(index)
    try:
        player_from = Player.from_userid(option.value)
    except:
        SAY_PLAYER_DISCONNECT.send(index)
    else:
        teleport_player_to_player(player_from, player_to)


@popup_to_player.register_select_callback
def callback(popup, index, option):
    player_from = Player(index)
    try:
        player_to = Player.from_userid(option.value)
    except:
        SAY_PLAYER_DISCONNECT.send(index)
    else:
        teleport_player_to_player(player_from, player_to)


@popup_others_to_loc.register_select_callback
def callback(popup, index, option):
    try:
        player = Player.from_userid(option.value)
    except:
        SAY_PLAYER_DISCONNECT.send(index)
    else:
        teleport_to_saved_loc(player, loc_owner_index=index)

    return popup_main


# =============================================================================
# >> COMMANDS
# =============================================================================
@TypedClientCommand("sp_teleport")
@TypedSayCommand("!tp", permission="kst_teleport")  # Alias
@TypedSayCommand("/tp", permission="kst_teleport")  # Alias
@TypedSayCommand("/teleport", permission="kst_teleport")
@TypedSayCommand("!teleport", permission="kst_teleport")
def cmd_teleport(cmd):
    popup_main.send(cmd.index)
    if cmd.command[0].startswith('/'):
        return CommandReturn.BLOCK
    return CommandReturn.CONTINUE


@TypedSayCommand("!tpstuck", "kst_teleport")
def cmd_teleport(cmd):
    player = Player(cmd.index)

    initial_noblock = player.noblock
    player.set_noblock(True)
    player.delay(
        STUCK_RELEASE_TIMEOUT, player.set_noblock, (initial_noblock, ))


# =============================================================================
# >> EVENTS
# =============================================================================
@Event("round_start")
def round_start(event):
    for player in PlayerIter(is_filters='alive'):
        try:
            if not saved_locs[player.index]['auto_tele']:
                continue
            player.teleport(
                saved_locs[player.index]['origin'],
                saved_locs[player.index]['angle']
            )
            SAY_TELEPORTED_TO_SAVED_RS.send(player.index)
        except:
            pass

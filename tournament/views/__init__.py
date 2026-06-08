# views/__init__.py
from .auth_views import (register, activate_account, log_tournament_details, custom_password_reset,
    custom_password_reset_done,custom_password_reset_confirm,custom_password_reset_complete,custom_login,custom_logout
)
from .profile_views import profile, profile_edit, player_stats_api, get_role_icon
from .host_views import apply_host
from .tournament_views import (
    home, create_tournament, tournament_detail, my_tournaments,
    start_tournament, cancel_tournament_start, tournament_games,
    complete_tournament, recalculate_tournament_stats
)
from .player_management_views import (
    get_players_for_tournament, add_player_to_tournament,
    remove_player_from_tournament, create_player_for_tournament,
    delete_player, toggle_data_visibility
)
from .game_views import game_input, game_edit, game_view
from .public_views import (
    tournament_public, tournament_public_stats,
    tournament_public_games, public_game_view
)
from .beta_views import beta_game, beta_start_game, beta_vote, beta_day, beta_night
import random
import sys

from Helper import Action


class GameState:
    def __init__(self):
        self.player_1 = Player()
        self.player_2 = Player()

    def __str__(self):
        return str(self.get_dict())

    def get_dict(self):
        data = {'p1': self.player_1.get_dict(), 'p2': self.player_2.get_dict()}
        return data

    def difference(self, received_game_state):
        """Find the difference between the current game_state and received"""
        try:
            recv_p1_dict = received_game_state["p1"]
            recv_p2_dict = received_game_state["p2"]

            p1 = self.player_1.get_difference(recv_p1_dict)
            p2 = self.player_2.get_difference(recv_p2_dict)

            diff = {'p1': p1, 'p2': p2}

            message = "Game state difference : " + str(diff)
        except KeyError:
            message = "Key error in the received Json"
        return message

    def init_players_random(self):
        """ Helper function to randomize the game state"""
        for player_id in [1, 2]:
            hp = random.randint(10, 90)
            bullets_remaining = random.randint(0, 6)
            grenades_remaining = random.randint(0, 3)
            shield_health = random.randint(0, 30)
            num_unused_shield = random.randint(0, 3)
            num_deaths = random.randint(0, 3)

            self._init_player(player_id, bullets_remaining, grenades_remaining, hp,
                              num_deaths, num_unused_shield,
                              shield_health)

    def _init_player (self, player_id, bullets_remaining, grenades_remaining, hp,
                      num_deaths, num_unused_shield, shield_health):
        if player_id == 1:
            player = self.player_1
        else:
            player = self.player_2
        player.set_state(bullets_remaining, grenades_remaining, hp, num_deaths,
                         num_unused_shield, shield_health)

    def perform_action(self, action, player_id, position_1, position_2):
        """use the user sent action to alter the game state"""

        # perform sanity check to see if our function handles all the actions
        all_actions = {"gun", "shield", "grenade", "reload", "web", "portal", "punch", "hammer", "spear"}
        if not Action.actions_match(all_actions):
            print("All actions not handled by GameState.perform_action")
            sys.exit(-1)

        if player_id == 1:
            attacker = self.player_1
            opponent = self.player_2
        else:
            attacker = self.player_2
            opponent = self.player_1

        # check if the players can see each other
        can_see = self._can_see (position_1, position_2)

        # perform the actual action
        if action == "gun":
            attacker.shoot(opponent, can_see)
        elif action == "shield":
            attacker.shield()
        elif action == "grenade":
            attacker.grenade(opponent, can_see)
        elif action == "reload":
            attacker.reload()
        elif action in {"web", "portal", "punch", "hammer", "spear"}:
            # all these have the same behaviour
            attacker.harm(opponent, can_see)
        elif action == "logout":
            # has no change in game state
            pass
        else:
            # invalid action we do nothing
            pass

    @staticmethod
    def _can_see(position_1, position_2):
        """check if the players can see each other"""
        can_see = True
        # the players cannot see each other only if one is quadrant 4 and other is in any other quadrant
        if position_1 == 4 and position_2 != 4:
            can_see = False
        elif position_1 != 4 and position_2 == 4:
            can_see = False
        return can_see


class Player:
    def __init__(self):
        self.max_grenades       = 2
        self.max_shields        = 3
        self.hp_bullet          = 10
        self.hp_grenade         = 30
        self.max_shield_health  = 30
        self.max_bullets        = 6
        self.max_hp             = 100

        self.num_deaths         = 0

        self.hp             = self.max_hp
        self.num_bullets    = self.max_bullets
        self.num_grenades   = self.max_grenades
        self.hp_shield      = 0
        self.num_shield     = self.max_shields

    def __str__(self):
        return str(self.get_dict())

    def get_dict(self):
        data = dict()
        data['hp']              = self.hp
        data['bullets']         = self.num_bullets
        data['grenades']        = self.num_grenades
        data['shield_hp']       = self.hp_shield
        data['deaths']          = self.num_deaths
        data['shields']         = self.num_shield
        return data

    def get_difference(self, recv_dict):
        """get difference between the received player sate and our state"""
        data = self.get_dict()
        for key in list(data.keys()):
            val = data[key] - recv_dict[key]
            if val == 0:
                # there is no difference so we delete the element
                data.pop(key)
            else:
                data[key] = val
        return data

    def set_state(self, bullets_remaining, grenades_remaining, hp, num_deaths, num_unused_shield, shield_health):
        self.hp             = hp
        self.num_bullets    = bullets_remaining
        self.num_grenades   = grenades_remaining
        self.hp_shield      = shield_health
        self.num_shield     = num_unused_shield
        self.num_deaths     = num_deaths

    def shoot(self, opponent, can_see):
        while True:
            # check the ammo
            if self.num_bullets <= 0:
                break
            self.num_bullets -= 1

            # check if the opponent is visible
            if not can_see:
                break

            opponent.reduce_health(self.hp_bullet)
            break

    def reduce_health(self, hp_reduction):
        # use the shield to protect the player
        if self.hp_shield > 0:
            new_hp_shield  = max (0, self.hp_shield-hp_reduction)
            # how much should we reduce the HP by?
            hp_reduction   = max (0, hp_reduction-self.hp_shield)
            # update the shield HP
            self.hp_shield = new_hp_shield

        # reduce the player HP
        self.hp = max(0, self.hp - hp_reduction)
        if self.hp == 0:
            # if we die, we spawn immediately
            self.num_deaths += 1

            # initialize all the states
            self.hp             = self.max_hp
            self.num_bullets    = self.max_bullets
            self.num_grenades   = self.max_grenades
            self.hp_shield      = 0
            self.num_shield     = self.max_shields

    def shield(self):
        """Activate shield"""
        while True:
            if self.num_shield <= 0:
                # check the number of shields available
                break
            elif self.hp_shield > 0:
                # check if shield is already active
                break
            self.hp_shield = self.max_shield_health
            self.num_shield -= 1

    def grenade(self, opponent, can_see):
        """Throw a grenade at opponent"""
        while True:
            # check the ammo
            if self.num_grenades <= 0:
                break
            self.num_grenades -= 1

            # check if the opponent is visible
            if not can_see:
                break

            opponent.reduce_health(self.hp_grenade)
            break

    def harm(self, opponent, can_see):
        """ We can harm am opponent if we can see them"""
        if can_see:
            opponent.reduce_health(self.hp_bullet)

    def reload(self):
        """ perform reload only if the magazine is empty"""
        if self.num_bullets <= 0:
            self.num_bullets = self.max_bullets

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


    def get_dict(self):
        data = dict()
        data['hp']              = self.hp
        data['bullets']         = self.num_bullets
        data['grenades']        = self.num_grenades
        data['shield_hp']       = self.hp_shield
        data['deaths']          = self.num_deaths
        data['shields']         = self.num_shield
        return data
    

    def damage(self, damage):
        if self.hp_shield > 0:
            self.hp_shield -= damage
        
            # bleedthrough
            if self.hp_shield < 0:
                self.hp += self.hp_shield
                self.hp_shield = 0

        else:
            self.hp -= damage

        if self.hp <= 0:
            self.num_deaths += 1
            self.hp             = self.max_hp
            self.num_bullets    = self.max_bullets
            self.num_grenades   = self.max_grenades
            self.hp_shield      = 0
            self.num_shield     = self.max_shields


    def shoot(self, defender, isHit):
        if self.num_bullets > 0:
            self.num_bullets -= 1
            if isHit:
                defender.damage(self.hp_bullet)
        else:
            pass


    def grenade(self, defender, isHit):
        if self.num_grenades > 0:
            self.num_grenades -= 1
            if isHit:
                defender.damage(self.hp_grenade)
        else:
            pass


    def shield(self):
        if self.num_shield > 0:
            self.hp_shield = self.max_shield_health
            self.num_shield -= 1
        else:
            pass


    def reload(self):
        if self.num_bullets > 0:
            pass
        else:
            self.num_bullets = self.max_bullets


    def generic_action(self, defender, isHit):
        if isHit:
            defender.damage(self.hp_bullet)
        else:
            pass


class GameState:

    def __init__(self):
        self.p1 = Player()
        self.p2 = Player()


    def get_dict(self):
        data = {'p1': self.p1.get_dict(), 'p2': self.p2.get_dict()}
        return data

    def __str__(self):
        return str(self.get_dict())
    

    def update(self, msg):

        player_id = msg["player_id"]
        action = msg["action"]
        isHit = msg["isHit"]

        if player_id == "1":
            attacker = self.p1
            defender = self.p2
        else:
            attacker = self.p2
            defender = self.p1

        if action == "gun":
            attacker.shoot(defender, isHit)
                
        elif action == "grenade":
            attacker.grenade(defender, isHit)

        elif action == "shield":
            attacker.shield()

        elif action == "reload":
            attacker.reload()

        elif action in {"web", "portal", "punch", "hammer", "spear"}:
            attacker.generic_action(defender, isHit)
        
        elif action == "logout":
            # logout
            pass

        else:
            # invalid
            pass

 
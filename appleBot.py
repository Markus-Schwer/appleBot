from utils import *


class AppleBot:
    def __init__(self, socket_manager):
        self.connection = socket_manager

        self.id = None
        self.name = self.__class__.__name__
        self.opponents = {}
        self.planets = []
        self.angle = 0
        self.speed = 10
        self.last_shot = []

    def init(self):
        self.connection.send_str(f"n {self.name}")

    def msg(self, message):
        print(f"[{self.__class__.__name__}]: {message}")

    def set_id(self, cid):
        self.id = cid
        self.msg(f"set id to {cid}")

    def del_opponent(self, oid):
        del self.opponents[oid]
        self.msg(f"opponent with id {oid} left the game.")

    def add_opponent(self, opponent):
        self.opponents[opponent.id] = opponent
        self.msg(f"opponent with id {opponent.id} joined the game.")

    def shoot(self):
        self.angle += 361 / 36.0
        if self.angle > 180:
            self.angle -= 360
        return self.speed, self.angle

    def report_shot(self, curve):
        self.last_shot = curve

    def set_planets(self, planets):
        self.planets = planets
        self.msg(f"Planet data for {len(planets)} planets received.")

    def loop(self):
        msg_type, payload = self.connection.receive_struct("II")

        # bot has joined
        if msg_type == 1:
            self.set_id(payload)

        # player left
        elif msg_type == 2:
            self.del_opponent(payload)

        # player joined/reset
        elif msg_type == 3:
            x, y = self.connection.receive_struct("ff")
            self.add_opponent(Opponent(x, y, payload))

        # someone shot
        elif msg_type == 4:
            n = self.connection.receive_struct("I")[0]
            curves = []
            for i in range(n):
                curve = self.connection.receive_struct("ff")
                curves.append(curve)
            if payload == self.id:
                self.report_shot(curves)
            else:
                self.msg(f"Ignoring shot by player {payload}")

        # planet pos
        elif msg_type == 9:
            planets = []
            self.connection.receive_struct("I")
            for i in range(payload):
                x, y, radius, mass = self.connection.receive_struct("dddd")
                planets.append(Planet(x, y, radius, mass))
            self.set_planets(planets)

        else:
            self.msg(f"Unexpected message_type: '{msg_type}'\n\t- data: '{payload}'")


from utils import *
from datetime import datetime

from SimulationHandler import SimulationHandler

ENERGY_UPDATE_INTERVAL = 2


class AppleBot:
    def __init__(self, socket_manager):
        self.connection = socket_manager
        self.simulation = SimulationHandler()

        self.id = None
        self.name = self.__class__.__name__
        self.planets = []
        self.players = {}
        self.angle = 0
        self.speed = 10
        self.last_shot = []
        self.energy = 0

        self.last_energy_update = datetime.now()

        self.init()

    def init(self):
        self.connection.send_str(f"n {self.name}")

    def msg(self, message):
        print(f"[{self.__class__.__name__}]: {message}")

    def set_id(self, cid):
        self.id = cid

    def shoot(self):
        self.angle += 361 / 36.0
        if self.angle > 180:
            self.angle -= 360
        return self.speed, self.angle

    def report_shot(self, curve):
        self.last_shot = curve

    def update_simulation(self):
        self.simulation.set_field(self.planets, self.players.values())

    def process_incoming(self):
        struct_data = self.connection.receive_struct("II")

        # recv timed out
        if struct_data is None:
            return

        msg_type, payload = struct_data

        # bot has joined
        if msg_type == 1:
            self.set_id(payload)
            self.msg(f"set id to {payload}")

        # player left
        elif msg_type == 2:
            del self.players[payload]

        # player joined/reset
        elif msg_type == 3:
            x, y = self.connection.receive_struct("ff")
            if payload not in self.players:
                self.msg(f"player {payload} joined the game at ({round(x)},{round(y)})")
            else:
                self.msg(f"player {payload} moved to ({round(x)},{round(y)})")
            self.players[payload] = Player(x, y, payload)

        # someone shot
        elif msg_type == 4:
            n = self.connection.receive_struct("I")[0]
            curves = []
            for i in range(n):
                curve = self.connection.receive_struct("ff")
                curves.append(curve)
            if payload == self.id:
                self.report_shot(curves)

        # game mode (unused)
        elif msg_type == 7:
            _ = self.connection.receive_struct('I')[0]

        # own energy
        elif msg_type == 8:
            self.energy = math.floor(self.connection.receive_struct("d")[0])

        # planet pos
        elif msg_type == 9:
            # discard planet byte count
            self.connection.receive_struct("I")

            self.planets = []
            for i in range(payload):
                x, y, radius, mass = self.connection.receive_struct("dddd")
                self.planets.append(Planet(x, y, radius, mass, i))
            self.msg(f"planet data for {len(self.planets)} planets received")
            self.update_simulation()

        # unknown MSG_TYPE
        else:
            self.msg(f"Unexpected message_type: '{msg_type}'\n\t- data: '{payload}'")

    def loop(self):
        if (datetime.now() - self.last_energy_update).seconds > ENERGY_UPDATE_INTERVAL:
            self.connection.send_str("u")
            self.last_energy_update = datetime.now()

        self.process_incoming()

import math

import numpy as np
from tqdm import tqdm

import pygame
from pygame.locals import *

import utils
import colorsys
from datetime import datetime

from scipy import optimize
from scipy.spatial.distance import cdist

vertCircle = np.zeros((32, 2))

for i in range(8):
    a = 2 * math.pi / 32 + 2 * math.pi / 16 * i
    x = math.sin(a)
    y = math.cos(a)
    vertCircle[i][0] = x
    vertCircle[i][1] = y
    vertCircle[8 + i][0] = -x
    vertCircle[8 + i][1] = -y
    vertCircle[16 + 2 * i][0] = x
    vertCircle[16 + 2 * i][1] = y
    vertCircle[16 + 2 * i + 1][0] = -x
    vertCircle[16 + 2 * i + 1][1] = -y


class SimulationHandler:

    def __init__(self):
        self.A = 2e6
        self.battlefieldW = math.sqrt(self.A * 16 / 9)
        self.battlefieldH = math.sqrt(self.A * 9 / 16)
        self.playerSize = 4.0 * 0.8
        self.margin = 500
        self.players = None
        self.planets = None
        self.maxSegments = 4000
        self.segmentSteps = 25
        self.maxPlayers = 12
        self.numPlanets = 24

        self.own_id = None
        self.position = None
        self.initialized = False

        self.battlefieldW = 1885
        self.battlefieldH = 1060

        self.maxPower = 50
        self.dragging = False
        self.power = 0
        self.angle = 0

        self.lastTrace = []
        self.lastTraceTime = datetime.now()
        self.traceUpdateDelay = 500

        pygame.init()
        self.display = (1120, 630)
        self.surface = pygame.display.set_mode(self.display)
        pygame.display.set_caption("AppleBot")
        self.reshape(self.display[0], self.display[1])

    def set_field(self, planets, players, own_id):
        self.initialized = True
        self.players = players
        self.planets = planets
        self.own_id = own_id

        for player in players:
            if player.id == own_id:
                self.position = player.position

    def simulate_own_shot(self, angle, energy):
        missile = utils.Missile(self.position, -angle + 90, energy)
        # print(f"{angle}° {energy}")
        missile_trace = []
        missile_result = utils.MissileResult.RES_UNDETERMINED
        info = 0
        sim_running = True
        missile_pos = missile.position
        missile_speed = missile.speed

        while sim_running:
            for planet in self.planets:
                # calculate vector from planet to missile and distance
                tmp_v = planet.position - missile_pos
                distance = np.linalg.norm(tmp_v)

                # collision with planet?
                if distance <= planet.radius:
                    missile_result = utils.MissileResult.RES_HIT_PLANET
                    info = planet.id
                    sim_running = False
                    break

                # normalize tmp vector
                tmp_v /= distance
                # apply Newtonian Gravity
                tmp_v *= planet.mass / (distance**2)
                # shortening to segment
                tmp_v /= self.segmentSteps

                # add tmp vector to missile speed vector
                missile_speed += tmp_v

            if not sim_running:
                break

            # shortening resulting speed to segment
            tmp_v = missile_speed / self.segmentSteps
            # apply speed vector
            new_missile_pos = missile_pos + tmp_v

            # check if missile hit a player
            for player in self.players:
                distance = np.linalg.norm(player.position - new_missile_pos)

                if distance <= self.playerSize and missile.left_source:
                    missile_result = utils.MissileResult.RES_HIT_PLAYER
                    info = player.id
                    sim_running = False
                    break

                if distance > self.playerSize + 1.0 and player.id == self.own_id:
                    missile.left_source = True

            if not sim_running:
                break

            # check if missile is out of bounds
            if new_missile_pos[0] < -self.margin or \
                    new_missile_pos[0] > self.battlefieldW + self.margin or \
                    new_missile_pos[1] < -self.margin or \
                    new_missile_pos[1] > self.battlefieldH + self.margin:
                missile_result = utils.MissileResult.RES_OUT_OF_BOUNDS
                break

            missile_trace.append(new_missile_pos)
            if len(missile_trace) >= self.maxSegments:
                missile_result = utils.MissileResult.RES_OUT_OF_SEGMENTS
                break
            
            missile_pos = new_missile_pos

        return missile_result, info, np.array(missile_trace)

    def scan_angle(self, angle_data, energy_data):
        for angle in np.arange(
                *angle_data):  #, desc='angle', colour='red', leave=False):
            res, info, trace = self.simulate_own_shot(angle, energy_data[0])
            if res == utils.MissileResult.RES_HIT_PLAYER and info != self.own_id:
                print(
                    f"=====> Can hit other player with angle={angle} and vel={energy_data[0]}"
                )
                break
            else:
                print(f"{res} {info} {len(trace)}")
        else:
            print("No angle found")

    def get_power_and_angle(self, event):
        mouse_x, mouse_y = event.pos
        offset_x = self.aimCircle.x + self.maxPower - mouse_x
        offset_y = self.aimCircle.y + self.maxPower - mouse_y
        self.power, self.angle = utils.cart2pol(offset_x, offset_y)
        self.power = min(self.power, self.maxPower)
        self.angle = math.degrees(self.angle)
        self.angle = (self.angle + 270) % 360

    def draw(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    # if self.aimCircle.collidepoint(event.pos):
                    self.dragging = True
                    self.get_power_and_angle(event)

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    self.dragging = False

            elif event.type == pygame.MOUSEMOTION:
                if self.dragging:
                    self.get_power_and_angle(event)
            
            elif event.type == pygame.KEYUP and event.key == K_SPACE:
                self.find_solution()

        self.surface.fill((0, 0, 0))

        for planet in self.planets:
            pygame.draw.lines(
                self.surface, (77, 77, 77), True,
                self.calc_surface_position(vertCircle * planet.radius +
                                           planet.position), 2)

        for player in self.players:
            pygame.draw.circle(self.surface, self.calc_player_color(player.id),
                               self.calc_surface_position(player.position),
                               self.playerSize)
            if player.id == self.own_id:
                pygame.draw.line(
                    self.surface, (255, 255, 255),
                    self.calc_surface_position(player.position),
                    self.calc_surface_position(player.position) +
                    utils.pol2cart(self.power, np.deg2rad(self.angle - 90)))
                self.aimCircle = pygame.draw.circle(
                    self.surface, (255, 255, 255),
                    self.calc_surface_position(player.position), self.maxPower,
                    1)

        # if (datetime.now() - self.lastTraceTime).microseconds > self.traceUpdateDelay:
        #     _, _, trace = self.simulate_own_shot(self.angle, self.power)
        #     self.lastTrace = self.calc_surface_position(trace)
        #     self.lastTraceTime = datetime.now()

        if (len(self.lastTrace) > 2):
            pygame.draw.lines(self.surface, (255, 0, 0), False, self.lastTrace)

        pygame.display.update()

    def calc_surface_position(self, pos):
        return pos * self.scaleFactor + self.globalOffset

    def reshape(self, w, h):
        ratioScreen = w / h
        ratioSim = self.battlefieldW / self.battlefieldH
        screenW = w
        screenH = h

        if ratioScreen > ratioSim:
            self.top = 0.0
            self.bottom = self.battlefieldH
            self.left = -(self.battlefieldH * ratioScreen -
                          self.battlefieldW) / 2.0
            self.right = self.battlefieldW + (self.battlefieldH * ratioScreen -
                                              self.battlefieldW) / 2.0
        else:
            self.top = -(self.battlefieldW / ratioScreen -
                         self.battlefieldH) / 2.0
            self.bottom = self.battlefieldH + (
                self.battlefieldW / ratioScreen - self.battlefieldH) / 2.0
            self.left = 0.0
            self.right = self.battlefieldW

        self.uiW = screenW if screenW > 1600 else screenW * 2 if screenW < 800 else 1600
        self.uiH = self.uiW * screenH / screenW

        self.scaleFactor = np.array([
            screenW / self.battlefieldW * 0.8,
            screenH / self.battlefieldH * 0.8
        ])
        self.globalOffset = np.array([self.uiW - screenW, self.uiH - screenH
                                      ]) / 2 * self.scaleFactor

    def calc_player_color(self, i):
        return utils.hsv2rgb(
            (360.0 / min(self.maxPlayers, 6) * i + (i / 6) * 30.0) / 360, 0.8,
            1.0)

    def find_solution(self):
        for player in self.players:
            if player.id != self.own_id:
                rel_position = player.position - self.position
                _, initialAngle = utils.cart2pol(rel_position[0], rel_position[1])
                initialAngle = (math.degrees(initialAngle) + 90) % 360
                self.angle = initialAngle
                print(initialAngle)

                # ret = optimize.least_squares(self.calc_distance, [initialAngle, 5], bounds=[[0, 0], [360, 20]], args=(player.position,))
                ret = optimize.minimize(self.calc_distance, [initialAngle, 5], bounds=optimize.Bounds([0, 0], [360, 20]), args=(player.position,))
                angle, power = ret.x
                print(ret)
                _, _, trace = self.simulate_own_shot(angle, power)
                self.lastTrace = self.calc_surface_position(trace)

                return angle, power

    def calc_distance(self, x, target):
        angle, energy = x
        _, _, missile_trace = self.simulate_own_shot(angle, energy)

        min_distance = cdist(missile_trace, [target]).min()

        if (min_distance < self.playerSize / 0.8):
            min_distance = 0

        return np.array([min_distance])

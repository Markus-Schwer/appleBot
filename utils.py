class Opponent:
    def __init__(self, x, y, id):
        self.x = x
        self.y = y
        self.id = id


class Curve:
    def __init__(self, n, curves):
        self.n = n
        self.curves = curves


class Planet:
    def __init__(self, x, y, radius, mass):
        self.x = x
        self.y = y
        self.mass = mass
        self.radius = radius


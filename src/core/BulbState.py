from enum import Enum

class BulbStateType(Enum):
    TEMPERATURE = 0
    RGB = 1

class BulbState:
    def __init__(self, type: BulbStateType, temperature, r, g, b, brightness):

        self.state_type: BulbStateType = type
        self.r = r
        self.g = g
        self.b = b
        self.temperature = temperature
        self.brightness = brightness
    
    def update_RGB(self,r, g, b):
        self.r = r
        self.g = g
        self.b = b
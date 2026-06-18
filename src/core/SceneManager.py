from .YeelightController import YeelightController

class SceneManager:
    def __init__(self, bulbs_config):
        self.bulbs = [YeelightController(b['ip'], b['name']) for b in bulbs_config]
        return

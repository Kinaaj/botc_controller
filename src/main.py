import yaml
from core.InputManager import InputManager
from core.SceneManager import SceneManager


async def main():
    with open("config.yaml", "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    # Seznam žárovek pro inicializaci controllerů
    bulbs_config = config['network']['yeelights']
    
    scene_manager = SceneManager(bulbs_config)
    input_manager = InputManager(scene_manager)
    
    await input_manager.start_listening()
    
    
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
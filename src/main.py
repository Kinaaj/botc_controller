import yaml
from core.InputManager import InputManager
from core.SceneManager import SceneManager
from core.AudioManager import AudioManager

async def main():
    with open("config.yaml", "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    # Seznam žárovek pro inicializaci controllerů
    bulbs_config = config['network']['yeelights']
    
    audio_manager = AudioManager("audio/bgm","audio/sfx")
    scene_manager = SceneManager(bulbs_config, audio_manager)
    input_manager = InputManager(scene_manager)
    
    await input_manager.start_listening()
    
    
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
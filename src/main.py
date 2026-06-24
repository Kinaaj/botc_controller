import os
from pathlib import Path

import yaml
from core.InputManager import InputManager
from core.SceneManager import SceneManager
from core.AudioManager import AudioManager

CODE_PATH = Path(__file__).parent.absolute()

async def main():
    with open("config.yaml", "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    # Seznam žárovek pro inicializaci controllerů
    bulbs_config = config['network']['yeelights']

    bgm_folder =  CODE_PATH / config['audio']['bgm_folder']
    sfx_folder =  CODE_PATH / config['audio']['sfx_folder']

    audio_manager = AudioManager(bgm_folder, sfx_folder)
    scene_manager = SceneManager(bulbs_config, audio_manager)
    input_manager = InputManager(scene_manager)
    
    await input_manager.start_listening()
    
    
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
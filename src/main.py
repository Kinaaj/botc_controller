import argparse
import os
from pathlib import Path

import yaml
from core.InputManager import InputManager
from core.SceneManager import SceneManager
from core.AudioManager import AudioManager
from core.GameState import GameState

CODE_PATH = Path(__file__).parent.absolute()


def build_arg_parser():
    parser = argparse.ArgumentParser(description="BotC Controller")
    parser.add_argument(
        "--keyboard-select",
        choices=["auto", "interactive"],
        default="auto",
        help="How to pick the keyboard device: 'auto' detects it automatically, "
             "'interactive' lists available devices and lets you choose by number (default: auto)",
    )
    return parser


async def main():
    args = build_arg_parser().parse_args()

    with open("config.yaml", "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    # Seznam žárovek pro inicializaci controllerů
    bulbs_config = config['network']['yeelights']

    bgm_folder = CODE_PATH / config['audio']['bgm_folder']
    sfx_folder = CODE_PATH / config['audio']['sfx_folder']

    # The evil-color palette is config, not state: it lives in config.yaml.
    # GameState only persists which index is currently selected, plus volume.
    evil_colors = [(c['r'], c['g'], c['b']) for c in config['bulbs']['evil_colors']]
    game_state = GameState(
        state_path=str(CODE_PATH / "state.json"),
        evil_colors=evil_colors,
        default_volume=config['audio'].get('volume', 0.5),
    )

    normal_color_cfg = config['bulbs']['normal_color']
    normal_color = (normal_color_cfg['r'], normal_color_cfg['g'], normal_color_cfg['b'])

    audio_manager = AudioManager(bgm_folder, sfx_folder, volume=game_state.volume)
    scene_manager = SceneManager(bulbs_config, audio_manager, game_state, normal_color)
    input_manager = InputManager(scene_manager, keyboard_select=args.keyboard_select)

    await input_manager.start_listening()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
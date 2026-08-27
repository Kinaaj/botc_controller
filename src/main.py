import argparse
import os
from pathlib import Path

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import yaml
from core.GameState import GameState
from core.AudioManager import AudioManager
from core.SceneManager import SceneManager
from core.InputManager import InputManager

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
    parser.add_argument(
        "--keymap",
        type=str,
        default=None,
        help="Path to keymap.json file (default: searches src/keymap.json)",
    )
    parser.add_argument(
        "--device-name",
        type=str,
        default=None,
        help="Filter keyboard device by name (e.g. 'Compx 2.4G Receiver')",
    )
    return parser


async def main():
    args = build_arg_parser().parse_args()

    with open("config.yaml", "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    # Seznam žárovek pro inicializaci controllerů
    bulbs_config = config['network']['yeelights']

    audio_folder = CODE_PATH / config['audio']['folder']

    normal_color_cfg = config['bulbs']['normal_color']
    normal_color = normal_color_cfg['kelvin']

    # The evil-color palette is config, not state: it lives in config.yaml.
    # GameState only persists which index is currently selected, plus volume.
    evil_colors = [(c['r'], c['g'], c['b']) for c in config['bulbs']['evil_colors']]
    game_state = GameState(
        state_path=str(CODE_PATH / "state.json"),
        evil_colors=evil_colors,
        default_volume=config['audio'].get('volume', 0.5),
        normal_temperature=normal_color
    )

    configured_device_name = (
        args.device_name
        or config.get('input', {}).get('device_name')
    )

    audio_manager = AudioManager(audio_folder, volume=game_state.volume)
    scene_manager = SceneManager(bulbs_config, audio_manager, game_state)
    input_manager = InputManager(
        scene_manager,
        keyboard_select=args.keyboard_select,
        keymap_path=args.keymap or str(CODE_PATH / "keymap.json"),
        device_name=configured_device_name,
    )

    # Report unreachable bulbs now, at boot, rather than failing silently the
    # first time a scene tries to use one. The app keeps running either way.
    await scene_manager.lights.connect_all()

    await input_manager.start_listening()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
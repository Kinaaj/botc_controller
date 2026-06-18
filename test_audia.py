import os
import pygame
import time


class AudioManager:

    def __init__(self):
        # Na Windows 'dummy' nepotřebujeme a mohl by dělat neplechu.
        # Na Raspberry Pi to pak zase odkomentujeme.
        os.environ["SDL_VIDEODRIVER"] = "dummy"

        try:
            pygame.mixer.init(44100, -16, 2, 2048)
            print("Audio mixer úspěšně spuštěn.")
        except pygame.error as e:
            print(f"Chyba při inicializaci zvuku: {e}")

    def play_sfx(self, filepath):
        try:
            sound = pygame.mixer.Sound(filepath)
            sound.play()
            print(f"Přehrávám: {filepath}")
        except Exception as e:
            print(f"Nepodařilo se načíst nebo přehrát soubor: {e}")


if __name__ == "__main__":
    audio_manager = AudioManager()

    # Spustíme zvuk
    audio_manager.play_sfx("dragon-studio-howling-wolves-515977.mp3")

    # POJISTKA: Držíme program spuštěný, dokud mixer hraje zvuky
    print("Čekám na dokončení zvuku...")
    while pygame.mixer.get_busy():
        time.sleep(0.1)  # Krátká pauza, ať nevytěžujeme procesor na 100%

    print("Program končí.")
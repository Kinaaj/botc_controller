import asyncio
import os
import random

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame

from .AudioPaths import BGM

# Definujeme si vlastní identifikátor události pro konec písničky
MUSIC_END_EVENT = pygame.USEREVENT + 1


class AudioManager:
    def __init__(self, audio_folder="audio/", volume=1.0):
        if not os.path.exists(audio_folder):
            raise ValueError(f"Folder not found: {audio_folder}")

        self.audio_folder = audio_folder

        # Stavy herní atmosféry
        self.is_night = False
        self.night_playlist = []  # Seznam skladeb pro aktuální fázi
        self.night_playlist_index = 0
        self.current_volume = volume

        if not pygame.display.get_init():
            os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
            pygame.display.init()

        # Inicializace zvukového modulu (pokud už nebyl inicializován)
        if not pygame.mixer.get_init():
            try:
                # Parametry: (frequency, size, channels, buffer)
                # Větší buffer (2048) pomáhá předcházet zasekávání zvuku na RPi
                pygame.mixer.init(44100, -16, 2, 2048)
            except pygame.error as e:
                print(f"[Audio] CHYBA při inicializaci zvuku: {e}")

        # Rezervace kanálů
        pygame.mixer.set_num_channels(8)
        self.sequence_channel = pygame.mixer.Channel(
            0
        )  # Kanál 0: Pro úvodní SFX sekvence (gong, atd.)
        self.ambient_channel = pygame.mixer.Channel(
            7
        )  # Kanál 7: Vyhrazeno pro hodinový šum (vítr, cvrčci)

        self.cached_sfx = {}
        self.cached_ambient = None

        self.active_sfx_channels = {}

        self.set_volume(self.current_volume)

        # Řekneme Pygame, aby při konci písničky na kanálu "music" vyvolal naši událost
        pygame.mixer.music.set_endevent(MUSIC_END_EVENT)

        # Spustíme asynchronní úkol, který neustále na pozadí hlídá konec písniček
        asyncio.create_task(self._playlist_watcher())

        self.audio_library = {}
        self._preload_library()
        self._preload_night_playlist()
        total_tracks = sum(len(files) for files in self.audio_library.values())
        print(f"[Audio] AudioManager připraven ({total_tracks} skladeb/efektů v {len(self.audio_library)} kategoriích, hlasitost: {int(self.current_volume*100)}%).")
    
    def _preload_library(self):
        """Projdede komplet celou složku audio a uloží si obsahy. BGM i SFX."""
        for root, dirs, files in os.walk(self.audio_folder):
            # OPRAVA: Převedeme název souboru na malá písmena pro kontrolu přípony
            audio_files = [f for f in files if f.lower().endswith(('.wav', '.mp3', '.ogg'))]
            if audio_files:
                rel_path = os.path.relpath(root, self.audio_folder).replace("\\", "/").lower()
                if rel_path == ".":
                    rel_path = ""
                self.audio_library[rel_path] = [os.path.join(root, f) for f in audio_files]
    
    def _preload_night_playlist(self):
        self.night_playlist = self._get_audio_files(BGM.Night)
        random.shuffle(self.night_playlist)

    def _get_path_from_class(self, category_class):
        """Převede zanořenou třídu (např. SFX.Day.Crowd) na text 'sfx/day/crowd'"""
        qualname = getattr(category_class, "__qualname__", "")
        return qualname.replace(".", "/").lower()

    def _get_audio_files(self, category_class, filename=None):
        """
        Nová hlavní univerzální funkce! 
        Pouze najde a vrátí seznam dostupných cest k souborům (Nic nenačítá do RAM!).
        """
        folder_path = self._get_path_from_class(category_class) if not isinstance(category_class, str) else category_class.lower()
        valid_files = []

        if filename:
            filepath = os.path.join(self.audio_folder, folder_path, filename)
            if os.path.exists(filepath):
                valid_files.append(filepath)
        else:
            # Kaskádové hledání
            search_prefix = folder_path
            for path_key, files in self.audio_library.items():
                if path_key == search_prefix or path_key.startswith(search_prefix + "/"):
                    valid_files.extend(files)

        return valid_files

    def play_tracked_sfx(self, category_class, filename=None, tag=None, volume=1.0, loops=0, fade_ms=0):
        """Zjednodušeno! Místo duplicitní logiky rovnou používá náš load_sfx."""
        sound = self.load_sfx(category_class, filename)
        if not sound:
            return None

        folder_path = self._get_path_from_class(category_class) if not isinstance(category_class, str) else category_class.lower()
        effect_tag = tag if tag else folder_path

        self.stop_tracked_sfx(effect_tag, fade_ms=0)

        free_channel = pygame.mixer.find_channel()
        if free_channel:
            # OPRAVA: Nastavujeme hlasitost kanálu, ne sdíleného Sound objektu!
            free_channel.set_volume(volume)
            free_channel.play(sound, loops=loops, fade_ms=fade_ms)
            self.active_sfx_channels[effect_tag] = free_channel
            print(f"[Audio] Spuštěn efekt {effect_tag}")
            return free_channel

        return None

    # --- LOGIKA PLAYLISTU (HUDBA NA POZADÍ) ---

    def _play_next_in_playlist(self):
        """Vybere náhodnou skladbu z aktuálního playlistu a spustí ji."""
        if not self.night_playlist:
            return

        next_track = self.night_playlist[self.night_playlist_index]
        print(f"[Audio] Přehrávám další skladbu: {os.path.basename(next_track)}")

        try:
            pygame.mixer.music.load(next_track)
            # loops=0 znamená přehrát jen jednou, po dohrání vyvolá MUSIC_END_EVENT
            pygame.mixer.music.play(loops=0, fade_ms=2000)
            self.night_playlist_index = (self.night_playlist_index+1)%len(self.night_playlist)
        except Exception as e:
            print(f"[Audio] Chyba při načítání skladby {next_track}: {e}")

    async def _playlist_watcher(self):
        """Smyčka běžící na pozadí aplikace, která hlídá konce skladeb."""
        while True:
            # Procházíme události z Pygame queue
            for event in pygame.event.get():
                if event.type == MUSIC_END_EVENT:
                    # Písnička skončila! Pustíme další z aktivního playlistu
                    if self.night_playlist:
                        self._play_next_in_playlist()

            # Pauza, abychom nevytěžovali procesor (stačí kontrolovat 2x za vteřinu)
            await asyncio.sleep(0.5)

    # --- PERMANENTNÍ AMBIENT (KANÁL 7) ---

    def play_permanent_ambient(self, category_class, filename=None, volume=1.0):
        """Spustí dlouhý ambientní podkres v nekonečné smyčce (nyní s podporou SFX tříd!)."""
        sound = self.load_sfx(category_class, filename)
        if not sound:
            return

        print(f"[Audio] Spouštím permanentní ambient z větve: {category_class.__name__ if hasattr(category_class, '__name__') else category_class}")
        self.cached_ambient = sound
        self.ambient_channel.set_volume(volume)
        self.ambient_channel.play(self.cached_ambient, loops=-1, fade_ms=3000)

    def stop_permanent_ambient(self, fade_ms=2000):
        """Plynule ztlumí a zastaví permanentní ambient."""
        if self.ambient_channel.get_busy():
            print("[Audio] Zastavuji permanentní ambient...")
            self.ambient_channel.fadeout(fade_ms)

# --- JEDNORÁZOVÉ ZVUKOVÉ EFEKTY (SFX) ---

    def load_sfx(self, category_class, filename=None):
        """Využije univerzální hledání. Vybere jeden soubor a NAČTE HO DO RAM."""
        valid_files = self._get_audio_files(category_class, filename)
        if not valid_files:
            print(f"[Audio] VAROVÁNÍ: Nenalezeny žádné SFX pro {category_class}")
            return None

        # Náhodný výběr JEDNOHO souboru
        filepath = random.choice(valid_files)

        # Cachování do RAM
        if filepath not in self.cached_sfx:
            self.cached_sfx[filepath] = pygame.mixer.Sound(filepath)
            
        return self.cached_sfx[filepath]

    def play_sfx(self, category_class, filename=None, volume=1.0):
        """Pustí krátký jednorázový zvuk (nyní s podporou SFX tříd!)."""
        sound = self.load_sfx(category_class, filename)
        if sound:
            free_channel = pygame.mixer.find_channel()
            if free_channel:
                # OPRAVA: Nastavujeme hlasitost kanálu
                free_channel.set_volume(volume)
                free_channel.play(sound)
            else:
                print("[Audio] VAROVÁNÍ: Nejsou volné zvukové kanály pro SFX!")



    def set_volume(self, level):
        """Sets master volume (0.0-1.0) for BGM and the two reserved channels."""
        self.current_volume = max(0.0, min(1.0, level))
        pygame.mixer.music.set_volume(self.current_volume)
        self.sequence_channel.set_volume(self.current_volume)
        self.ambient_channel.set_volume(self.current_volume)

    # --- HLAVNÍ ATMOSFÉRICKÉ SCÉNY ---

    async def start_night_sequence(self, intro_sfx_list, bgm_class):
        """
        Spustí úvodní efekty (intro_sfx_list) a poté zaktivuje noční playlist.
        intro_sfx_list: List s [SFX.Class, SFX.Class, ...]
        bgm_class: Třída reprezentující složku s hudbou (např. BGM.Night)
        """
        self.is_night = True

        # 1. Načtení playlistu pomocí kaskádového hledání
        self.night_playlist = self._get_audio_files(bgm_class)
        print(f"[Audio] Začíná Noc. Načteno {len(self.night_playlist)} skladeb.")

        # 2. Přehrání úvodních efektů (Sekvenčně)
        for sfx_class in intro_sfx_list:
            if not self.is_night:
                return  # Přerušení, pokud se mezitím změnila scéna

            # Použijeme tvou novou metodu, která vrací Sound objekt
            sound = self.load_sfx(sfx_class)
            
            if sound:
                self.sequence_channel.play(sound)
                # Čekáme, dokud zvuk dohraje
                while self.sequence_channel.get_busy():
                    await asyncio.sleep(0.1)
                    if not self.is_night:
                        self.sequence_channel.stop()
                        return

        # 3. Po dohrání intra spustíme playlist hudby
        if self.is_night and self.night_playlist:
            self._play_next_in_playlist()

    def stop_night_sequence(self, fade_ms=2000):
        """
        Bezpečně ukončí noční sekvenci, zastaví hudbu a vyčistí playlist.
        """
        print("[Audio] Ukončuji noční sekvenci...")
        self.is_night = False
        
        # 1. Zastaví sekvenční kanál (pokud by zrovna dohrávalo intro)
        self.sequence_channel.stop()
        
        # 2. Plynule ztlumí hudbu na pozadí
        pygame.mixer.music.fadeout(fade_ms)
        
        # 3. Vyprázdní playlist, aby watchery nezačaly hrát další skladbu
        self.night_playlist = []

    def stop_all(self):
        """Zastaví kompletne všetok zvuk (hudbu, SFX, ambienty) a vyčistí playlist."""
        self.is_night = False
        self.night_playlist = []
        
        # VYČISTENIE TRACKOVANÝCH EFEKTOV
        self.active_sfx_channels.clear()

        pygame.mixer.music.fadeout(1000)  # Stopne BGM (playlist)
        self.stop_permanent_ambient(1000)  # Stopne hodinovú slučku
        self.sequence_channel.stop()  # Stopne prípadné intrá
        pygame.mixer.stop()  # Zhodí všetky ostatné SFX kanály

        print("[Audio] Všetky zvuky boli kompletne zastavené a resetované.")


    def stop_tracked_sfx(self, tag, fade_ms=500, specific_channel=None, delay_ms=0):
        """
        Zastaví konkrétny efekt podľa jeho tagu, alebo zastaví konkrétny zadaný kanál.
        Ak je zadané delay_ms > 0, zastavenie sa odloží o daný počet milisekúnd.
        """

        if not isinstance(tag, str):
            tag = self._get_path_from_class(tag)

        # Pokud máme zpoždění, rovnou vyrobíme nezávislý odpočet na pozadí a skončíme
        if delay_ms > 0:
            async def _delayed_stop():
                await asyncio.sleep(delay_ms / 1000.0)
                # Po uplynutí času zavoláme tu samou funkci znovu, ale už s delay_ms=0
                self.stop_tracked_sfx(tag, fade_ms=fade_ms, specific_channel=specific_channel, delay_ms=0)
            
            asyncio.create_task(_delayed_stop())
            return True

        # --- Zbytek funkce zůstává úplně stejný jako předtím ---
        if specific_channel is not None:
            if specific_channel.get_busy():
                print(f"[Audio] Zastavujem špecifický dožívajúci kanál pre efekt: {tag}")
                specific_channel.fadeout(fade_ms)
            
            if self.active_sfx_channels.get(tag) == specific_channel:
                del self.active_sfx_channels[tag]
            return True

        if tag in self.active_sfx_channels:
            channel = self.active_sfx_channels[tag]
            if channel.get_busy():
                print(f"[Audio] Zastavujem efekt: {tag}")
                channel.fadeout(fade_ms)
            del self.active_sfx_channels[tag]
            return True

        return False
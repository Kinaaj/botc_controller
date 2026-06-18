import os
import pygame
import asyncio
import random

# Definujeme si vlastní identifikátor události pro konec písničky
MUSIC_END_EVENT = pygame.USEREVENT + 1

class AudioManager:
    def __init__(self, bgm_folder="audio/bgm/", sfx_folder="audio/sfx/"):
        self.bgm_folder = bgm_folder
        self.sfx_folder = sfx_folder
        
        # Stavy herní atmosféry
        self.is_night = False
        self.current_playlist = []  # Seznam skladeb pro aktuální fázi
        
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
        self.sequence_channel = pygame.mixer.Channel(0)  # Kanál 0: Pro úvodní SFX sekvence (gong, atd.)
        self.ambient_channel = pygame.mixer.Channel(7)   # Kanál 7: Vyhrazeno pro hodinový šum (vítr, cvrčci)

        self.cached_sfx = {}
        self.cached_ambient = None

        # Řekneme Pygame, aby při konci písničky na kanálu "music" vyvolal naši událost
        pygame.mixer.music.set_endevent(MUSIC_END_EVENT)
        
        # Spustíme asynchronní úkol, který neustále na pozadí hlídá konec písniček
        asyncio.create_task(self._playlist_watcher())
        print("[Audio] AudioManager úspěšně inicializován.")

    # --- POMOCNÉ METODY PRO CESTY A SOUBORY ---

    def _get_bgm_files(self, subfolder):
        """Vrátí seznam všech .mp3 souborů v dané podsložce (např. 'night' nebo 'day')."""
        path = os.path.join(self.bgm_folder, subfolder)
        if not os.path.exists(path):
            print(f"[Audio] VAROVÁNÍ: Složka {path} neexistuje!")
            return []
        return [os.path.join(path, f) for f in os.listdir(path) if f.endswith('.mp3')]

    def _get_sfx_path(self, category, filename):
        """Pomocná metoda pro sestavení cesty k SFX nebo ambientu."""
        return os.path.join(self.sfx_folder, category, filename)

    # --- LOGIKA PLAYLISTU (HUDBA NA POZADÍ) ---

    def _play_next_in_playlist(self):
        """Vybere náhodnou skladbu z aktuálního playlistu a spustí ji."""
        if not self.current_playlist:
            return

        next_track = random.choice(self.current_playlist)
        print(f"[Audio] Přehrávám další skladbu: {os.path.basename(next_track)}")
        
        try:
            pygame.mixer.music.load(next_track)
            # loops=0 znamená přehrát jen jednou, po dohrání vyvolá MUSIC_END_EVENT
            pygame.mixer.music.play(loops=0, fade_ms=2000)
        except Exception as e:
            print(f"[Audio] Chyba při načítání skladby {next_track}: {e}")

    async def _playlist_watcher(self):
        """Smyčka běžící na pozadí aplikace, která hlídá konce skladeb."""
        while True:
            # Procházíme události z Pygame queue
            for event in pygame.event.get():
                if event.type == MUSIC_END_EVENT:
                    # Písnička skončila! Pustíme další z aktivního playlistu
                    if self.current_playlist:
                        self._play_next_in_playlist()
            
            # Pauza, abychom nevytěžovali procesor (stačí kontrolovat 2x za vteřinu)
            await asyncio.sleep(0.5)

    # --- PERMANENTNÍ AMBIENT (KANÁL 7) ---

    def play_permanent_ambient(self, category, filename, volume=0.5):
        """Spustí dlouhý ambientní podkres (cvrčci, vítr) v nekonečné smyčce."""
        path = self._get_sfx_path(category, filename)
        if not os.path.exists(path):
            print(f"[Audio] Chyba: Ambientní soubor {path} neexistuje!")
            return

        print(f"[Audio] Spouštím permanentní ambient: {filename}")
        self.cached_ambient = pygame.mixer.Sound(path)
        self.ambient_channel.set_volume(volume)
        
        # loops=-1 (nekonečná smyčka), fadein_ms=3000 (náběh přes 3 vteřiny)
        self.ambient_channel.play(self.cached_ambient, loops=-1, fadein_ms=3000)

    def stop_permanent_ambient(self, fade_ms=2000):
        """Plynule ztlumí a zastaví permanentní ambient."""
        if self.ambient_channel.get_busy():
            print("[Audio] Zastavuji permanentní ambient...")
            self.ambient_channel.fadeout(fade_ms)

    # --- JEDNORÁZOVÉ ZVUKOVÉ EFEKTY (SFX) ---

    def load_sfx(self, category, filename):
        """Načte jednorázový zvuk do paměti a vrátí ho."""
        path = self._get_sfx_path(category, filename)
        key = f"{category}/{filename}"
        
        if key not in self.cached_sfx:
            if os.path.exists(path):
                self.cached_sfx[key] = pygame.mixer.Sound(path)
            else:
                print(f"[Audio] VAROVÁNÍ: SFX soubor {path} neexistuje!")
                return None
        return self.cached_sfx.get(key)
        
    def play_sfx(self, category, filename, volume=1.0):
        """Pustí zvuk přes volný kanál (blesk, výkřik, zaklepání)."""
        sound = self.load_sfx(category, filename)
        if sound:
            sound.set_volume(volume)
            # find_channel() vyhledá jakýkoliv volný kanál mimo těch hrajících
            free_channel = pygame.mixer.find_channel()
            if free_channel:
                free_channel.play(sound)
            else:
                print("[Audio] VAROVÁNÍ: Nejsou volné zvukové kanály pro SFX!")

    # --- HLAVNÍ ATMOSFÉRICKÉ SCÉNY ---

    async def start_night_sequence(self, intro_sfx_list, night_subfolder):
        """Spustí úvodní efekty za sebou a následně zaktivuje noční playlist."""
        self.is_night = True
        
        # Načteme složku s playlistem
        self.current_playlist = self._get_bgm_files(night_subfolder)
        print(f"[Audio] Začíná Noc. Načteno {len(self.current_playlist)} skladeb z '{night_subfolder}'.")

        # 1. Přehrání úvodních efektů ze seznamu
        for sfx_info in intro_sfx_list:
            if not self.is_night:
                return  # Pokud někdo během intra hru zastaví, přerušíme to
                
            category, filename = sfx_info
            sound = self.load_sfx(category, filename)
            
            if sound:
                self.sequence_channel.play(sound)
                # Čekáme, dokud zvuk dohraje
                while self.sequence_channel.get_busy():
                    await asyncio.sleep(0.1)
                    if not self.is_night:
                        self.sequence_channel.stop()
                        return

        # 2. Po dohrání intra spustíme playlist hudby
        if self.is_night and self.current_playlist:
            self._play_next_in_playlist()

    def start_day(self, day_subfolder):
        """Okamžitě přepne playlist na denní a stopne noční sekvence."""
        self.is_night = False
        self.sequence_channel.stop()
        
        # Načteme denní playlist a spustíme první track
        self.current_playlist = self._get_bgm_files(day_subfolder)
        print(f"[Audio] Začíná Den. Načteno {len(self.current_playlist)} skladeb z '{day_subfolder}'.")
        
        if self.current_playlist:
            self._play_next_in_playlist()

    def stop_all(self):
        """Zastaví kompletně všechen zvuk (hudbu, SFX, ambienty) a vyčistí playlist."""
        self.is_night = False
        self.current_playlist = []
        
        pygame.mixer.music.fadeout(1000)      # Stopne BGM (playlist)
        self.stop_permanent_ambient(1000)     # Stopne hodinovou smyčku
        self.sequence_channel.stop()          # Stopne případná intra
        pygame.mixer.stop()                   # Shodí všechny ostatní SFX kanály
        
        print("[Audio] Všechny zvuky byly kompletně zastaveny a resetovány.")
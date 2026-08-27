import os
import yt_dlp

# --- KONFIGURACE ---
PLAYLIST_URL = "https://youtube.com/playlist?list=PLPSQMFwZylXE&si=HFf05_P5RNKrqlvk"  # Odkaz na YouTube playlist
OUTPUT_DIR = "./downloads_mp3"                  # Složka pro normalizované MP3
OUTPUT_DIR_ORIGINAL = "./downloads_mp3_original"  # Složka pro originální MP3 (bez normalizace)
TARGET_LUFS = -32.0                             # Cílová hlasitost (-16 LUFS je standard pro web/podcasting)
TRUE_PEAK = -2                                # Ochranný strop proti přebuzení (dB)

def _base_ydl_opts(output_folder: str, archive_file: str) -> dict:
    """Společné nastavení pro oba průchody."""
    return {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(output_folder, '%(title)s.%(ext)s'),
        'ignoreerrors': True,
        'nooverwrites': True,
        'download_archive': archive_file,
        'postprocessors': [
            {
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '0',  # Nejvyšší VBR kvalita
            }
        ],
    }

def download_original(playlist_url: str, output_folder: str):
    """Stáhne MP3 bez jakékoliv normalizace – originál pro porovnání."""
    os.makedirs(output_folder, exist_ok=True)
    ydl_opts = _base_ydl_opts(output_folder, 'archive_original.txt')

    print(f"\n📥 [1/2] Stahuji ORIGINÁLNÍ (nenormalizované) MP3 do: {output_folder}")
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([playlist_url])
    print(f"✅ Originály uloženy do: {output_folder}")

def download_and_normalize(playlist_url: str, output_folder: str):
    """Stáhne MP3 a aplikuje EBU R128 loudnorm normalizaci."""
    os.makedirs(output_folder, exist_ok=True)
    loudnorm_filter = f"loudnorm=I={TARGET_LUFS}:TP={TRUE_PEAK}:LRA=11"

    ydl_opts = _base_ydl_opts(output_folder, 'archive_normalized.txt')
    # Normalizační filtr pouze pro krok extrakce audia
    ydl_opts['postprocessor_args'] = {
        'ffmpegextractaudio': ['-af', loudnorm_filter]
    }

    print(f"\n🎚️  [2/2] Stahuji a normalizuji MP3 do: {output_folder}")
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([playlist_url])
    print(f"✅ Normalizované skladby uloženy do: {output_folder}")

if __name__ == "__main__":
    if "SEM_VLOZ_URL_PLAYLISTU" in PLAYLIST_URL:
        print("⚠️  Před spuštěním nezapomeň v proměnné PLAYLIST_URL nastavit URL playlistu.")
    else:
        download_original(PLAYLIST_URL, OUTPUT_DIR_ORIGINAL)
        download_and_normalize(PLAYLIST_URL, OUTPUT_DIR)
        print("\n🎉 Hotovo! Porovnej soubory ve složkách:")
        print(f"   Originál:      {OUTPUT_DIR_ORIGINAL}")
        print(f"   Normalizováno: {OUTPUT_DIR}")

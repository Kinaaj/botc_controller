# Atmosférický ovladač pro hru Blood on the Clocktower

Tento dokument shrnuje účel a technické fungování systému pro synchronizaci chytrých světel a zvuku, běžícího na Raspberry Pi.

## Cíl projektu

Hlavním cílem je maximalizovat herní zážitek a atmosféru při hraní sociální dedukční hry **Blood on the Clocktower**. Projekt umožňuje vypravěči (Storyteller) pomocí stisku jediného tlačítka na vyhrazené klávesnici plynule měnit nasvícení místnosti a spouštět synchronizovaný zvukový doprovod. Celé to běží na headless (bezmonitorovém) Raspberry Pi, takže vypravěč nepotřebuje sledovat žádnou obrazovku a může se plně věnovat hře a hráčům.

## Jak to pod kapotou funguje

Aplikace je napsaná v Pythonu a stojí na **asynchronní, událostmi řízené architektuře** (`asyncio`). Systém neustále nenaslouchá v blokující smyčce, ale běží paralelně – světla mohou komunikovat po síti, hudba hraje a systém je přitom okamžitě připraven reagovat na další stisk klávesy bez jakéhokoliv záseku.

Systém je rozdělen do čtyř hlavních logických bloků:

* **InputManager (Zpracování vstupu):** Využívá linuxovou knihovnu `evdev`, která čte surová data (raw events) z hardwarové vrstvy připojené klávesnice v linuxovém jádře (`/dev/input/`). Díky tomu program nepotřebuje grafické rozhraní a reaguje i na ořezaném Raspberry Pi OS Lite spuštěném na pozadí.
* **AudioManager (Zpracování zvuku):** Obaluje knihovnu `pygame.mixer`, která komunikuje přímo se zvukovým serverem (přes ALSA). Má vyhrazený kanál pro nekonečný ambient (cvrčci, vítr), kanál pro automaticky rotující playlisty hudby na pozadí (noční/denní melodie) a volné kanály pro okamžité, překrývající se zvukové efekty (výkřiky, hrom).
* **YeelightController (Ovládání světel):** Udržuje trvalé TCP spojení se žárovkami Yeelight na lokální LAN síti. Požadavky posílá jako surové JSON řetězce podle oficiálního protokolu. Umí plynule měnit RGB barvy, jas nebo spouštět složité efekty typu color flow (např. stroboskopický blesk).
* **SceneManager (Mozek aplikace):** Funguje jako hlavní orchestrátor. Při zachycení stisku konkrétní klávesy asynchronně rozešle příkazy. Ve stejný okamžik dá pokyn všem žárovkám ke změně barvy a `AudioManageru` ke spuštění zvuku. Konkrétní herní scény (Noc, Den, Poprava, Blesk) jsou logicky odděleny právě zde.

## Běhové prostředí a konfigurace

* **Hardware:** Raspberry Pi 4 s dedikovanou USB/bezdrátovou klávesnicí a audio výstupem.
* **Operační systém:** Raspberry Pi OS Lite (bez grafického prostředí).
* **Konfigurace:** Projekt využívá soubor `config.yaml`, ze kterého si při startu načte lokální IP adresy a jména jednotlivých Yeelight žárovek, aby síťová konfigurace nebyla natvrdo zapsaná v kódu a dala se snadno upravit před každou hrou.

---

Mám ten text ještě nějak obohatit o podrobný návod k instalaci závislostí a postupu pro spuštění, abys to mohl rovnou vzít a vložit na GitHub jako `README.md`?
import asyncio
import json

class YeelightController:
    def __init__(self, ip, name, port=55443):
        self.ip = ip
        self.name = name
        self.port = port
        self.reader = None
        self.writer = None
        self.cmd_id = 0

    async def connect(self):
        """Naváže trvalé TCP spojení se žárovkou."""
        if self.writer is None:
            try:
                # Asynchronní otevření TCP spojení
                self.reader, self.writer = await asyncio.open_connection(self.ip, self.port)
                print(f"[{self.name}] Úspěšně připojeno k {self.ip}")
            except Exception as e:
                print(f"[{self.name}] Chyba připojení k {self.ip}: {e}")

    async def send_command(self, method, params):
        """Univerzální metoda pro odeslání JSON příkazu přes TCP tunnel."""
        await self.connect() # Pojistka, pokud by spojení vypadlo
        if not self.writer:
            return

        self.cmd_id += 1
        payload = {
            "id": self.cmd_id,
            "method": method,
            "params": params
        }
        
        # Převedeme na JSON a přidáme povinné \r\n
        message = json.dumps(payload) + "\r\n"
        
        try:
            self.writer.write(message.encode())
            await self.writer.drain() # Počkáme na fyzické odeslání dat do sítě
        except Exception as e:
            print(f"[{self.name}] Selhalo odeslání příkazu: {e}")
            self.writer = None # Resetujeme spojení pro příští pokus

    # --- KONKRÉTNÍ FUNKCE PRO ATMOSFÉRU ---

    async def turn_on(self):
        # Parametry: ["on", "smooth", trvání v ms]
        await self.send_command("set_power", ["on", "smooth", 500])

    async def turn_off(self):
        await self.send_command("set_power", ["off", "smooth", 500])

    async def set_brightness(self, level):
        # level: 1 až 100
        await self.send_command("set_bright", [level, "smooth", 500])

    async def set_rgb(self, r, g, b, duration=500):
        """Nastaví barvu žárovky pomocí RGB hodnot."""
        # Yeelight vyžaduje barvu jako jedno číslo: (R * 65536) + (G * 256) + B
        rgb_value = (r << 16) + (g << 8) + b
        await self.send_command("set_rgb", [rgb_value, "smooth", duration])
    
    async def flash_lightning(self):
        """
        Vytvoří efekt dvojitého blesku pomocí color flow.
        Po skončení se světlo automaticky vrátí do původního stavu.
        """
        # count = 3, action = 0 (recover), flow_expression
        params = [3, 0, "50,2,6500,100,100,7,0,0,50,2,6500,100"]
        await self.send_command("start_cf", params)

    async def close(self):
        """Uvítáme při ukončení programu."""
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
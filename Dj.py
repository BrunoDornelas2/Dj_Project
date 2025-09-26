import pygame
import threading
import time
import os
import numpy as np

pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

class Instrument(threading.Thread):
    def __init__(self, name, file_path, global_start_time, channel_id):
        super().__init__(daemon=True)
        self.name = name
        self.file_path = file_path
        self.global_start_time = global_start_time

        self.channel = pygame.mixer.Channel(channel_id)
        self.sound = pygame.mixer.Sound(file_path)

        # Carrega array de samples para manipulação
        self.sound_array = pygame.sndarray.array(self.sound)
        self.sample_rate = pygame.mixer.get_init()[0]
        self.total_samples = self.sound_array.shape[0]

        self._lock = threading.Lock()
        self._pause_cond = threading.Condition(self._lock)
        self._paused = False
        self._running = True
        self._stop_event = threading.Event()

    def run(self):
        while not self._stop_event.is_set():
            with self._pause_cond:
                while self._paused and not self._stop_event.is_set():
                    self._pause_cond.wait()

            if self._stop_event.is_set():
                break

            elapsed = time.time() - self.global_start_time
            start_sample = int(elapsed * self.sample_rate) % self.total_samples

            segment = np.concatenate((
                self.sound_array[start_sample:],
                self.sound_array[:start_sample]
            ))

            sound_to_play = pygame.sndarray.make_sound(segment.copy())
            self.channel.stop()
            self.channel.play(sound_to_play)

            # Espera com timeout, mas pode ser interrompido pelo stop
            self._stop_event.wait(self.total_samples / self.sample_rate / 4)

    def pause(self):
        with self._pause_cond:
            self._paused = True
            self.channel.pause()

    def resume(self):
        with self._pause_cond:
            self._paused = False
            self._pause_cond.notify()

    def stop(self):
        self._stop_event.set()
        with self._pause_cond:
            self._paused = False
            self._pause_cond.notify_all()
        self.channel.stop()

    def is_playing(self):
        return self.channel.get_busy() and not self._paused

class DJDesk:
    def __init__(self):
        self.instruments = {}
        self.global_start_time = time.time()
        self.max_channels = pygame.mixer.get_num_channels()

    def add_instrument(self, name, file_path):
        if name in self.instruments:
            print(f"Instrumento '{name}' já existe.")
            return
        channel_id = len(self.instruments)
        if channel_id >= self.max_channels:
            print("Sem canais disponíveis.")
            return
        inst = Instrument(name, file_path, self.global_start_time, channel_id)
        inst.start()
        self.instruments[name] = inst
        print(f"Instrumento '{name}' adicionado.")

    def pause_instrument(self, name):
        inst = self.instruments.get(name)
        if inst:
            inst.pause()
            print(f"Instrumento '{name}' pausado.")

    def resume_instrument(self, name):
        inst = self.instruments.get(name)
        if inst:
            inst.resume()
            print(f"Instrumento '{name}' retomado.")

    def stop_all(self):
        for inst in self.instruments.values():
            inst.stop()
            inst.join(timeout=1.0)
        self.instruments.clear()
        pygame.mixer.quit()
        print("Todos os instrumentos foram parados.")

    def show_status(self):
        if not self.instruments:
            print("(Sem instrumentos)")
        else:
            for name, inst in self.instruments.items():
                estado = "Tocando" if inst.is_playing() else "Pausado"
                print(f"{name}: {estado}")

def main():
    dj = DJDesk()

    stems_dir = os.path.join("Musicas", "stems1")
    stems = {
        "baixo": "Bass.ogg",
        "bateria": "Drums.ogg",
        "guitarra": "Guitar.ogg",
        "voz": "Vocals.ogg",
    }

    for name, file in stems.items():
        try:
            dj.add_instrument(name, os.path.join(stems_dir, file))
        except Exception as e:
            print(f"Erro ao carregar {file}: {e}")

    print("\nComandos: pause <nome> | resume <nome> | status | quit\n")

    try:
        while True:
            cmd_line = input("> ").strip().split()
            if not cmd_line:
                continue
            cmd = cmd_line[0].lower()
            if cmd == "pause" and len(cmd_line) >= 2:
                dj.pause_instrument(cmd_line[1])
            elif cmd == "resume" and len(cmd_line) >= 2:
                dj.resume_instrument(cmd_line[1])
            elif cmd == "status":
                dj.show_status()
            elif cmd == "quit":
                break
            else:
                print("Comando inválido.")
    finally:
        dj.stop_all()
        pygame.quit()

if __name__ == "__main__":
    main()

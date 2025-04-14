import logging
import time
import threading
import queue
import atexit
import os
import subprocess
from sshkeyboard import listen_keyboard

LOG_FILE = "/tmp/gagasampler.log"

# Restaura o echo do terminal ao sair
atexit.register(lambda: os.system('stty echo'))

# Fila para capturar teclas
key_queue = queue.Queue()

def on_press(key):
    key_queue.put(key)

def start_keyboard_listener():
    listener_thread = threading.Thread(
        target=lambda: listen_keyboard(on_press=on_press),
        daemon=True
    )
    listener_thread.start()

def get_key(timeout=0.1):
    try:
        return key_queue.get(timeout=timeout)
    except queue.Empty:
        return None

def setup_logging():
    # Limpa o log anterior ao iniciar nova jogada
    with open(LOG_FILE, "w") as f:
        f.write("=== NOVA JOGADA INICIADA ===\n")
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler()
        ]
    )

def play_sound(sound_file):
    full_path = f"samples/{sound_file}"
    try:
        logging.info(f"Tocando som: {sound_file}")
        subprocess.run(['aplay', full_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        logging.info(f"Som finalizado: {sound_file}")
    except Exception as e:
        logging.error(f"Erro ao tocar {sound_file}: {e}")

def play_sequence(user_sequence):
    logging.info("Iniciando sequência de sons (fXX.wav)...")
    for key in user_sequence:
        sound_file = f"f{int(key):02d}.wav"
        logging.info(f"Tocando {sound_file}...")
        threading.Thread(target=play_sound, args=(sound_file,), daemon=True).start()
        time.sleep(0.5)

def play_game():
    user_sequence = []
    click_count = 0
    sequence_history = []

    print("Aguardando a tecla '0' para iniciar...")

    start_keyboard_listener()

    # Aguarda tecla de início
    while True:
        key = get_key()
        if key is not None and key == '0':
            setup_logging()
            logging.info("Tecla START ('0') pressionada")
            threading.Thread(target=play_sound, args=("start.wav",), daemon=True).start()
            break
        time.sleep(0.1)

    start_time = time.time()

    def handle_result():
        sequence_str = ",".join(map(str, user_sequence))
        logging.info(f"Sequência registrada: {sequence_str}")
        if sequence_str in sequence_history:
            logging.warning(f"Sequência repetida detectada: {sequence_str}")
        else:
            sequence_history.append(sequence_str)
            logging.info(f"Nova sequência salva: {sequence_str}")
        logging.info("=== FIM DA JOGADA ===")

    play_threads = []

    while click_count < 6:
        key = get_key()
        if key is not None and key in [str(i) for i in range(1, 10)]:
            timestamp = time.time() - start_time
            logging.info(f"Tecla '{key}' detectada aos {timestamp:.2f} segundos")
            sound_file = f"{int(key):02d}.wav"
            thread = threading.Thread(target=play_sound, args=(sound_file,))
            thread.start()
            play_threads.append(thread)
            user_sequence.append(key)
            click_count += 1
            time.sleep(0.5)

            if click_count == 6:
                logging.info("Aguardando o fim dos sons da jogada...")
                for t in play_threads:
                    t.join()
                handle_result()
                play_sequence(user_sequence)
                break

        time.sleep(0.1)

if __name__ == "__main__":
    try:
        play_game()
    except KeyboardInterrupt:
        logging.info("Jogo encerrado manualmente")

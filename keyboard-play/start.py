import logging
import time
import threading
import queue
import atexit
import os
import subprocess
import random
from sshkeyboard import listen_keyboard

LOG_FILE = "/tmp/gagasampler.log"
DB_FILE = "/tmp/gagasampler.db"

key_queue = queue.Queue()

# Restaura o echo do terminal ao sair
atexit.register(lambda: os.system('stty echo'))

def on_press(key):
    key_queue.put(key)

def start_keyboard_listener():
    threading.Thread(
        target=lambda: listen_keyboard(on_press=on_press),
        daemon=True
    ).start()

def get_key(timeout=0.1):
    try:
        return key_queue.get(timeout=timeout)
    except queue.Empty:
        return None

def setup_logging():
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

def read_sequence_history():
    if not os.path.exists(DB_FILE):
        return set()
    with open(DB_FILE, "r") as f:
        return set(line.strip() for line in f.readlines())

def append_sequence(seq_str):
    with open(DB_FILE, "a") as f:
        f.write(seq_str + "\n")

def get_random_win_offset():
    return random.choice([3, 4, 5, 6])

def play_game():
    user_sequence = []
    click_count = 0

    print("Aguardando a tecla '0' para iniciar...")
    start_keyboard_listener()

    while True:
        key = get_key()
        if key == '0':
            setup_logging()
            logging.info("Tecla START ('0') pressionada")
            threading.Thread(target=play_sound, args=("start.wav",), daemon=True).start()
            break
        time.sleep(0.1)

    # Lê histórico
    sequence_history = read_sequence_history()
    total_attempts = len(sequence_history)
    winning_attempt = total_attempts + get_random_win_offset()
    logging.info(f"Tentativa sorteada para vitória: {winning_attempt}")

    start_time = time.time()
    play_threads = []

    while click_count < 6:
        key = get_key()
        if key and key in [str(i) for i in range(1, 10)]:
            timestamp = time.time() - start_time
            logging.info(f"Tecla '{key}' detectada aos {timestamp:.2f} segundos")
            thread = threading.Thread(target=play_sound, args=(f"{int(key):02d}.wav",))
            thread.start()
            play_threads.append(thread)
            user_sequence.append(key)
            click_count += 1
            time.sleep(0.5)

            if click_count == 6:
                logging.info("Aguardando o fim dos sons da jogada...")
                for t in play_threads:
                    t.join()

                # Processa a jogada
                seq_str = ",".join(map(str, user_sequence))
                logging.info(f"Sequência registrada: {seq_str}")

                # Toca a sequência final (fXX.wav)
                play_sequence(user_sequence)

                is_unique = seq_str not in sequence_history
                logging.info("Verificando unicidade da sequência...")

                if not is_unique:
                    logging.warning("Sequência repetida detectada!")
                    play_sound("obrigado.wav")
                    logging.info("=== FIM DA JOGADA ===")
                    break

                # Sequência inédita: salvar e verificar se é premiada
                append_sequence(seq_str)
                total_attempts += 1

                if total_attempts == winning_attempt:
                    logging.info("🎉 VENCEDOR DETECTADO!")
                    play_sound("win.wav")
                else:
                    logging.info("Não foi premiado nesta tentativa.")
                    play_sound("obrigado.wav")

                logging.info("=== FIM DA JOGADA ===")
                break

        time.sleep(0.1)

if __name__ == "__main__":
    try:
        play_game()
    except KeyboardInterrupt:
        logging.info("Jogo encerrado manualmente")

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
        f.write("=== SISTEMA INICIADO ===\n")
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler()
        ]
    )

def reset_log_for_jogada(jogada_num):
    with open(LOG_FILE, "w") as f:
        f.write(f"=== NOVA JOGADA #{jogada_num} INICIADA ===\n")

def play_sound(sound_file):
    full_path = f"samples/{sound_file}"
    try:
        logging.info(f"{sound_file}")
        subprocess.run(['aplay', full_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
      #  logging.info(f"Som finalizado: {sound_file}")
    except Exception as e:
        logging.error(f"Erro ao tocar {sound_file}: {e}")

def play_sequence(user_sequence):
    logging.info("Iniciando sequência de sons (fXX.wav)...")
    for key in user_sequence:
        sound_file = f"f{int(key):02d}.wav"
        logging.info(f"{sound_file}...")
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

def wait_for_start_key():
    print("Aguardando a tecla '0' para iniciar jogada...")
    while True:
        key = get_key()
        if key == '0':
            logging.info("Tecla START ('0') pressionada")
            threading.Thread(target=play_sound, args=("start.wav",), daemon=True).start()
            return
        time.sleep(0.1)

def play_game():
    start_keyboard_listener()
    setup_logging()

    jogada_atual = 0
    winning_offset = get_random_win_offset()
    winning_jogada = jogada_atual + winning_offset

    logging.info(f"Sorteio inicial: Jogada vencedora será a tentativa #{winning_jogada}")

    while True:
        jogada_atual += 1
        reset_log_for_jogada(jogada_atual)

        user_sequence = []
        click_count = 0
        wait_for_start_key()

        start_time = time.time()
        sequence_history = read_sequence_history()

        logging.info(f"Jogada atual: {jogada_atual}")
        logging.info(f"Jogada premiada atual: {winning_jogada}")

        play_threads = []

        while click_count < 6:
            key = get_key()
            if key and key in [str(i) for i in range(1, 10)]:
                timestamp = time.time() - start_time
                posicao = f"{click_count + 1:02d}"
                logging.info(f"Posição: [{posicao}]")
                thread = threading.Thread(target=play_sound, args=(f"{int(key):02d}.wav",))
                thread.start()
                play_threads.append(thread)
                user_sequence.append(key)
                click_count += 1
                time.sleep(0.5)

        logging.info("Aguardando o fim dos sons da jogada...")
        for t in play_threads:
            t.join()

        seq_str = ",".join(map(str, user_sequence))
        logging.info(f"Sequência registrada: {seq_str}")
        play_sequence(user_sequence)

        is_unique = seq_str not in sequence_history
        if not is_unique:
            logging.warning("Sequência repetida detectada.")
            play_sound("obrigado.wav")
            logging.info("=== FIM DA JOGADA ===")
            continue

        append_sequence(seq_str)

        if jogada_atual == winning_jogada:
            logging.info("🎉 JOGADA PREMIADA! Jogador venceu.")
            play_sound("win.wav")
            # SORTEIA próxima jogada premiada
            winning_offset = get_random_win_offset()
            winning_jogada = jogada_atual + winning_offset
            logging.info(f"Próxima jogada sorteada para vitória: {winning_jogada}")
        else:
            logging.info("Jogada não premiada.")
            play_sound("obrigado.wav")

        logging.info("=== FIM DA JOGADA ===")
        time.sleep(1)

if __name__ == "__main__":
    try:
        play_game()
    except KeyboardInterrupt:
        logging.info("Jogo encerrado manualmente")

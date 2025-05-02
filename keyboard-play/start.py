#!/usr/bin/env python3
import logging
import time
import threading
import queue
import atexit
import os
import subprocess
import random
from sshkeyboard import listen_keyboard

# Configurações editáveis
WIN_OFFSETS = [3, 4, 5, 6]

# Arquivos de log e histórico
LOG_FILE = "/tmp/gagasampler.log"
DB_FILE = "/tmp/gagasampler.db"

# Mapeamento de teclas
BTN_KEYS = {
    "1": 1,
    "2": 2,
    "3": 3,
    "4": 4,
    "5": 5,
    "6": 6,
    "7": 7,
    "8": 8,
    "9": 9,
}
START_KEY = "0"
VALID_KEYS = list(BTN_KEYS.keys())
ALL_KEYS = VALID_KEYS + [START_KEY]

# Fila de teclas pressionadas
key_queue = queue.Queue()

# Garante echo do terminal ao sair
atexit.register(lambda: os.system('stty echo'))

# Configuração do logging
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

def log(value):
    logging.info(value)
    print(value)

def play_sound(sound_file):
    full_path = f"samples/{sound_file}"
    try:
        log(f"Tocando: {sound_file}")
        subprocess.run(['aplay', full_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        error = f"Erro ao tocar {sound_file}: {e}"
        print(error)
        logging.error(error)

def reset_log_for_jogada(jogada_num):
    with open(LOG_FILE, "w") as f:
        f.write(f"=== NOVA JOGADA #{jogada_num} INICIADA ===\n")

def read_sequence_history():
    if not os.path.exists(DB_FILE):
        return set()
    with open(DB_FILE, "r") as f:
        return set(line.strip() for line in f)

def append_sequence(seq_str):
    with open(DB_FILE, "a") as f:
        f.write(seq_str + "\n")

def get_random_win_offset():
    return random.choice(WIN_OFFSETS)

# Handler do teclado
def press_handler(key):
    if key in ALL_KEYS:
        key_queue.put(key)

def wait_for_start_key():
    print("Aguardando a tecla start para iniciar jogada...")
    while True:
        key = key_queue.get()
        if key == START_KEY:
            log("Tecla START pressionada")
            threading.Thread(target=play_sound, args=("card.wav",), daemon=True).start()
            return True
        time.sleep(0.1)

# Variáveis de controle de jogo
jogada_atual = 0
winning_offset = 0
winning_jogada = 0

def reset_game():
    global jogada_atual, winning_offset, winning_jogada
    setup_logging()
    jogada_atual = 0
    winning_offset = get_random_win_offset()
    winning_jogada = jogada_atual + winning_offset
    log(f"Sorteio inicial: Jogada vencedora será a tentativa #{winning_jogada}")

def play_game():
    global jogada_atual, winning_offset, winning_jogada
    reset_game()
    pending_win = False

    while True:
        jogada_atual += 1
        reset_log_for_jogada(jogada_atual)

        if not wait_for_start_key():
            continue

        sequence_history = read_sequence_history()
        log(f"Jogada atual: {jogada_atual}")
        log(f"Jogada premiada atual: {winning_jogada}")

        # Captura da sequência
        user_sequence = []
        click_count = 0
        play_threads = []
        while click_count < 6:
            key = key_queue.get()
            if key in VALID_KEYS:
                position = BTN_KEYS[key]
                t = threading.Thread(target=play_sound, args=(f"{position:02d}.wav",), daemon=True)
                t.start()
                play_threads.append(t)
                user_sequence.append(position)
                click_count += 1
                log(f"Posição: [{click_count:02d}]")
                time.sleep(0.5)

        # Espera todos os sons da jogada
        log("Aguardando o fim dos sons da jogada...")
        for t in play_threads:
            t.join()

        # Registro da sequência
        seq_str = ",".join(map(str, user_sequence))
        log(f"Sequência registrada: {seq_str}")

        is_unique = seq_str not in sequence_history

        # Lógica de repetição e premiação
        if not is_unique:
            logging.warning("Sequência repetida detectada.")
            print("Sequência repetida detectada.")
            if jogada_atual == winning_jogada or pending_win:
                pending_win = True
                log(" Sequência repetida na jogada premiada → próxima original SERÁ premiada")
            else:
                log(" Sequência repetida em jogada normal → sem efeito no sorteio")
            play_sound("obrigado.wav")
            log("=== FIM DA JOGADA ===")
            continue

        append_sequence(seq_str)

        if pending_win:
            log("🎉 JOGADA PREMIADA (devido a repetição anterior)! Jogador venceu.")
            play_sound("win.wav")
            pending_win = False
            winning_offset = get_random_win_offset()
            winning_jogada = jogada_atual + winning_offset
            log(f"Próxima jogada sorteada para vitória: {winning_jogada}")
        elif jogada_atual == winning_jogada:
            log("🎉 JOGADA PREMIADA! Jogador venceu.")
            play_sound("win.wav")
            winning_offset = get_random_win_offset()
            winning_jogada = jogada_atual + winning_offset
            log(f"Próxima jogada sorteada para vitória: {winning_jogada}")
        else:
            log("Jogada não premiada.")
            play_sound("obrigado.wav")

        log("=== FIM DA JOGADA ===")
        time.sleep(1)

if __name__ == "__main__":
    try:
        threading.Thread(target=listen_keyboard, kwargs={"on_press": press_handler, "delay_second_char": 0.1}, daemon=True).start()
        play_sound("on.wav")
        play_game()
    except KeyboardInterrupt:
        log("Jogo encerrado manualmente")


import logging
import time
import threading
import queue
import atexit
import os
import subprocess
import random
import RPi.GPIO as GPIO

LOG_FILE = "/tmp/gagasampler.log"
DB_FILE = "/tmp/gagasampler.db"

btn_1 = 7
btn_2 = 11
btn_3 = 12
btn_4 = 13
btn_5 = 15
btn_6 = 29
btn_7 = 31
btn_8 = 33
btn_9 = 35
btn_reset = 38
btn_start = 37
list_btns = [btn_1, btn_2, btn_3, btn_4, btn_5, btn_6, btn_7, btn_8, btn_9, btn_reset, btn_start]
sensor = 40

key_queue = queue.Queue()

atexit.register(lambda: os.system('stty echo'))

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

setup_logging()
log("Iniciando GPIO")

GPIO.setmode(GPIO.BOARD)
for btn in list_btns:
    GPIO.setup(btn, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(sensor, GPIO.IN)

# O restante do código original deve seguir daqui em diante, mantendo o uso de log()

 # Sensor de proximidade

key_queue = queue.Queue()

# Restaura o echo do terminal ao sair
atexit.register(lambda: os.system('stty echo'))

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
      #  log(f"{sound_file}")
        subprocess.run(['aplay', full_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
      #  log(f"Som finalizado: {sound_file}")
    except Exception as e:
        error = f"Erro ao tocar {sound_file}: {e}"
        print(error)
        logging.error(error)

def play_sequence(user_sequence):
    # log("Iniciando sequência de sons (XX.wav)...")
    threads = []
    for key in user_sequence:
        sound_file = f"{int(key):02d}.wav"
        log(f"{sound_file}...")
        t = threading.Thread(target=play_sound, args=(sound_file,), daemon=True)
        t.start()
        threads.append(t)
        time.sleep(0.7)
    
    for t in threads:
        t.join()  # Espera o término de todos os sons antes de seguir


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

has_play_card_sound = False
def wait_for_start_or_reset_key():
    global has_play_card_sound

    print("Aguardando a tecla start para iniciar jogada...")
    while True:
        if GPIO.input(sensor) == False and has_play_card_sound == False:
            has_play_card_sound = True
            log("Sensor ativo")
            threading.Thread(target=play_sound, args=("card.wav",), daemon=True).start()
        if GPIO.input(btn_reset) == GPIO.LOW:
            has_play_card_sound = False
            log("Tecla RESET pressionada")
            reset_game()
            return False
        if GPIO.input(btn_start) == GPIO.LOW:
            has_play_card_sound = False
            log("Tecla START pressionada")
            threading.Thread(target=play_sound, args=("start.wav",), daemon=True).start()
            return True
        time.sleep(0.1)

jogada_atual = 0
winning_offset = 0
winning_jogada = 0

def reset_game():
    global jogada_atual
    global winning_offset
    global winning_jogada

    setup_logging()
    jogada_atual = 0
    winning_offset = get_random_win_offset()
    winning_jogada = jogada_atual + winning_offset
    log(f"Sorteio inicial: Jogada vencedora será a tentativa #{winning_jogada}")

def play_game():
    global jogada_atual
    global winning_offset
    global winning_jogada

    reset_game()
    pending_win = False  # flag para próxima vitória garantida, se repetirem na jogada premiada

    while True:
        jogada_atual += 1
        reset_log_for_jogada(jogada_atual)

        # coleta da sequência do jogador
        user_sequence = []
        click_count = 0
        if not wait_for_start_or_reset_key():
            continue

        sequence_history = read_sequence_history()
        log(f"Jogada atual: {jogada_atual}")
        log(f"Jogada premiada atual: {winning_jogada}")

        # leitura dos 6 cliques
        play_threads = []
        while click_count < 6:
            for idx, btn in enumerate(list_btns):
                if GPIO.input(btn) == GPIO.LOW and idx < 9:  # apenas botões 1–9
                    position = idx + 1
                    t = threading.Thread(target=play_sound, args=(f"{position:02d}.wav",), daemon=True)
                    t.start()
                    play_threads.append(t)
                    user_sequence.append(position)
                    click_count += 1
                    log(f"Posição: [{click_count:02d}]")
                    time.sleep(0.5)

        # espera todos os sons desta jogada terminarem
        log("Aguardando o fim dos sons da jogada...")
        for t in play_threads:
            t.join()

        # registra e toca a sequência
        seq_str = ",".join(map(str, user_sequence))
        log(f"Sequência registrada: {seq_str}")
        play_sequence(user_sequence)

        is_unique = seq_str not in sequence_history

        # Se repetiu...
        if not is_unique:
            logging.warning("Sequência repetida detectada.")
            print("Sequência repetida detectada.")

            # Se estávamos numa jogada premiada ou já tínhamos pending_win,
            # mantemos pending_win = True para a próxima sequência original
            if jogada_atual == winning_jogada or pending_win:
                pending_win = True
                log(" Sequência repetida na jogada premiada → próxima original SERÁ premiada")
            else:
                log(" Sequência repetida em jogada normal → sem efeito no sorteio")
            play_sound("obrigado.wav")
            log("=== FIM DA JOGADA ===")
            continue

        # Se chegou aqui, é sequência original: adiciona ao histórico
        append_sequence(seq_str)

        # Se havia um pending_win, esta jogada é premiada
        if pending_win:
            log("🎉 JOGADA PREMIADA (devido a repetição anterior)! Jogador venceu.")
            play_sound("win.wav")
            pending_win = False
            # agora volta ao sorteio aleatório
            winning_offset = get_random_win_offset()
            winning_jogada = jogada_atual + winning_offset
            log(f"Próxima jogada sorteada para vitória: {winning_jogada}")

        # senão, se for a jogada sorteada originalmente
        elif jogada_atual == winning_jogada:
            log("🎉 JOGADA PREMIADA! Jogador venceu.")
            play_sound("win.wav")
            # sortear próxima vitória
            winning_offset = get_random_win_offset()
            winning_jogada = jogada_atual + winning_offset
            log(f"Próxima jogada sorteada para vitória: {winning_jogada}")

        # caso contrário, não premiada
        else:
            log("Jogada não premiada.")
            play_sound("obrigado.wav")

        log("=== FIM DA JOGADA ===")
        time.sleep(1)


if __name__ == "__main__":
    try:
        play_game()
    except KeyboardInterrupt:
        log("Jogo encerrado manualmente")

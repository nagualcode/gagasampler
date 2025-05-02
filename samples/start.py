#!/usr/bin/env python3
import logging
import time
import threading
import queue
import atexit
import os
import subprocess
import random
import RPi.GPIO as GPIO

# Configurações editáveis
WIN_OFFSETS = [3, 4, 5, 6]  # Editar aqui para alterar os offsets possíveis

# Arquivos de log e histórico
LOG_FILE = "/tmp/gagasampler.log"
DB_FILE = "/tmp/gagasampler.db"

# Mapeamento dos pinos dos botões
btn_1 = 7
btn_2 = 11
btn_3 = 12
btn_4 = 13
btn_5 = 15
btn_6 = 29
btn_7 = 31
btn_8 = 33
btn_9 = 35
btn_start = 37
list_btns = [btn_1, btn_2, btn_3, btn_4, btn_5, btn_6, btn_7, btn_8, btn_9, btn_start]

# Fila auxiliar
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

# Função de log padrão
def log(value):
    logging.info(value)
    print(value)

# Função de reprodução de som
def play_sound(sound_file):
    full_path = f"samples/{sound_file}"
    try:
        log(f"Tocando: {sound_file}")
        subprocess.run(['aplay', full_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        error = f"Erro ao tocar {sound_file}: {e}"
        print(error)
        logging.error(error)

# Inicia o logger e toca o som de inicialização
setup_logging()
play_sound("on.wav")
log("Iniciando GPIO")

# Configura GPIO
GPIO.setmode(GPIO.BOARD)
for btn in list_btns:
    GPIO.setup(btn, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Funções auxiliares de jogo
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

        
# Função que aguarda qualquer botão para iniciar
def wait_for_start_key():
    print("Aguardando qualquer tecla para iniciar jogada...")
    while True:
        for pin in list_btns:
            if GPIO.input(pin) == GPIO.LOW:
                log(f"Tecla no pino {pin} pressionada (START)")
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
            for idx, btn in enumerate(list_btns):
                if GPIO.input(btn) == GPIO.LOW and idx < 9:
                    position = idx + 1
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
        play_game()
    except KeyboardInterrupt:
        log("Jogo encerrado manualmente")

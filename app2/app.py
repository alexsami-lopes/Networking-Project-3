from flask import Flask, render_template, jsonify, request
from datetime import datetime, timedelta
import threading
import time
import requests

app = Flask(__name__)

# Variáveis globais para armazenar o tempo
current_time = datetime.strptime("00:00:00", "%H:%M:%S")
clock1_time = datetime.strptime("00:00:00", "%H:%M:%S")
clock2_time = datetime.strptime("00:00:00", "%H:%M:%S")
clock3_time = datetime.strptime("00:00:00", "%H:%M:%S")
drift = 0  # Drift em segundos
master_clock = None  # Armazena o ID do relógio mestre

# Criação do bloqueio
lock = threading.Lock()

def increment_time():
    global current_time, drift, master_clock, clock2_time
    while True:
        with lock:
            current_time += timedelta(seconds=1 + drift)
            clock2_time = current_time.strftime("%H:%M:%S")
        time.sleep(1)

def send_time():
    clock_id = 2
    while True:
        time.sleep(1)
        with lock:
            current_time_str = current_time.strftime("%H:%M:%S")
        try:
            response1 = requests.post('http://127.0.0.1:8000/update_time', json={'time': current_time_str, 'id': clock_id})
            response3 = requests.post('http://127.0.0.1:8002/update_time', json={'time': current_time_str, 'id': clock_id})
            print(f"Sent time to clock1: {response1.status_code}, clock3: {response3.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Erro ao enviar o tempo: {e}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/time')
def get_time():
    global current_time
    global clock1_time
    global clock3_time
    with lock:
        time_str = current_time.strftime("%H:%M:%S")
    return jsonify(clock1=clock1_time, clock2=time_str, clock3=clock3_time)

@app.route('/set_time', methods=['POST'])
def set_time():
    global current_time
    if request.json:
        new_time_str = request.json.get('time')
        if new_time_str:
            try:
                # Atualiza o tempo atual com base na string recebida
                with lock:
                    current_time = datetime.strptime(new_time_str, "%H:%M:%S")
                print(f"Tempo ajustado para: {current_time.strftime('%H:%M:%S')}")
                return '', 204
            except ValueError as e:
                print(f"Erro ao converter o tempo: {e}")
                return '', 400
    return '', 400

@app.route('/update_time', methods=['POST'])
def update_time():
    global clock1_time, clock2_time, clock3_time
    if request.json:
        print(f"Requisição JSON: {request.json}")
        if 'time' in request.json and 'id' in request.json:
            time_received = request.json['time']
            clock_id = request.json['id']
            
            print(f"ID do relógio: {clock_id}")
            
            # Atualiza o tempo global com base no ID do relógio
            with lock:
                if clock_id == 1:
                    clock1_time = time_received
                    print(f"Horário recebido de clock1: {clock1_time}")
                elif clock_id == 2:
                    clock2_time = time_received
                    print(f"Horário recebido de clock2: {clock2_time}")
                elif clock_id == 3:
                    clock3_time = time_received
                    print(f"Horário recebido de clock3: {clock3_time}")
    return '', 204

@app.route('/set_drift', methods=['POST'])
def set_drift():
    global drift
    if request.json:
        drift_value = request.json.get('drift', 0)
        drift_value = int(drift_value)  # Garantir que o drift é um inteiro
        with lock:
            drift = drift_value
        print(f"Novo valor de drift: {drift}")
    return '', 204

@app.route('/sync', methods=['POST'])
def sync():
    global master_clock
    global clock1_time, clock2_time, clock3_time
    with lock:
        try:
            # Determine o relógio mais atrasado
            times = {
                1: datetime.strptime(clock1_time, "%H:%M:%S"),
                2: datetime.strptime(clock2_time, "%H:%M:%S"),
                3: datetime.strptime(clock3_time, "%H:%M:%S")
            }
            master_clock = min(times, key=times.get)
            master_time = times[master_clock].strftime("%H:%M:%S")
            print(f"Times {times}")
            print(f"Clock {master_clock} definido como mestre. Horário do mestre: {master_time}")
        
        except Exception as e:
            print(f"Erro: {e}")
        
        # Atualiza todos os relógios para o horário do relógio mestre
        for clock_id in [1, 2, 3]:
            if clock_id != master_clock:
                try:
                    response = requests.post(f'http://127.0.0.1:800{clock_id - 1}/set_time', json={'time': master_time})
                    print(f"Sync response from clock{clock_id}: {response.status_code}")
                except requests.exceptions.RequestException as e:
                    print(f"Erro ao sincronizar com o clock {clock_id}: {e}")

    return '', 204

def run_app():
    app.run(port=8001, debug=True, use_reloader=False)

if __name__ == '__main__':
    time_thread = threading.Thread(target=increment_time)
    time_thread.start()
    
    send_time_thread = threading.Thread(target=send_time)
    send_time_thread.start()
    
    server_thread = threading.Thread(target=run_app)
    server_thread.start()

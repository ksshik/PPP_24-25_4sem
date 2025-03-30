import os 
import json 
import socket 
import struct 
import logging 
from datetime import datetime
import hashlib 
import threading
import sys

class Server:
    def __init__(self, host='127.0.0.1', port=57535):
        self.my_host = host 
        self.my_port = port  
        self.socket_serv = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # создание сокета для сетевого взаимодействия 
        self.socket_serv.bind((self.my_host, self.my_port)) # привязка сокета к IP-адресу и порту
        self.socket_serv.listen(1) # максимум 1 подключение в очереди
        self.data_file = "data_environment.json"
        self.history_file = "history_environment.json"
        logging.basicConfig(filename='server.log', level=logging.INFO, # настройка логирования: запись в файл server.log, уровень INFO, формат с временем
                            format='%(asctime)s - %(message)s')
        logging.info("Сервер запущен")
        print(f"Сервер запущен на {self.my_host}:{self.my_port}")  
        self.load_history()  

    def load_history(self):     # загрузка истории изменений переменных из файла
        try:
            with open(self.history_file, 'r') as f:
                self.history = json.load(f)  
        except (FileNotFoundError, json.JSONDecodeError): 
            self.history = [] # пустой список, если нет данных

    def save_changes(self, key, val): # сохранение новой записи в историю изменений переменных окружения
        self.history.append({"timestamp": datetime.now().isoformat(),   
            "key": key, 
            "value": val})
        with open(self.history_file, 'w') as f:
            json.dump(self.history, f, indent=4) # сохранение в файл в формате JSON 

    def get_environment_data(self, sort=None): # сбор данных об окружении
        path = os.environ.get("PATH", "").split(os.pathsep)    # получение списка директорий из переменной окружения PATH
        environment_data = {"directories": {}, "variables": dict(os.environ)} 
        for directory in path:
            if os.path.isdir(directory): # проверяем является ли путь директорией
                try:
                    files = os.listdir(directory)    # получаем список файлов в директории
                    exec_files = [{"name": f,  
                         "size": os.path.getsize(os.path.join(directory, f)), 
                         "mtime": os.path.getmtime(os.path.join(directory, f))}  
                        for f in files 
                        if os.path.isfile(os.path.join(directory, f))  # проверка, что это файл
                        and os.access(os.path.join(directory, f), os.X_OK)]  # проверка, что файл исполняемый
                    if sort: 
                        if sort == "name":
                            exec_files.sort(key=lambda x: x["name"])
                        elif sort == "size":
                            exec_files.sort(key=lambda x: x["size"])
                        elif sort == "mtime":
                            exec_files.sort(key=lambda x: x["mtime"])
                    if exec_files: # если есть исполняемые файлы, добавление их в словарь данных
                        environment_data["directories"][directory] = exec_files
                except PermissionError:     # пропуск директории, если нет прав доступа
                    continue
        return environment_data
    
    def save_to_file(self, data): # сохранение данных в файл
        with open(self.data_file, 'w') as f:
            json.dump(data, f, indent=4)  

    def send_file(self, connection):  # отправка файла клиенту
        try:
            with open(self.data_file, 'rb') as f:
                data = f.read() 
                connection.send(struct.pack('!I', len(data))) # упаковка размера данных в 4 байта 
                connection.send(data) # отправка данных клиенту
        except Exception as e: 
            logging.error(f"Ошибка при отправке файла: {e}")

    def make_hash(self, data):     # создание хеша из строки данных для проверки целостности данных
        return hashlib.sha256(data.encode()).hexdigest() 

    def start(self):     # запуск сервера и обработки команд
        while True:         
            connection, addr = self.socket_serv.accept() # ожидание подключения клиента, получение сокета и адреса
            logging.info(f"Подключился клиент: {addr}")
            print(f"Подключился клиент: {addr}")
            with connection: 
                while True:   
                    try:
                        command = connection.recv(1024).decode().strip()  # получение команды от клиента (до 1024 байт), декодирование и удаление пробелов
                        if not command: # если команда пустая, выход из цикла
                            break
                        logging.info(f"Получена команда: {command}")
            
                        if command.startswith("UPDATE"):
                            update_parts = command.split()     
                            sort = update_parts[1] if len(update_parts) > 1 else None # получение критерия сортировки
                            if sort not in [None, "name", "size", "mtime"]: 
                                connection.send(b"ERROR: Invalid sort criterion") 
                                continue                 
                            data = self.get_environment_data(sort) 
                            self.save_to_file(data)
                            self.send_file(connection) 
                            logging.info("Данные обновлены и отправлены")
                    
                        elif command.startswith("SET "): 
                            try:
                                _, key, val, client_hash = command.split(" ", 3) # разделение команды на части: SET, ключ, значение, хеш     
                                expected_hash = self.make_hash(f"SET {key} {val}") # вычисление ожидаемого хеша для проверки
                                if client_hash != expected_hash:  # проверка совпадения хеша от клиента с ожидаемым 
                                    connection.send(b"ERROR: Hash mismatch")
                                    logging.warning(f"Ошибка хеша для команды SET от {addr}")
                                    continue
                                os.environ[key] = val # установка переменной окружения
                                self.save_changes(key, val) # сохранение изменения в историю
                                connection.send(b"OK") 
                                logging.info(f"Установлена переменная: {key} = {val}")
                            except ValueError:  
                                connection.send(b"ERROR: Invalid SET command")
                        
                        else: 
                            connection.send(b"ERROR: Unknown command")
                    except Exception as e: 
                        logging.error(f"Ошибка обработки команды: {e}")
                        break

class Client:
    def __init__(self, host='127.0.0.1', port=57535): 
        self.my_host = host 
        self.my_port = port 
        self.socket_cl = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  
        self.socket_cl.connect((self.my_host, self.my_port))
        logging.basicConfig(filename='client.log', level=logging.INFO, # настройка логирования: запись в файл client.log, уровень INFO, формат с временем
                            format='%(asctime)s - %(message)s')
        logging.info("клиент запущен и подключен к серверу") 
        print(f"клиент подключен к серверу {self.my_host}:{self.my_port}") 

    def get_file(self): # получение файла от сервера
        try:
            size_data = self.socket_cl.recv(4)  # получение первых 4 байтов, содержащих размер файла
            if not size_data:
                return None
            file_size = struct.unpack('!I', size_data)[0]  # распаковка размера файла из 4 байтов в целое число
            data = b""  # инициализация пустой строки байтов для хранения данных
            while len(data) < file_size:    # получение данных, пока не будет получен весь файл
                packet = self.socket_cl.recv(min(file_size - len(data), 1024)) # сколько байтов осталось получить
                if not packet:     
                    break
                data += packet # добавление полученного пакета к данным
            return json.loads(data.decode()) # декодирование полученных байтов в строку и преобразование из JSON в объект Python
        except Exception as e:
            logging.error(f"Ошибка при получении файла: {e}")
            return None

    def show_info(self, data): # отображение полученных данных
        if not data:  
            print("Ошибка: данные не получены")
            return
        print("\n=== Переменные окружения ===") 
        for key, val in data["variables"].items():  # цикл по всем переменным окружения
            print(f"{key}: {val}")             # вывод каждой пары ключ-значение
        print("\n=== Исполняемые файлы в директориях PATH ===")
        for directory, files in data["directories"].items():  # проходим по всем директориям и по всем файлам каждой из них
            print(f"{directory}:")     
            for f in files: 
                print(f"  - {f['name']} (размер: {f['size']} байт, изменен: {f['mtime']})") 

    def make_hash(self, data): # создание хеша из строки данных
        return hashlib.sha256(data.encode()).hexdigest() 

    def send_command(self, command): # отправка команды серверу и получения ответа
        try:
            self.socket_cl.send(command.encode()) # кодирование команды в байты и отправка серверу
            logging.info(f"Отправлена команда: {command}") 
            if command.startswith("UPDATE"):
                data = self.get_file() # получение данных от сервера (JSON-файл) и их отображение
                self.show_info(data) 
            else:
                response = self.socket_cl.recv(1024).decode() # получение текстового ответа от сервера (до 1024 байт)
                print(f"Ответ сервера: {response}") 
                logging.info(f"Получен ответ: {response}")  
        except Exception as e:
            logging.error(f"Ошибка при отправке команды: {e}")

    def start(self): # запуск клиента и взаимодействие с пользователем
        while True: 
            print("\nКоманды:")
            print("1. UPDATE [name|size|mtime] - обновить данные с сортировкой")
            print("2. SET <key> <value> - установить переменную")
            print("3. EXIT - выйти")
            user_choice = input("Введите команду: ").strip()            
            if user_choice.upper() == "EXIT":
                break
            elif user_choice.upper().startswith("UPDATE"): 
                self.send_command(user_choice.upper())
            elif user_choice.upper().startswith("SET "): 
                set_parts = user_choice.upper().split(" ", 2) 
                if len(set_parts) == 3: # проверка, что команда содержит ключ и значение
                    key = set_parts[1] 
                    val = set_parts[2] 
                    command = f"SET {key} {val} {self.make_hash(f'SET {key} {val}')}" # формирование и отправка команды SET с ключом, значением и хешем
                    self.send_command(command) 
                else: 
                    print("Ошибка: неверный формат команды SET")
            else: 
                print("Неизвестная команда")
        self.socket_cl.close() 
        logging.info("Клиент завершил работу")
        print("Соединение закрыто")

def main():
    if len(sys.argv) != 2:
        print("Использование: python 1lab/main.py [server|client]")
        sys.exit(1)
    
    mode = sys.argv[1].lower()
    
    if mode == "server":
        server = Server()
        server.start()  # запустить сервер
    elif mode == "client":
        client = Client()
        client.start()  # запустить клиента
    else:
        print("Неизвестный режим. Используйте 'server' или 'client'.")
        sys.exit(1)

if __name__ == "__main__":
        print("Неизвестный режим. Используйте 'server' или 'client'")
        sys.exit(1)

if name == "main":
>>>>>>> 89b9e74d5a782a17531ee52bb7e34a8641551291
    main()

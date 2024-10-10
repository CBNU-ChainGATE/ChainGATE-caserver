import time
import requests
import logging
import os
from flask import Flask, request, jsonify
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from ca.ca_utils import create_certificate, verify_certificate, is_certificate_expired
from blockchain.blockchain_utils import send_transaction_to_nodes, search_data_across_nodes
from config import CERTS_DIR, PORT, LOG_UPLOAD_URL

app = Flask(__name__)
logging.basicConfig(filename="logs/caserver.log", filemode="w", level=logging.INFO)

class LogFileHandler(FileSystemEventHandler):
    def __init__(self, log_file_path, server_url):
        self.log_file_path = log_file_path
        self.server_url = server_url

    def on_modified(self, event):
        if event.src_path == self.log_file_path:
            self.send_log_file()

    def send_log_file(self):
        try:
            with open(self.log_file_path, 'rb') as log_file:
                # 파일을 읽어서 서버에 전송
                response = requests.post(self.server_url, files={'file': log_file})
                if response.status_code == 200:
                    print(f"Log file sent successfully: {self.log_file_path}")
                else:
                    print(f"Failed to send log file. Status code: {response.status_code}")
        except Exception as e:
            print(f"Error while sending log file: {e}")

@app.route('/api/v1/cert/request', methods=['POST'])
def issue_cert():
    logging.info("=== 인증서 발급 프로세스 시작 ===")
    csr_pem = request.json.get('csr')
    cert_pem = create_certificate(csr_pem)
    logging.info("=== 인증서 발급 프로세스 완료 ===")
    return jsonify({'certificate': cert_pem})

@app.route('/api/v1/cert/verify', methods=['POST'])
def verify_cert():
    logging.info("=== 인증서 검증 시작 ===")
    cert_pem = request.json.get('cert')
    result = verify_certificate(cert_pem)
    logging.info("=== 인증서 검증 종료 ===")
    return jsonify(result)

@app.route('/api/blockchain/new', methods=['POST'])
def post_new_transaction():
    data = request.get_json()
    result = send_transaction_to_nodes(data)
    return jsonify(result), 201

@app.route('/api/blockchain/search', methods=['POST'])
def post_data_searching():
    data = request.get_json()
    result = search_data_across_nodes(data)
    return jsonify(result)

if __name__ == '__main__':
    log_file_path = "logs/caserver.log"  # 모니터링할 로그 파일 경로

    # 로그 파일 모니터링 설정
    event_handler = LogFileHandler(log_file_path, LOG_UPLOAD_URL)
    observer = Observer()
    observer.schedule(event_handler, path='logs/', recursive=False)

    observer.start()
    print(f"Monitoring changes to {log_file_path}...")

    # 서버 실행
    if not os.path.exists(CERTS_DIR):
        os.makedirs(CERTS_DIR)
    app.run(host='0.0.0.0', port=PORT)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


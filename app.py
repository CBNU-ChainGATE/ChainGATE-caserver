import time
import requests
import logging
import os
import threading
import queue
from flask import Flask, request, jsonify
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from ca.ca_utils import create_certificate, verify_certificate
from blockchain.blockchain_utils import send_transaction_to_nodes, search_data_across_nodes
from config import CERTS_DIR, PORT, LOG_UPLOAD_URL

app = Flask(__name__)

# 로그 전송을 위한 큐
log_queue = queue.Queue()

# 로그 전송 스레드 정의
def process_log_queue():
    while True:
        log_entry, server_url, log_file_name = log_queue.get()
        try:
            response = requests.post(server_url, json={
                'log': log_entry,
                'file_name': log_file_name
            })
            if response.status_code != 200:
                print(f"Failed to send log entry. Status code: {response.status_code}")
        except Exception as e:
            print(f"Error while sending log entry: {e}")
        finally:
            log_queue.task_done()

# 로그 전송 스레드 시작
threading.Thread(target=process_log_queue, daemon=True).start()

# 커스텀 핸들러 정의
class LogServerHandler(logging.Handler):
    def __init__(self, server_url, log_file_name):
        super().__init__()
        self.server_url = server_url
        self.log_file_name = log_file_name

    def emit(self, record):
        log_entry = self.format(record)
        # 로그 메시지를 큐에 추가
        log_queue.put((log_entry, self.server_url, self.log_file_name))

# 로그 설정
log_file_path = "logs/caserver.log"  # 모니터링할 로그 파일 경로
logging.basicConfig(filename=log_file_path, filemode="w", level=logging.INFO)
logger = logging.getLogger()

# 로그 서버로 로그를 보내는 핸들러 추가 (파일 이름 포함)
log_server_handler = LogServerHandler(LOG_UPLOAD_URL, "caserver.log")
log_server_handler.setLevel(logging.INFO)
logger.addHandler(log_server_handler)

@app.route('/api/v1/cert/request', methods=['POST'])
def issue_cert():
    logger.info("=== 인증서 발급 프로세스 시작 ===")
    csr_pem = request.json.get('csr')
    cert_pem = create_certificate(csr_pem)
    logger.info("=== 인증서 발급 프로세스 완료 ===")
    return jsonify({'certificate': cert_pem}), 201

@app.route('/api/v1/cert/verify', methods=['POST'])
def verify_cert():
    logger.info("=== 인증서 검증 시작 ===")
    cert_pem = request.json.get('cert')
    result = verify_certificate(cert_pem)
    logger.info("=== 인증서 검증 종료 ===")
    return jsonify(result), 200

@app.route('/api/blockchain/new', methods=['POST'])
def post_new_transaction():
    data = request.get_json()
    result = send_transaction_to_nodes(data)
    return jsonify(result), 201

@app.route('/api/blockchain/search', methods=['POST'])
def post_data_searching():
    data = request.get_json()
    result = search_data_across_nodes(data)
    return jsonify(result), 200

if __name__ == '__main__':
    # 서버 실행
    if not os.path.exists(CERTS_DIR):
        os.makedirs(CERTS_DIR)
    app.run(host='0.0.0.0', port=PORT)


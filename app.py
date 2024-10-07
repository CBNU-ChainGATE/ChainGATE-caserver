from flask import Flask, request, jsonify
import logging
from ca.ca_utils import create_certificate, verify_certificate, is_certificate_expired
from blockchain.blockchain_utils import send_transaction_to_nodes, search_data_across_nodes
from config import CERTS_DIR, PORT
import os

app = Flask(__name__)
logging.basicConfig(filename="logs/server.log", filemode="w", level=logging.INFO)

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
    if not os.path.exists(CERTS_DIR):
        os.makedirs(CERTS_DIR)
    app.run(host='0.0.0.0', port=PORT)


from flask import Flask, request, jsonify
from OpenSSL import crypto
import os
from config import CA_CERT_PATH, CA_KEY_PATH, CA_KEY_PASSWORD, CRL_PATH, CERTS_DIR, PORT
import time
from datetime import datetime
import hashlib
import logging
import requests

app = Flask(__name__)
logging.basicConfig(filename="logs/server.log", filemode="w", level=logging.INFO)

def load_ca_cert_and_key():
    with open(CA_CERT_PATH, 'r') as f:
        ca_cert = crypto.load_certificate(crypto.FILETYPE_PEM, f.read())
    with open(CA_KEY_PATH, 'r') as f:
        ca_key = crypto.load_privatekey(crypto.FILETYPE_PEM, f.read(), CA_KEY_PASSWORD.encode('utf-8'))
    return ca_cert, ca_key

def create_certificate(csr):
    ca_cert, ca_key = load_ca_cert_and_key()
    cert = crypto.X509()

    current_time = str(time.time()).encode('utf-8')
    serial_number_hash = hashlib.sha256(current_time).hexdigest()
    serial_number = int(serial_number_hash[:16], 16)  # 일련번호의 길이 조정

    cert.set_serial_number(serial_number)
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(31536000)  # 1 year
    cert.set_issuer(ca_cert.get_subject())
    cert.set_subject(csr.get_subject())
    cert.set_pubkey(csr.get_pubkey())
    cert.sign(ca_key, 'sha256')
    return cert

'''
def update_crl(cert_serial_number, reason):
    try:
        with open(CRL_PATH, 'rb') as f:
            crl_data = f.read()
            crl = crypto.load_crl(crypto.FILETYPE_PEM, crl_data)
    except FileNotFoundError:
        crl = crypto.CRL()

    revoked = crypto.Revoked()
    serial_number_hex = format(cert_serial_number, 'x')
    serial_number_bytes = serial_number_hex.encode('ascii')
    print(serial_number_bytes)
    revoked.set_serial(serial_number_bytes)
    revoked.set_reason(reason.encode('utf-8'))
    crl.add_revoked(revoked)

    with open(CRL_PATH, 'wb') as f:
        f.write(crl.export())
'''

def is_certificate_expired(cert):
    not_after_asn1 = cert.get_notAfter()
    cert_not_after = not_after_asn1.decode('utf-8')
    cert_not_after_datetime = datetime.strptime(cert_not_after, '%Y%m%d%H%M%SZ')
    current_datetime = datetime.utcnow()
    return current_datetime > cert_not_after_datetime

###################################################################


@app.route('/api/v1/cert/request', methods=['POST'])
def issue_cert():
    logging.info("=== 인증서 발급 프로세스 시작 ===")
    
    csr_pem = request.json.get('csr')
    logging.info("CSR 수신 완료")

    csr = crypto.load_certificate_request(crypto.FILETYPE_PEM, csr_pem)
    logging.info("CSR 로드 완료")

    cert = create_certificate(csr)
    cert_pem = crypto.dump_certificate(crypto.FILETYPE_PEM, cert).decode('utf-8')
    logging.info("인증서 생성 완료")

    logging.info("=== 인증서 발급 프로세스 완료 ===")
    return jsonify({'certificate': cert_pem})

'''
@app.route('/api/v1/cert/revoke', methods=['POST'])
def revoke_cert():
    cert_pem = request.json.get('cert')
    if not cert_pem:
        return jsonify({'error': 'No certificate data provided'}), 400

    cert = crypto.load_certificate(crypto.FILETYPE_PEM, cert_pem)
    serial_number = cert.get_serial_number()
    try:
        update_crl(serial_number, 'keyCompromise')
        return {'status': 'revoked'}
    except Exception as e:
        return {'error': str(e)}, 500
'''

import logging
from flask import request, jsonify
from OpenSSL import crypto

@app.route('/api/v1/cert/status', methods=['GET'])
def cert_status(serial):
    logging.info(f"=== 인증서 상태 확인 시작 (시리얼: {serial}) ===")
    try:
        with open(CRL_PATH, 'rb') as f:
            crl_data = f.read()
            crl = crypto.load_crl(crypto.FILETYPE_PEM, crl_data)
            logging.info("CRL 로드 완료")
            
            revoked_list = crl.get_revoked()
            if revoked_list is None:
                logging.info("폐기된 인증서 없음")
                return {'status': 'valid'}
            
            for revoked in revoked_list:
                if revoked.get_serial().decode('utf-8') == serial:
                    logging.info(f"인증서 폐기 확인 (시리얼: {serial})")
                    return {'status': 'revoked'}
            
            logging.info(f"유효한 인증서 확인 (시리얼: {serial})")
            return {'status': 'valid'}
    except FileNotFoundError:
        logging.warning("CRL 파일을 찾을 수 없음")
        return {'status': 'valid'}
    except Exception as e:
        logging.error(f"상태 확인 중 오류 발생: {str(e)}")
        return {'status': 'error', 'message': str(e)}
    finally:
        logging.info("=== 인증서 상태 확인 종료 ===")

@app.route('/api/v1/cert/verify', methods=['POST'])
def verify_cert():
    logging.info("=== 인증서 검증 시작 ===")
    cert_pem = request.json.get('cert')
    try:
        cert = crypto.load_certificate(crypto.FILETYPE_PEM, cert_pem)
        logging.info("인증서 로드 완료")
        
        ca_cert, _ = load_ca_cert_and_key()
        logging.info("CA 인증서 로드 완료")
        
        store = crypto.X509Store()
        store.add_cert(ca_cert)
        store_ctx = crypto.X509StoreContext(store, cert)
        store_ctx.verify_certificate()
        logging.info("인증서 체인 검증 완료")
        
        if is_certificate_expired(cert):
            serial = cert.get_serial_number()
            logging.warning(f"인증서 만료 (시리얼: {serial})")
            update_crl(serial, 'expired')
            return jsonify({'status': 'expired'}), 400
        else:
            logging.info("유효한 인증서 확인")
            return jsonify({'status': 'valid'})
    except crypto.X509StoreContextError as e:
        logging.error(f"인증서 검증 실패: {str(e)}")
        return jsonify({'status': 'invalid'}), 400
    except Exception as e:
        logging.error(f"검증 중 오류 발생: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        logging.info("=== 인증서 검증 종료 ===")


@app.route('/api/blockchain/new', methods=['POST'])
def post_new_transaction():
    """I."""
    logging.info("* New transaction request *")
    data = request.get_json()
    endpoint = {
        'node1': '192.168.0.29:1444/transaction/new',
        'node2': '192.168.0.28:1444/transaction/new',
        'node3': '192.168.0.45:1444/transaction/new',
        'node4': '192.168.0.48:1444/transaction/new'
    }
    logging.info('Send Request to every nodes...')
    for node in ["node1", "node2", "node3", "node4"]:
        response = requests.post(
            f"http://{endpoint[node]}", json=data)
    logging.info("complete to send request")
    return jsonify({'message': 'Send Request to node...'}), 201


if __name__ == '__main__':
    if not os.path.exists(CERTS_DIR):
        os.makedirs(CERTS_DIR)
    app.run(host='0.0.0.0', port=PORT)


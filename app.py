from flask import Flask, request, jsonify
from OpenSSL import crypto
import os
from config import CA_CERT_PATH, CA_KEY_PATH, CA_KEY_PASSWORD, CRL_PATH, CERTS_DIR, PORT
import time
from datetime import datetime
import hashlib

app = Flask(__name__)

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

@app.route('/api/v1/cert/request', methods=['POST'])
def request_cert():
    csr_pem = request.json.get('csr')
    csr = crypto.load_certificate_request(crypto.FILETYPE_PEM, csr_pem)
    cert = create_certificate(csr)
    cert_pem = crypto.dump_certificate(crypto.FILETYPE_PEM, cert).decode('utf-8')
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

@app.route('/api/v1/cert/status', methods=['GET'])
def cert_status(serial):
    try:
        with open(CRL_PATH, 'rb') as f:
            crl_data = f.read()
            crl = crypto.load_crl(crypto.FILETYPE_PEM, crl_data)
            revoked_list = crl.get_revoked()
            if revoked_list is None:
                return {'status': 'valid'}
            for revoked in revoked_list:
                if revoked.get_serial().decode('utf-8') == serial:
                    return {'status': 'revoked'}
            return {'status': 'valid'}
    except FileNotFoundError:
        return {'status': 'valid'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

@app.route('/api/v1/cert/verify', methods=['POST'])
def verify_cert():
    cert_pem = request.json.get('cert')
    try:
        cert = crypto.load_certificate(crypto.FILETYPE_PEM, cert_pem)
        ca_cert, _ = load_ca_cert_and_key()
        store = crypto.X509Store()
        store.add_cert(ca_cert)
        store_ctx = crypto.X509StoreContext(store, cert)
        store_ctx.verify_certificate()

        if is_certificate_expired(cert):
            update_crl(cert.get_serial_number(), 'expired')
            return jsonify({'status': 'expired'}), 400
        else:
            return jsonify({'status': 'valid'})

    except crypto.X509StoreContextError:
        return jsonify({'status': 'invalid'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    if not os.path.exists(CERTS_DIR):
        os.makedirs(CERTS_DIR)
    app.run(host='0.0.0.0', port=PORT)


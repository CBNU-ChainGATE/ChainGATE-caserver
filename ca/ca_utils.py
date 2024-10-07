from OpenSSL import crypto
import time
import hashlib
from datetime import datetime
import logging
from config import CA_CERT_PATH, CA_KEY_PATH, CA_KEY_PASSWORD

def load_ca_cert_and_key():
    with open(CA_CERT_PATH, 'r') as f:
        ca_cert = crypto.load_certificate(crypto.FILETYPE_PEM, f.read())
    with open(CA_KEY_PATH, 'r') as f:
        ca_key = crypto.load_privatekey(crypto.FILETYPE_PEM, f.read(), CA_KEY_PASSWORD.encode('utf-8'))
    return ca_cert, ca_key

def create_certificate(csr_pem):
    csr = crypto.load_certificate_request(crypto.FILETYPE_PEM, csr_pem)
    ca_cert, ca_key = load_ca_cert_and_key()
    cert = crypto.X509()
    current_time = str(time.time()).encode('utf-8')
    serial_number_hash = hashlib.sha256(current_time).hexdigest()
    serial_number = int(serial_number_hash[:16], 16)

    cert.set_serial_number(serial_number)
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(31536000)  # 1 year
    cert.set_issuer(ca_cert.get_subject())
    cert.set_subject(csr.get_subject())
    cert.set_pubkey(csr.get_pubkey())
    cert.sign(ca_key, 'sha256')

    return crypto.dump_certificate(crypto.FILETYPE_PEM, cert).decode('utf-8')

def verify_certificate(cert_pem):
    try:
        cert = crypto.load_certificate(crypto.FILETYPE_PEM, cert_pem)
        ca_cert, _ = load_ca_cert_and_key()
        store = crypto.X509Store()
        store.add_cert(ca_cert)
        store_ctx = crypto.X509StoreContext(store, cert)
        store_ctx.verify_certificate()

        if is_certificate_expired(cert):
            return {'status': 'expired'}
        return {'status': 'valid'}
    except crypto.X509StoreContextError:
        return {'status': 'invalid'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

def is_certificate_expired(cert):
    not_after_asn1 = cert.get_notAfter()
    cert_not_after = not_after_asn1.decode('utf-8')
    cert_not_after_datetime = datetime.strptime(cert_not_after, '%Y%m%d%H%M%SZ')
    current_datetime = datetime.utcnow()
    return current_datetime > cert_not_after_datetime


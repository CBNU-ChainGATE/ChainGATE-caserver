import logging
import requests
import random

def send_transaction_to_nodes(data):
    logging.info("=== New transaction request ===")
    endpoint = {
        'node1': '192.168.0.29:1444/transaction/new',
        'node2': '192.168.0.28:1444/transaction/new',
        'node3': '192.168.0.45:1444/transaction/new',
        'node4': '192.168.0.48:1444/transaction/new'
    }

    for node in endpoint:
        logging.info(f'Send Request to {node} ...')
        requests.post(f"http://{endpoint[node]}", json=data)
    logging.info("=== complete to send request ===")
    return {'message': 'Send Request to nodes...'}

def search_data_across_nodes(data):
    logging.info("=== Data searching request ===")
    endpoint = {
        'node1': '192.168.0.29:1444/chain/search',
        'node2': '192.168.0.28:1444/chain/search',
        'node3': '192.168.0.45:1444/chain/search',
        'node4': '192.168.0.48:1444/chain/search'
    }

    results = []
    selected_nodes = random.sample(endpoint.keys(), 2)
    for node in selected_nodes:
        logging.info(f'Send Request to {node} ...')
        response = requests.post(f"http://{endpoint[node]}", json=data)
        if response.status_code == 200:
            results.append(response.json())
        else:
            logging.error(f"Failed to get data from {node}.")
            return {'error': 'Failed to get data!'}

    if len(results) == 2 and results[0] == results[1]:
        logging.info("Found a block that meets the conditions.")
        return {'results': results[0]['results']}
    else:
        logging.error("Chains between nodes do not match!")
        return {"error": "Chain inconsistency detected among nodes."}


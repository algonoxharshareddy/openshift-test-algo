"""
Author: Ashyam
Created Date: 20-02-2019
"""

import os
import json
import requests
import traceback
import subprocess

from flask import Flask, request, jsonify, flash
from urllib.parse import urlparse

from db_utils import DB

from app import app
try:
    from app.ace_logger import Logging
except:
    from ace_logger import Logging

logging = Logging()

# Database configuration
db_config = {
    'host': os.environ['HOST_IP'],
    'user': os.environ['LOCAL_DB_USER'],
    'password': os.environ['LOCAL_DB_PASSWORD'],
    'port': os.environ['LOCAL_DB_PORT'],
}

@app.route('/servicebridge_health_check', methods=['GET'])
def servicebridge_health_check():

    return jsonify({'flag':True})

@app.route('/test', methods=['POST', 'GET'])
def test():
    try:
        data = request.json

        if data['data']:
            return jsonify({'flag': True, 'data': data})
        else:
            return jsonify({'flag': False, 'message': 'Failed to execute the function.'})
    except Exception as e:
        return jsonify({'flag': False, 'message':'System error! Please contact your system administrator.'})

@app.route('/<route>', defaults={'argument': None}, methods=['POST', 'GET'])
@app.route('/<route>/<argument>', methods=['POST', 'GET'])
def connect(route, argument=None):
    """
    This is the only route called from the UI along with the name of the route in
    the URL and the data to be POSTed. This app will reroute to the corresponding
    route sent from the UI.
    The final URL will be generated using the bridge_config.json file. The route
    and its corresponding host and port will be stored in this file.

    Args:
        route (str): The route it should call this app should reroute to.
        data (dict): The data that needs to be sent to the URL.

    Returns:
        flag (bool): True if success otherwise False.
        message (str): Message for the user.

    Note:
        Along with the mentioned keys, there will be other keys that the called
        route will return. (See the docstring of the app)
    """
    try:
        logging.info('Serving a request')
        logging.info(f'Route: {route}')
        logging.info(f'Argument: {argument}')

        logging.debug('Reading bridge config')
        with open('/var/www/service_bridge/app/bridge_config.json') as f:
            connector_config = json.loads(f.read())

        logging.info("############### Hit reached service bridge stage 1")
        if route not in connector_config:
            message = f'Route `{route}` is not configured in bridge_config.json.'
            logging.error(message)
            return jsonify({'flag': False, 'message': message})

        logging.info("############### Hit reached service bridge stage 2")
        route_config = connector_config[route]
        logging.info("############### Hit reached service bridge stage 3")
        host = route_config['host']
        port = route_config['port']

        logging.debug(f'Host: {host}')
        logging.debug(f'Port: {port}')

        if request.method == 'POST':
            logging.debug('POST method.')
            try:

                try:
                    logging.info("############### Hit reached service bridge stage 4")
                    data = request.json
                    data['tenant_id'] = os.environ['TENANT_ID']
                    logging.info(f'Data recieved: {data}')
                except:
                    logging.warning('No data recieved.')
                    data = {}



                tenant_id = None
                try:
                    logging.info("############### Hit reached service bridge stage 5")
                    if 'tenant_id' not in data:    
                        if 'host_url' in data:
                            logging.info("############### Hit reached service bridge stage 6")
                            ui_url=data['host_url']
                            logging.info(f'Got host URL as parameter: {ui_url}')
                        else:
                            ui_url = request.headers.get('Origin')
                            logging.info("############### Hit reached service bridge stage 7")
                        url = urlparse(ui_url).netloc

                        logging.info(f'Request header origin: {ui_url}')
                        logging.info(f'URL: {url}')

                        with open('/var/www/service_bridge/app/tenants.json') as t:
                            tenants = json.loads(t.read())
                            logging.debug(f'Tenant data: {tenants}')

                        for key, val in tenants['tenants'].items():
                            if key == url:
                                tenant_id = val
                                break

                        logging.info("############### Hit reached service bridge stage 8")
                        if tenant_id is None or not tenant_id:
                            logging.warning('Could not find tenant url in tenants.json')
                        
                        logging.info(f'Tenant ID: {tenant_id}')
                    else:
                        logging.warning('Tenant ID already in request data!')
                        tenant_id = data['tenant_id']
                except:
                    logging.exception('Could not get tenant ID from request. Setting tenant ID to None.')
                    tenant_id = None
                    
                if tenant_id == '3.208.195.34':
                    tenant_id = None

                tenant_id = os.environ['TENANT_ID']
                try:
                    logging.info("############### Hit reached service bridge stage 9")
                    user = data['user']
                    db_config['tenant_id'] = tenant_id
                    session_db = DB('group_access', **db_config)
                    logging.info("############### Hit reached service bridge stage 10")
                    query = f"SELECT * FROM `live_sessions` WHERE status = 'active' and user = '{user}' and last_request + INTERVAL 30 MINUTE < CURRENT_TIMESTAMP()"
                    output = session_db.execute(query)
                    logging.info("############### Hit reached service bridge stage 11")
                    if not output.empty:
                        logging.info("############### Hit reached service bridge stage 12")
                        session_id = list(output.session_id)[0]
                        update = f"update live_sessions set status = 'closed' where user = '{user}'"
                        session_db.execute(update)
                        logging.info("############### Hit reached service bridge stage 13")
                        stats_db = DB('stats', **db_config) 
                        audit_data = {
                            "type": "insert", "last_modified_by": "service_bridge", "table_name": "live_sessions",
                            "reference_column": "user",
                            "reference_value": user, "changed_data": json.dumps({"status": "logout", "sessiontimeout": True, "session_id": session_id})
                        }
                        logging.info("############### Hit reached service bridge stage 14")
                        stats_db.insert_dict(audit_data, 'audit')
                        logging.info("############### Hit reached service bridge stage 15")
                        return jsonify({'flag': True, 'sessiontimeout': True})
                    else:
                        logging.info("############### Hit reached service bridge stage 16")
                        update = f"update live_sessions set last_request = CURRENT_TIMESTAMP() , status = 'active' where user = '{user}'"
                        session_db.execute(update)
                        logging.info("############### Hit reached service bridge stage 17")
                except:
                    pass

                data['tenant_id'] = tenant_id
                logging.info(f'Data after adding tenant ID: {data}')

                logging.debug(f'http://{host}:{port}/{route}/{argument}')
                if argument is not None:
                    logging.debug(f"arugument are >>>>>>>>>>> {argument}")
                    response = requests.post(f'http://{host}:{port}/{route}/{argument}', json=data)
                    logging.info("############### Hit reached service bridge stage 18")
                else:
                    logging.debug(f"There are no arguments to pass with route.>>>>>>>>>>>")
                    response = requests.post(f'http://{host}:{port}/{route}', json=data)
                    logging.info("############### Hit reached service bridge stage 19")

                cache_clearing = ['usermanagement']

                if host in cache_clearing:
                    headers = {'Content-type': 'application/json; charset=utf-8', 'Accept': 'text/json'}
                    requests.post(f'http://queueapi:80/clear_cache', headers=headers)
                    logging.info("############### Hit reached service bridge stage 20")

                logging.debug(f'Response: {response.content}')
                try:
                    logging.info("############### Hit reached service bridge stage 21")
                    return jsonify(response.json())
                except:
                    return response.content
            except requests.exceptions.ConnectionError as e:
                message = f'ConnectionError: {e}'
                logging.error(message)
                return jsonify({'flag': False, 'message': message})
            except Exception as e:
                message = f'Could not serve request.'
                logging.exception(message)
                return jsonify({'flag': False, 'message': message})
        elif request.method == 'GET':
            logging.debug('GET method.')
            try:
                params_dict={}
                try:
                    logging.info("############### Hit reached service bridge stage 22")
                    args = request.args

                    for key,value in args.items():
                        params_dict[key]=value
                    logging.info("############### Hit reached service bridge stage 23")

                except Exception as e:
                    logging.info(f"############## Probably no args with url")
                    logging.exception(e)
                logging.info("############### Hit reached service bridge stage 24")
                response = requests.get(f'http://{host}:{port}/{route}',params=params_dict)
                logging.info("############### Hit reached service bridge stage 25")
                logging.debug(f'Response: {response.content}')
                return jsonify(json.loads(response.content))
            except requests.exceptions.ConnectionError as e:
                message = f'ConnectionError: {e}'
                logging.error(message)
                return jsonify({'flag': False, 'message': message})
            except Exception as e:
                message = f'Unknown error calling `{route}`. Maybe should use POST instead of GET. Check logs.'
                logging.exception(message)
                return jsonify({'flag': False, 'message': message})
    except Exception as e:
        logging.exception('Something went wrong in service bridge. Check trace.')
        return jsonify({'flag': False, 'message':'System error! Please contact your system administrator.'})


@app.route('/zipkin', methods=['POST', 'GET'])
def zipkin():
    body = request.data
    requests.post(
            'http://zipkin:9411/api/v1/spans',
            data=body,
            headers={'Content-Type': 'application/x-thrift'},
        )
    return jsonify({'flag': True})

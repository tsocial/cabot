import argparse
import json
from collections import defaultdict

import requests

# python checks.py http://localhost:5001 http://10.22.8.12:9090
# /home/akshay/PycharmProjects/Scripts/venv/cabot/alerts.conf

ACTIVE = "true"
IMPORTANCE = "ERROR"
FREQUENCY = 5
DEBOUNCE = 2
CALCULATED_STATUS = "passing"
ZERO = 0


def parse_args():
    parser = argparse.ArgumentParser(
        description="Creates cabot checks."
                    "Usage: python checks.py url host config_file")
    parser.add_argument("url", type=str, help="URL of Cabot API")
    parser.add_argument("host", type=str, help="Host for the cabot check")
    parser.add_argument("config_file", type=str, help="path/to/checks")
    parser.add_argument("user", type=str, help="username")
    parser.add_argument("password", type=str, help="password")
    return parser


def create_check(url, host, check_name, check_query, check_type, check_value):
    post_url = url + "/api/prometheus_checks/?format=api"
    data = """ {
              "name": "%s",
              "active": %s,
              "importance": "%s",
              "frequency": %d,
              "debounce": %d, 
              "calculated_status": "%s",
              "query": "%s",
              "host": "%s",
              "check_type": "%s",
              "value": "%s",
              "expected_num_hosts": %d,
              "allowed_num_failures": %d
              } """ % (check_name, ACTIVE, IMPORTANCE, FREQUENCY, DEBOUNCE,
                       CALCULATED_STATUS, check_query, host, check_type,
                       check_value, ZERO, ZERO)

    headers = {'Content-Type': "application/json"}
    if check_alert_exists(check_name, url) == "[]":
        print("Creating check for %s" % check_name)
        response = requests.post(post_url, data=data, headers=headers, auth=(user, password))
        return response.status_code


def fix_cabot_query(query):
    return query.replace("\"", "\\\"")


def check_alert_exists(check_name, url):
    get_url = url + "/api/prometheus_checks/?name=%s" % check_name
    headers = {'Content-Type': "application/json"}
    response = requests.get(get_url, headers=headers, auth=(user, password))
    return response.text


def check_service_exists(url, service_name):
    get_url = url + "/api/services/?name=%s" % service_name
    headers = {'Content-Type': "application/json"}
    response = requests.get(get_url, headers=headers, auth=(user, password))
    return response.text


def read_checks_file(file_path):
    with open(file_path) as file:
        checks = file.readlines()
    checks = [x.strip() for x in checks]
    return checks


def generate_checks(url, host, config_file):
    check_list = read_checks_file(config_file)
    for check in check_list:
        check_params = check.split(sep="|")
        create_check(url, host, check_params[1], fix_cabot_query(check_params[2]),
                     check_params[3], check_params[4])


def get_alert_id_with_service(url, alert_name, service_name, service_list):
    check_id = json.loads(check_alert_exists(alert_name, url))[0]["id"]
    service_list[service_name].append(check_id)


def get_service_with_id(url, config_file):
    service_dict = defaultdict(list)
    check_list = read_checks_file(config_file)
    for check in check_list:
        check_params = check.split(sep="|")
        get_alert_id_with_service(url, check_params[1], check_params[0], service_dict)
    return dict(service_dict)


def create_service(service_url, service_name, alerts):
    headers = {'Content-Type': "application/json"}
    service_data = """{
                "name": "%s",
                "users_to_notify": ["1"],
                "alerts_enabled": true,
                "status_checks": %s,
                "alerts": ["1"],
                "hackpad_id": "",
                "url": "",
                "instances": [],
                "overall_status": "PASSING"
            }""" % (service_name, alerts)

    print("Creating service for %s" % service_name)
    response = requests.post(service_url, data=service_data, headers=headers, auth=(user, password))
    return response.status_code


def create_service_with_alerts(url, config_file):
    service_url = url + "/api/services/?format=api"
    services_with_id = get_service_with_id(url, config_file)
    for service in services_with_id.items():
        if check_service_exists(url, service[0]) == '[]':
            create_service(service_url, service[0], service[1])


if __name__ == '__main__':
    parser = vars(parse_args().parse_args())
    url = str(parser["url"])
    host = str(parser["host"])
    config_file = str(parser["config_file"])
    user = str(parser["user"])
    password = str(parser["password"])
    generate_checks(url, host, config_file)
    create_service_with_alerts(url, config_file)

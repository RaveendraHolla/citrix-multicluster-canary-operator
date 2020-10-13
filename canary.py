import requests
import os
import json
import logging
import sys
import yaml
import copy
import time

log = logging.getLogger(__name__)
out_hdlr = logging.StreamHandler(sys.stdout)
out_hdlr.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
out_hdlr.setLevel(logging.INFO)
log.addHandler(out_hdlr)
log.setLevel(logging.INFO)


base_url = "http://127.0.0.1:8001"

namespace = os.getenv("res_namespace", "default")


def increase_traffic_percentage(gtp_dict, gtp_old_destination, gtp_new_destination):
    '''Increase percentage of traffic for new cluster'''
    new_percentage = 0
    old_percentage = 0
    completed = False
    # go through the targets and modify percentage for both old and new.
    for dest_cluster in gtp_dict['spec']['hosts'][0]['policy']['targets']:
        if dest_cluster['destination'] == gtp_old_destination:
            if dest_cluster['weight'] > 0:
                dest_cluster['weight'] -= 5
                old_percentage = dest_cluster['weight']
                if old_percentage == 0:
                    completed = True
        if dest_cluster['destination'] == gtp_new_destination:
            dest_cluster['weight'] += 5
            new_percentage = dest_cluster['weight']
    # add the new entry if it is still 0.
    if new_percentage == 0:
        gtp_dict['spec']['hosts'][0]['policy']['targets'].append({'destination': gtp_new_destination, 'weight' : 5})
        new_percentage = 5
    
    # Remove the old entry if it reduced to 0
    if old_percentage == 0:
        gtp_dict['spec']['hosts'][0]['policy']['targets'] = [x for x in gtp_dict['spec']['hosts'][0]['policy']['targets'] if x['destination'] != gtp_old_destination]

    return completed, new_percentage

def apply_gtp(gtp_dict):
    url = '{}/globaltrafficpolicies'.format(base_url)
    header = {"Content-Type": "application/json"}
    requests.post(url, headers=header, data=gtp_dict)

def read_existing_gtp(gtp_name, gtp_namespace):
    url = '{}/api/v1/namespaces/{}/multiclustercanarys/{}'.format(base_url, gtp_namespace, gtp_name)
    r = requests.get(url)
    return r

def calculate_health_score():
    return 95

def handle_multicluster_canary_crd(canary_cr):
    log.info("handling multicluster canary for GTP {canary_cr['spec']['gtpName']}")
    gtp_dict = read_existing_gtp(canary_cr['spec']['gtpName'], canary_cr['spec']['gtpNamespace'])
    original_gtp_dict = copy.copy(gtp_dict)
    completed = False
    while completed is False:
        completed, percentage = increase_traffic_percentage(gtp_dict, canary_cr['spec']['gtpOldDestination'], canary_cr['spec']['gtpNewDestination'])
        apply_gtp(gtp_dict)
        log.info(f"increased the percentage to {percentage}")
        time.sleep(1)
        health_score = calculate_health_score()
        if health_score < canary_cr['spec']['healthThreshold']:
            log.info(f"Health score dropped to {health_score}. Rolling back now.")
            apply_gtp(original_gtp_dict)
            return False
    log.info("Migration is successful")
    return True


def watch_loop():
    log.info("watching for multicluster canary CRD...")
    url = '{}/api/v1/namespaces/{}/multiclustercanary?watch=true"'.format(
        base_url)
    r = requests.get(url, stream=True)
    # We issue the request to the API endpoint and keep the conenction open
    for line in r.iter_lines():
        obj = json.loads(line)
        # We examine the type part of the object to see if it is MODIFIED
        event_type = obj['type']
        if event_type == "ADDED":
            handle_multicluster_canary_crd(obj['object'])

if __name__ == "__main__": 
    event_loop()

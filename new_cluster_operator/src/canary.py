import requests
from requests.adapters import HTTPAdapter
import os
import json
import logging
import sys
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
ingress_adc_ip = os.getenv("NS_IP")
ingress_adc_user = os.getenv("NS_USER")
ingress_adc_password = os.getenv("NS_PASSWORD")


def increase_traffic_percentage(gtp_dict, gtp_old_destination, gtp_new_destination):
    '''This will modify gtp_dict to ncrease percentage of traffic for new cluster'''
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

def apply_gtp(gtp_dict, gtp_name, gtp_namespace):
    '''This will delete the existing GTP and create the new GTP. TODO: Patching existing GTP'''
    url = '{}/apis/citrix.com/v1beta1/namespaces/{}/globaltrafficpolicies/{}'.format(base_url, gtp_namespace, gtp_name)
    retval = requests.delete(url)
    if gtp_dict['metadata'].get('resourceVersion') is not None:
        gtp_dict['metadata'].pop('resourceVersion')
    url = '{}/apis/citrix.com/v1beta1/namespaces/{}/globaltrafficpolicies'.format(base_url, gtp_namespace)
    header = {"Content-Type": "application/json"}
    requests.post(url, headers=header, json=gtp_dict)

def read_existing_gtp(gtp_name, gtp_namespace):
    url = '{}/apis/citrix.com/v1beta1/namespaces/{}/globaltrafficpolicies/{}'.format(base_url, gtp_namespace, gtp_name)
    r = requests.get(url)
    return r.json()

def calculate_health_score(lbname, interval):
    '''Fetch the counters and calculate the health score and return that value'''
    # save the statistics of the lb vserver representing the service.
    session = requests.Session()
    session.mount("http://", HTTPAdapter(max_retries=3))
    session.auth = (ingress_adc_user, ingress_adc_password)
    adc_stat_url = "http://{}:80:/nitro/v1/stat/lbsvserver/{}".format(ingress_adc_ip, lbname)
    starting_stat = session.get(adc_stat_url)
    starting_stat = original_stat.json()
    # wait for the traffic to hit new lb vserver.
    time.sleep(interval)
    # get the statistics again.
    final_stat = session.get(adc_stat_url)
    final_stat = latest_stat.json()
    # compare them. Decide the health.
    invalidrequestresponse = int(final_stat["lbvserver"]["invalidrequestresponse"]) + int(final_stat["lbvserver"]["invalidrequestresponsedropped"]) - int(starting_stat["lbvserver"]["invalidrequestresponse"]) + int(starting_stat["lbvserver"]["invalidrequestresponsedropped"])
    totalrequests = int(final_stat["lbvserver"]["totalrequests"]) + int(final_stat["lbvserver"]["totalrequests"]) - int(starting_stat["lbvserver"]["totalrequests"]) + int(starting_stat["lbvserver"]["totalrequests"])
    return (totalrequests - invalidrequestresponse)*100/totalrequests if totalrequests > 0 else 100

def handle_multicluster_canary_crd(canary_cr):
    log.info(f"handling multicluster canary for GTP {canary_cr['spec']['gtpName']}")
    gtp_dict = read_existing_gtp(canary_cr['spec']['gtpName'], canary_cr['spec']['gtpNamespace'])
    original_gtp_dict = copy.deepcopy(gtp_dict)
    completed = False
    while completed is False:
        completed, percentage = increase_traffic_percentage(gtp_dict, canary_cr['spec']['gtpOldDestination'], canary_cr['spec']['gtpNewDestination'])
        apply_gtp(gtp_dict, canary_cr['spec']['gtpName'], canary_cr['spec']['gtpNamespace'])
        log.info(f"increased the percentage to {percentage}")
        health_score = calculate_health_score(canary_cr['spec']['healthMonitoringLbName'], canary_cr['spec']['healthMonitoringInterval'])
        if health_score < canary_cr['spec']['healthThreshold']:
            log.info(f"Health score dropped to {health_score}. Migration failed. Rolling back now.")
            apply_gtp(original_gtp_dict, canary_cr['spec']['gtpName'], canary_cr['spec']['gtpNamespace'])
            return False
    log.info("Migration is successful")
    return True


def watch_loop():
    log.info("watching for multicluster canary CRD...")
    url = '{}/apis/citrix.com/v1beta1/multiclustercanaries?watch=true'.format(base_url)
    r = requests.get(url, stream=True)
    # We issue the request to the API endpoint and keep the conenction open
    for line in r.iter_lines():
        obj = json.loads(line)
        # We examine the type part of the object to see if it is MODIFIED
        event_type = obj['type']
        if event_type == "ADDED":
            handle_multicluster_canary_crd(obj['object'])

if __name__ == "__main__": 
    watch_loop()

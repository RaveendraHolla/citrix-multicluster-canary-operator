import requests
from requests.adapters import HTTPAdapter
import os
import json
import logging
import sys
import copy
import time
import urllib3

log = logging.getLogger(__name__)
out_hdlr = logging.StreamHandler(sys.stdout)
out_hdlr.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
out_hdlr.setLevel(logging.INFO)
log.addHandler(out_hdlr)
log.setLevel(logging.INFO)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Kubernetes URL.
base_url = token = namespace = ingress_adc_ip = ingress_adc_user = ingress_adc_password = None

def init_kubernetes_params():
    global namespace, base_url, token
    namespace = os.getenv("res_namespace", "default")
    base_url = "https://"+os.getenv("KUBERNETES_SERVICE_HOST") + ":" + os.getenv("KUBERNETES_SERVICE_PORT")
    # Read serviceaccount access token.
    with open("/var/run/secrets/kubernetes.io/serviceaccount/token") as f:
        token = f.read()

def init_adc_params():
    global ingress_adc_ip, ingress_adc_user, ingress_adc_password
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
    retval = requests.delete(url, headers = {"Authorization":"Bearer " + token}, verify=False)
    if gtp_dict['metadata'].get('resourceVersion') is not None:
        gtp_dict['metadata'].pop('resourceVersion')
    url = '{}/apis/citrix.com/v1beta1/namespaces/{}/globaltrafficpolicies'.format(base_url, gtp_namespace)
    header = {"Content-Type": "application/json", "Authorization":"Bearer " + token}
    requests.post(url, headers=header, json=gtp_dict, verify=False)

def read_existing_gtp(gtp_name, gtp_namespace):
    url = '{}/apis/citrix.com/v1beta1/namespaces/{}/globaltrafficpolicies/{}'.format(base_url, gtp_namespace, gtp_name)
    r = requests.get(url, headers = {"Authorization":"Bearer " + token}, verify=False)
    return r.json()

def calculate_health_score(lbname, interval):
    '''Fetch the counters and calculate the health score and return that value'''
    # save the statistics of the lb vserver representing the service.
    session = requests.Session()
    session.mount("http://", HTTPAdapter(max_retries=3))
    session.auth = (ingress_adc_user, ingress_adc_password)
    adc_stat_url = "http://{}:80/nitro/v1/stat/lbvserver/{}".format(ingress_adc_ip, lbname)
    starting_stat = session.get(adc_stat_url)
    starting_stat = starting_stat.json()
    # wait for the traffic to hit new lb vserver.
    time.sleep(interval)
    # get the statistics again.
    final_stat = session.get(adc_stat_url)
    final_stat = final_stat.json()
    # compare them. Decide the health.
    invalidrequestresponse = int(final_stat["lbvserver"][0]["invalidrequestresponse"]) + int(final_stat["lbvserver"][0]["invalidrequestresponsedropped"]) - int(starting_stat["lbvserver"][0]["invalidrequestresponse"]) + int(starting_stat["lbvserver"][0]["invalidrequestresponsedropped"])
    totalrequests = int(final_stat["lbvserver"][0]["totalrequests"]) + - int(starting_stat["lbvserver"][0]["totalrequests"])
    return (totalrequests - invalidrequestresponse)*100/totalrequests if totalrequests > 0 else 0

def handle_canary_crd(canary_cr):
    try:
        log.info(f"Handling canary CRD {canary_cr['metadata']['name']} for Global Traffic Policy: {canary_cr['spec']['gtpName']}")
        gtp_dict = read_existing_gtp(canary_cr['spec']['gtpName'], canary_cr['spec']['gtpNamespace'])
        original_gtp_dict = copy.deepcopy(gtp_dict)
        completed = False
        while completed is False:
            completed, percentage = increase_traffic_percentage(gtp_dict, canary_cr['spec']['sourceCluster'], canary_cr['spec']['destinationCluster'])
            apply_gtp(gtp_dict, canary_cr['spec']['gtpName'], canary_cr['spec']['gtpNamespace'])
            log.info(f"increased the percentage to {percentage}")
            health_score = calculate_health_score(canary_cr['spec']['healthMonitoringLbName'], canary_cr['spec']['healthMonitoringInterval'])
            if health_score < canary_cr['spec']['healthScoreThreshold']:
                log.info(f"Health score dropped to {health_score}. Migration failed. Rolling back now.")
                apply_gtp(original_gtp_dict, canary_cr['spec']['gtpName'], canary_cr['spec']['gtpNamespace'])
                return False
        log.info("Migration is successful")
        return True
    except Exception as e:
        log.info(f"Exception during handling canary for GTP {canary_cr['spec']['gtpName']}")
        return False


def watch_loop():
    log.info("watching for canary CRDs...")
    resource_version = None
    while True:
        try:
            if resource_version is None:
                url = '{}/apis/citrix.com/v1beta1/canaries?watch=true'.format(base_url)
            else:
                url = '{}/apis/citrix.com/v1beta1/canaries?resourceVersion={}&watch=true'.format(base_url, resource_version)
            r = requests.get(url, headers = {"Authorization":"Bearer " + token}, stream=True, verify=False)
            # We issue the request to the API endpoint and keep the conenction open
            for line in r.iter_lines():
                obj = json.loads(line)
                if obj.get("type") == "ERROR":
                    log.info("ERROR from Kube API server: %s", obj)
                    resource_version = None
                    time.sleep(1)
                # We examine the type part of the object to see if it is MODIFIED
                else:
                    event_type = obj['type']
                    if event_type == "ADDED":
                        handle_canary_crd(obj['object'])
                    resource_version = obj['object']['metadata']['resourceVersion']
        except Exception as e:
            log.info("Exception during listening for canary CRDs. %s", e)
            time.sleep(1)
            log.info("Retrying...")


if __name__ == "__main__": 
    init_kubernetes_params()
    init_adc_params()
    watch_loop()

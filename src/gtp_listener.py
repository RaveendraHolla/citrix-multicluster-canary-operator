import requests
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

def rm_gtp_crd(gtp_dict, params):
    try:
        log.info("Removing local GTP as remote GTP (name:{} namespace:{}) got removed.".format(gtp_dict['metadata']['name'], gtp_dict['metadata']['namespace']))
        url = '{}/apis/citrix.com/v1beta1/namespaces/{}/globaltrafficpolicies/{}'.format(params["base_url"], gtp_dict['metadata']['namespace'], gtp_dict['metadata']['name'])
        retval = requests.delete(url, headers = {"Authorization":"Bearer " + params["token"]}, verify=False)
    except Exception as e:
        log.info("Exception during removing gtp_crd. %s", e)

def add_gtp_crd(gtp_dict, params):
    try:
        log.info("Crating remote GTP (name:{} namespace:{}) locally.".format(gtp_dict['metadata']['name'], gtp_dict['metadata']['namespace']))
        if gtp_dict['metadata'].get('resourceVersion') is not None:
            gtp_dict['metadata'].pop('resourceVersion')
        url = '{}/apis/citrix.com/v1beta1/namespaces/{}/globaltrafficpolicies'.format(params["base_url"], gtp_dict['metadata']['namespace'])
        header = {"Content-Type": "application/json", "Authorization":"Bearer " + params["token"]}
        requests.post(url, headers=header, json=gtp_dict, verify=False)
    except Exception as e:
        log.info("Exception during adding gtp_crd. %s", e)

def get_gtp_resource_version_from_remote_cluster(external_url, external_token):
    try:
        url = '{}/apis/citrix.com/v1beta1/globaltrafficpolicies'.format(external_url)
        r = requests.get(url, headers = {"Authorization":"Bearer " + external_token}, verify=False)
        if r.status_code == 200:
            message = r.json()
            return message['metadata']['resourceVersion']
        else:
            log.info(f"Request {url} is failed with following statuscode {r.status_code}")
            return "0"
    except Exception as e:
        log.info(f"Exception during requesting {url} {e}")
        return "0"

def gtp_watch_loop(params):
    log.info("watching for changes for remote GTP CRDs...")
    while True:
        try:
            resource_version = get_gtp_resource_version_from_remote_cluster(params["external_url"], params["external_token"])
            url = '{}/apis/citrix.com/v1beta1/globaltrafficpolicies?resourceVersion={}&watch=true'.format(params["external_url"], resource_version)
            r = requests.get(url, headers = {"Authorization":"Bearer " + params["external_token"]}, stream=True, verify=False)
            # We issue the request to the API endpoint and keep the conenction open
            for line in r.iter_lines():
                obj = json.loads(line)
                # We examine the type part of the object to see if it is MODIFIED
                if obj.get("type") == "ERROR":
                    log.info("ERROR from Kube API server: %s", obj)
                    time.sleep(1)
                else:
                    event_type = obj.get('type')
                    if event_type == "ADDED":
                        time.sleep(1)
                        add_gtp_crd(obj['object'], params)
                    if event_type == "DELETED":
                        time.sleep(1)
                        rm_gtp_crd(obj['object'], params)
        except Exception as e:
            log.info("Exception during listening for multi-cluster canary CRDs. %s", e)
            time.sleep(1)
            log.info("Retrying...")

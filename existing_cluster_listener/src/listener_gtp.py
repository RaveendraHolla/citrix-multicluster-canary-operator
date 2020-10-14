import requests
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
external_url = os.getenv("External_kubernetes_url", base_url)
external_token = os.getenv("External_Kuubernetes_jwt_token")

def rm_gtp_crd(gtp_dict):
    log.info("Removing local GTP as remote GTP (name:{} namespace:{}) got removed.".format(gtp_dict['metadata']['name'], gtp_dict['metadata']['namespace']))
    url = '{}/apis/citrix.com/v1beta1/namespaces/{}/globaltrafficpolicies/{}'.format(base_url, gtp_dict['metadata']['namespace'], gtp_dict['metadata']['name'])
    retval = requests.delete(url)

def add_gtp_crd(gtp_dict):
    log.info("Crating remote GTP (name:{} namespace:{}) locally.".format(gtp_dict['metadata']['name'], gtp_dict['metadata']['namespace']))
    if gtp_dict['metadata'].get('resourceVersion') is not None:
        gtp_dict['metadata'].pop('resourceVersion')
    url = '{}/apis/citrix.com/v1beta1/namespaces/{}/globaltrafficpolicies'.format(base_url, gtp_dict['metadata']['namespace'])
    header = {"Content-Type": "application/json"}
    requests.post(url, headers=header, json=gtp_dict)

def watch_loop():
    log.info("watching for changes for remote GTP CRDs...")
    url = '{}/apis/citrix.com/v1beta1/globaltrafficpolicies?watch=true'.format(external_url)
    r = requests.get(url, headers = {"Authorization":"Bearer " + external_token}, stream=True, verify=False)
    # We issue the request to the API endpoint and keep the conenction open
    for line in r.iter_lines():
        obj = json.loads(line)
        # We examine the type part of the object to see if it is MODIFIED
        event_type = obj['type']
        if event_type == "ADDED":
            add_gtp_crd(obj['object'])
        if event_type == "DELETED":
            rm_gtp_crd(obj['object'])

if __name__ == "__main__": 
    watch_loop()

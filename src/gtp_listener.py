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
from kubernetes import client, config
from kubernetes.client.rest import ApiException

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def rm_gtp_crd(gtp_dict, params, api_instance):
    try:
        log.info("Removing local GTP as remote GTP (name:{} namespace:{}) got removed.".format(gtp_dict['metadata']['name'], gtp_dict['metadata']['namespace']))
        # url = '{}/apis/citrix.com/v1beta1/namespaces/{}/globaltrafficpolicies/{}'.format(params["base_url"], gtp_dict['metadata']['namespace'], gtp_dict['metadata']['name'])
        group = 'citrix.com'
        version = 'v1beta1'
        plural = 'globaltrafficpolicies'
        # retval = requests.delete(url, headers = {"Authorization":"Bearer " + params["token"]}, verify=False)
        api_response = api_instance.delete_namespaced_custom_object(group, version, gtp_dict['metadata']['namespace'], plural, ,gtp_dict['metadata']['name'], body=body)
    except ApiException as e:
        print("Exception when calling CustomObjectsApi->delete_namespaced_custom_object: %s\n" % e)
    except Exception as e:
        log.info("Exception during removing gtp_crd. %s", e)

def add_gtp_crd(gtp_dict, params, api_instance):
    try:
        log.info("Crating remote GTP (name:{} namespace:{}) locally.".format(gtp_dict['metadata']['name'], gtp_dict['metadata']['namespace']))
        if gtp_dict['metadata'].get('resourceVersion') is not None:
            gtp_dict['metadata'].pop('resourceVersion')
        # url = '{}/apis/citrix.com/v1beta1/namespaces/{}/globaltrafficpolicies'.format(params["base_url"], gtp_dict['metadata']['namespace'])
        # header = {"Content-Type": "application/json", "Authorization":"Bearer " + params["token"]}
        # requests.post(url, headers=header, json=gtp_dict, verify=False)
        group = 'citrix.com'
        version = 'v1beta1'
        plural = 'globaltrafficpolicies'
        api_response = api_instance.create_namespaced_custom_object(group, version, namespace=gtp_dict['metadata']['namespace'], plural, body)
    except ApiException as e:
        log.error("Exception when calling CustomObjectsApi->create_namespaced_custom_object: %s\n" % e)
    except Exception as e:
        log.error("Exception during adding gtp_crd. %s", e)

def get_gtp_resource_version_from_remote_cluster(api_instance):
    try:
        # url = '{}/apis/citrix.com/v1beta1/globaltrafficpolicies'.format(external_url)
        group = 'citrix.com'
        version = 'v1beta1'
        plural = 'globaltrafficpolicies'
        api_response = api_instance.list_cluster_custom_object(group, version, plural, resource_version=resource_version, timeout_seconds=60, watch=False)
        if api_response.status_code == 200:
            message = api_response.json()
            return message['metadata']['resourceVersion']
        else:
            log.info(f"Request {url} is failed with following statuscode {api_response.status_code}")
            return "0"
    except Exception as e:
        log.info(f"Exception during requesting resource version from remote cluster: {e}")
        return "0"

def gtp_watch_loop(params):
    log.info("watching for changes for remote GTP CRDs...")
    remoteClusterConfiguration = client.Configuration()
    remoteClusterConfiguration.host = params["external_url"]
    remoteClusterConfiguration.verify_ssl = False
    remoteClusterConfiguration.api_key = {"authorization": "Bearer " + params["external_token"]}

    # get local cluster details. That is for pushing GTPs to local cluster.
    localClusterConfiguration = client.Configuration()
    localClusterConfiguration.host = params["base_url"]
    localClusterConfiguration.verify_ssl = False
    localClusterConfiguration.api_key = {"authorization": "Bearer " + params["token"]}

    while True:
        try:

            # r = requests.get(url, headers = {"Authorization":"Bearer " + params["external_token"]}, stream=True, verify=False)
            # We issue the request to the API endpoint and keep the conenction open
            with client.ApiClient(remoteClusterConfiguration) as remote_api_client, client.ApiClient(localClusterConfiguration) as local_api_client:
                remote_api_instance = client.CustomObjectsApi(rempte_api_client)
                local_api_instance = client.CustomObjectsApi(local_api_client)
                group = 'citrix.com'
                version = 'v1beta1'
                plural = 'globaltrafficpolicies'
                resource_version = get_gtp_resource_version_from_remote_cluster(remote_api_instance)
                api_response = api_instance.list_cluster_custom_object(group, version, plural, resource_version=resource_version, timeout_seconds=60, watch=True)
                
                for line in api_response.iter_lines():
                    obj = json.loads(line)
                    # We examine the type part of the object to see if it is MODIFIED
                    if obj.get("type") == "ERROR":
                        log.info("ERROR from Kube API server: %s", obj)
                        time.sleep(1)
                    else:
                        event_type = obj.get('type')
                        if event_type == "ADDED":
                            time.sleep(1)
                            add_gtp_crd(obj['object'], params, local_api_instance)
                        if event_type == "DELETED":
                            time.sleep(1)
                            rm_gtp_crd(obj['object'], params, local_api_instance)
        except Exception as e:
            log.info("Exception during listening for multi-cluster canary CRDs. %s", e)
            time.sleep(1)
            log.info("Retrying...")

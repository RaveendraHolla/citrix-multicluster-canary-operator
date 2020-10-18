import canary_listener
import gtp_listener
import os

def read_params():
    params_dict = {}
    params_dict["mode"] = os.getenv("MODE")
    params_dict["base_url"] = "https://"+os.getenv("KUBERNETES_SERVICE_HOST") + ":" + os.getenv("KUBERNETES_SERVICE_PORT")
    # Read serviceaccount access token.
    with open("/var/run/secrets/kubernetes.io/serviceaccount/token") as f:
        params_dict["token"] = f.read()

    params_dict["ingress_adc_ip"] = os.getenv("NS_IP")
    params_dict["ingress_adc_user"] = os.getenv("NS_USER")
    params_dict["ingress_adc_password"] = os.getenv("NS_PASSWORD")
    params_dict["external_token"] = os.getenv("External_Kuubernetes_jwt_token")
    params_dict["external_url"] = os.getenv("External_kubernetes_url")

    return params_dict

if __name__ == "__main__": 
    params = read_params()
    if params["mode"] == "listener":
        gtp_listener.gtp_watch_loop(params)
    else:
        canary.canary_watch_loop(params)

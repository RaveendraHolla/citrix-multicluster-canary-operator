# citrix-canary-operator-using-multicluster-CRDs
This will build a canary operator on top of Citrix multicluster GSLB based CRDs which help divert traffic from one Cluster to another.

## Description
This is a python operator which leverages on cloud native Citrix multi-cluster ingress solutions to create a canary strategy for migrating app traffic from one cluster to other.

## What are Canary deployments?

Until about thirty years ago, coal miners used to go down to work carrying canaries with them in glass chambers such as these. Underground mines can contain potentially deadly gases such as carbon monoxide that can form during an accident such as fire or an explosion. The odorlessand colorlessgas is equally deadly to both humans and canaries alike, but canaries are much more susceptible to the gas, and reacts more quickly and visibly than humans do, thus alerting miners to the presence of the poisonous gas.

### Canary deployments as CICD strategy

## Use-case:

### Use-case-1:
Customer has hosted an application in an on-prem Kubernetes cluster, now he wants to migrate that application to a Kubernetes cluster on cloud. He wants migration to be smooth and what to evaluate the build as he redirects a portion of the traffic towards new cluster.

### Use-case-2:
Customer hosted an app in multiple Kubernetes clusters. Now, he wants to migrate that app to the latest version of the Kubernetes cluster. He wants migration to be smooth and what to evaluate the build as he redirects a portion of the traffic towards new cluster.

## Existing Deployment:
An App is hosted on multiple clusters 



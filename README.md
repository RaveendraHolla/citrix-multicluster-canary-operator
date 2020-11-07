# citrix-canary-operator-using-multicluster-CRDs
This will build a canary operator on top of Citrix multicluster GSLB based CRDs which help divert traffic from one Cluster to another.

## Description
This is a python operator which leverages on cloud native Citrix multi-cluster ingress solutions to create a canary strategy for migrating app traffic from one cluster to other.

## What are Canary deployments?

Until about thirty years ago, coal miners used to go down to work carrying canaries with them in glass chambers such as these. Underground mines can contain potentially deadly gases such as carbon monoxide that can form during an accident such as fire or an explosion. The odorlessand colorlessgas is equally deadly to both humans and canaries alike, but canaries are much more susceptible to the gas, and reacts more quickly and visibly than humans do, thus alerting miners to the presence of the poisonous gas.

### Canary deployments as CICD strategy

#### Benefits
- Minimizes blast radius of new releases in production
- Gives insight into user experience from small sample of users
- Gives ability to roll-back releases if things don’t work out
- Gives Developers time to roll-out or roll-back releases carefully

#### Use cases
- New version of app with new features or bug fixes
- Infrastructure updates (upgrade of databases or operating systems or Kubernetes itself)
- Bring up new PoPor Region or Availability zones
- Bring up multi cloud or hybrid cloud setups

#### Customer scenarios

- Customer has hosted an application in an on-prem Kubernetes cluster, now he wants to migrate that application to a Kubernetes cluster on cloud. He wants migration to be smooth and what to evaluate the build as he redirects a portion of the traffic towards new cluster.

- Customer hosted an app in multiple Kubernetes clusters. Now, he wants to migrate that app to the latest version of the Kubernetes cluster. He wants migration to be smooth and what to evaluate the build as he redirects a portion of the traffic towards new cluster.

## Existing Deployment:
An App is hosted on multiple clusters 



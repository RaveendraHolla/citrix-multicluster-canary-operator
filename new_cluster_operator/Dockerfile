FROM python:latest
RUN pip install requests
RUN pip install kubernetes
COPY src/canary.py /canary.py
ENTRYPOINT [ "python", "/canary.py" ]

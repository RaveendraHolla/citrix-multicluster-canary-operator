FROM python:latest
RUN pip install requests
RUN pip install kubernetes
COPY src/gtp_listener.py /gtp_listener.py
COPY src/canary_listener.py /canary_listener.py
COPY src/canary_main.py /canary_main.py
ENTRYPOINT [ "python", "/canary_main.py" ]

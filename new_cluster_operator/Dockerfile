FROM python:latest
RUN pip install requests
COPY src/canary.py /canary.py
ENTRYPOINT [ "python", "/canary.py" ]

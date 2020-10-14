FROM python:latest
RUN pip install requests
COPY src/listener_gtp.py /listener_gtp.py
ENTRYPOINT [ "python", "/listener_gtp.py" ]

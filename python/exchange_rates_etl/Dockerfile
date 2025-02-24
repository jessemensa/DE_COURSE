FROM python:3

ADD main.py /

RUN pip install pandas==2.2.3
RUN pip install requests==2.32.3
RUN pip install sqlalchemy==2.0


ENTRYPOINT ["python", "main.py"]

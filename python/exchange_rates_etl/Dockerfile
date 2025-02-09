FROM python:3

ADD main.py /

RUN pip install pandas
RUN pip install requests
RUN pip install sqlalchemy


ENTRYPOINT ["python", "main.py"]

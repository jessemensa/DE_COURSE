# ETL for Currency Converter

This repository contains a simple python script that will allow us to programmatically interact with the 'Exchangerates API"
provided in the Challenge allowing us to build an ETL pipeline .


## Introduction

The motivation behind this Project is to simplify and Automate the process involved in the extraction of both the latest exchange rates and those from 2 days ago with EUR as the base rate . This date needs to be stored in database which will allow us to perform further analysis such as converting from EUR to GBP.

## File structure

```
├── Dockerfile
├── Readme.md
├── Tests
│   ├── sample_response.json
│   └── test.py
├── backup-whateverfolder-2021-06-26.txt
├── db
│   └── foo.db
├── docker-compose.yml
├── main.py
└── ETL.png

2 directories, 9 files
```

## Dependencies
- pandas
```bash
pip install pandas==2.2.3
```
- requests
```bash
pip install requests==2.32.3
```
- SqlAlchemy
```bash
pip install sqlalchemy==2.0
```
- requests-mock
```bash
pip install requests-mock
```



# How to use

The file "main.py" contains the ETL script and relies on certain libraries to function hence i have provided a simple a way for us
to run this code locally using containerization via Docker. Simply clone or fork this repository to your local environment and execute
the code you see below :

```
docker compose up

```
## Useful Info

- In order to persist the data within the container , we mounted a directory containing a sqlite databse which would house our structured data after ETL . This allowed us to run a sample SQL query at the end  which converts 100 EUR to GBP using exchange rates from 2days ago

- The ETL is able to re-import historical rates from a specific point in time together with the latest rates.

- The table is overitten everytime the script is run overwriting existing records in the databse hence , at any point in time , we can be assured that we are using the right rates.

- With regard to tests , i used a library that allows us to mock the exchenge rate api in python .

# Next Steps - Running in Production

- Since Cloud Composer runs on top of a Google Kubernetes Engine (GKE) cluster, this allows for massive scalability and working around the limitations of the other managed Airflow services out there. Hence we can setup an Airflow Environment using this approach and configure a Dag File to run this ETL process. Google Query/Amazon redshift could be possible candidates for Datawarehousing . You can find a visual representation on "heycar_ETL.png"



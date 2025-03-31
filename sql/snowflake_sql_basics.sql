##############################################
-- CREATE DATA OBJECTS IN SNOWFLAKE
##############################################

// Step_0 : Choose a Default warehouse
USE WAREHOUSE COMPUTE_WH;

// Step_1 :Creating a Database
CREATE OR REPLACE DATABASE company_db;

// Step_2 : Use Database
USE DATABASE  company_db;

// Step_3 : Create Schemas
CREATE SCHEMA hr_schema;

// Step_4 : Create employees/addresses table
// inside hr_schema

CREATE TABLE employees (
   id INT PRIMARY KEY,
   name STRING,
   department STRING ,
   salary FLOAT,
   hire_date DATE

);

CREATE TABLE addresses (
   address_id INT PRIMARY KEY,
   employee_id INT,
   street STRING,
   city STRING,
   STATE STRING,
   FOREIGN KEY (employee_id) REFERENCES employees(id)
);

##############################################
-- BASIC OPERATIONS IN SQL
##############################################
// Step_5 : insert sample Data
// Into employees/addresses Table

-- employees table
INSERT INTO employees (ID, Name, Department, Salary, Hire_Date)
VALUES
(1, 'Alice', 'HR', 75000, '2023-01-15'),
(2, 'Bob', 'Finance', 85000, '2022-03-20'),
(3, 'Charlie', 'Engineering', 95000, '2021-06-10'),
(4, 'Dana', 'Marketing', 72000, '2023-07-25');

SELECT *
FROM employees


-- addresses table
INSERT INTO addresses (Address_ID, Employee_ID, Street, City, State)
VALUES
(1, 1, '123 Main St', 'New York', 'NY'),
(2, 2, '456 Elm St', 'Los Angeles', 'CA'),
(3, 3, '789 Pine St', 'Chicago', 'IL'),
(4, 4, '101 Maple Ave', 'Houston', 'TX');

SELECT *
FROM addresses

// Alter employees Tables

ALTER TABLE employees ADD COLUMN email STRING;

-- Add Some Data To New Column
UPDATE employees SET email = 'alice@example.com' WHERE id = 1;
UPDATE employees SET email = 'bob@example.com' WHERE id = 2;
UPDATE employees SET email = 'charlie@example.com' WHERE id = 3;
UPDATE employees SET email = 'dana@example.com' WHERE id = 4;

SELECT * FROM employees;

// Delete Data
DELETE FROM employees WHERE id = 4;

##############################################
-- BASIC JOINS IN SQL
##############################################

// Step_6 : Inner Join
SELECT
    employees.id ,
    employees.name,
    employees.department,
    employees.salary,
    employees.hire_date,
    employees.email,
    addresses.street,
    addresses.city,
    addresses.state
FROM employees
INNER JOIN addresses
ON employees.id = addresses.employee_id;

// Step_8 : Left Join
SELECT
    employees.id,
    employees.name,
    employees.department,
    employees.salary,
    employees.hire_date,
    employees.email,
    addresses.street,
    addresses.city,
    addresses.state
FROM employees
LEFT JOIN addresses
ON employees.id = addresses.employee_id;

// Step_9 : Right Outer Join
SELECT
    employees.id,
    employees.name,
    employees.department,
    employees.salary,
    employees.hire_date,
    employees.email,
    addresses.street,
    addresses.city,
    addresses.state
FROM employees
RIGHT OUTER JOIN addresses
ON employees.id = addresses.employee_id;


// Step_10 : Left Outer Join
SELECT
    employees.id,
    employees.name,
    employees.department,
    employees.salary,
    employees.hire_date,
    employees.email,
    addresses.street,
    addresses.city,
    addresses.state
FROM addresses
LEFT OUTER JOIN employees
ON employees.id = addresses.employee_id;

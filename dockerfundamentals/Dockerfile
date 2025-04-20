# Use an official Python runtime as a parent image
FROM python:3.9 

# Set the working directory in the container
WORKDIR /test

# Copy the current directory contents into the container at /app
COPY . /test

# Run app.py when the container launches
CMD ["python", "test.py"]
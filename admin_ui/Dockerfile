# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the application files into the container
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port the app runs on
EXPOSE 8000

# Define the command to run the application
# We use gunicorn for a production-ready server
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]

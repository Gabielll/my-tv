# Use the official Python image.
FROM python:3.9-slim

# Set the working directory.
WORKDIR /app

# Copy shared modules first.
COPY shared/ /app/shared/

# Copy service-specific code.
COPY stream_api/ /app/

# Install dependencies.
RUN pip install --no-cache-dir -r requirements.txt

# Command to run the service.
CMD ["python", "app.py"]

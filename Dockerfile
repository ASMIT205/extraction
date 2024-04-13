# Use the official Ubuntu image as base
FROM ubuntu:latest

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive

# Update and install necessary packages
RUN apt-get update && \
    apt-get install -y git python3 python3-venv python3-pip tesseract-ocr && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Clone repository
WORKDIR ~
RUN git clone https://github.com/ASMIT205/extraction.git

# Create and activate virtual environment
WORKDIR ~/extraction
RUN python3 -m venv venv && \
    . venv/bin/activate && \
    pip install --upgrade pip && \
    pip install -r requirements.txt

# Expose the port the app runs on
EXPOSE 5000

# Command to run the application
CMD ["venv/bin/python", "test.py"]

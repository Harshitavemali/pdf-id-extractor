# Use the official Python image
FROM python:3.12-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all backend files into the container
COPY . .

# Expose FastAPI port
EXPOSE 8000

# Start the FastAPI server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
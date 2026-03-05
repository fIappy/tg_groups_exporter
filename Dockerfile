FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Expose Web UI port
EXPOSE 8000

# Start Web UI by default
CMD ["python", "web_app.py"]
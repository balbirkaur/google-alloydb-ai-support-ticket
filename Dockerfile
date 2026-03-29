FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# 💡 FIX: Using app.main because your file is in a folder named 'app'
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]



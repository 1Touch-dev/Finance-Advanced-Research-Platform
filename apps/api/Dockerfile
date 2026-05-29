FROM python:3.11-slim

WORKDIR /app/api

COPY apps/api/pyproject.toml ./
COPY apps/api/app ./app
RUN pip install --upgrade pip && pip install -e .

COPY packages/finance /packages/finance
RUN pip install -e /packages/finance

EXPOSE 3001
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "3001"]

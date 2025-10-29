#frontend
FROM node:20 AS build-stage
WORKDIR /frontend
COPY frontend/ .
RUN npm install
RUN npm run build

#backend
FROM python:3.12-trixie
WORKDIR /backend
COPY backend/ .

ENV PATH="${PATH}:/root/.local/bin"
ENV PYTHONPATH=.

RUN pip install --no-cache-dir --upgrade -r requirements.txt
COPY --from=build-stage /frontend/dist dist
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5600"]

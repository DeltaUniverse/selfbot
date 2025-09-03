FROM python:3.11-alpine AS build
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /tmp
RUN apk add --no-cache git

RUN python -m venv /opt/venv
RUN pip install -U pip

COPY ./requirements.txt ./
RUN pip install -Ur requirements.txt


FROM python:3.11-alpine
ENV PATH="/opt/venv/bin:$PATH" TZ="Asia/Jakarta"

WORKDIR /app
RUN apk add --no-cache git

COPY --from=build /opt/venv /opt/venv
COPY . .

CMD ["python", "-m", "selfbot"]

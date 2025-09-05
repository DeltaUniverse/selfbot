FROM python:3.11-alpine AS build

ENV VENV="/opt/venv"
ENV PATH="$VENV/bin:$PATH"

WORKDIR /tmp

RUN apk add --no-cache build-base git

RUN python -m venv $VENV
RUN pip install --upgrade pip

COPY ./requirements.txt ./
RUN pip install -r requirements.txt

COPY . /app


FROM python:3.11-alpine

ENV VENV="/opt/venv"
ENV PATH="$VENV/bin:$PATH" TZ="Asia/Jakarta"

WORKDIR /app

RUN apk add --no-cache git

COPY --from=build $VENV $VENV
COPY --from=build /app /app

CMD ["python", "-m", "selfbot"]

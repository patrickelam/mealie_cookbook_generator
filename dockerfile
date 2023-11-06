FROM python:3.10-alpine

WORKDIR /usr/src/app

COPY requirements.txt .

RUN apk add py3-pip py3-pillow py3-cffi py3-brotli gcc musl-dev python3-dev pango

RUN apk --update --upgrade --no-cache add fontconfig ttf-freefont font-noto terminus-font \ 
   && fc-cache -f \ 
   && fc-list | sort 

RUN pip install --no-cache-dir --upgrade pip \
  && pip install --no-cache-dir -r requirements.txt
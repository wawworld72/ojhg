FROM python:3.12-slim

RUN groupadd -g 1001 judge && useradd -u 1001 -g judge -s /sbin/nologin judge
RUN apt-get update && apt-get install -y --no-install-recommends timeout && rm -rf /var/lib/apt/lists/*

WORKDIR /sandbox
RUN chown judge:judge /sandbox

USER judge

FROM gcc:13

RUN groupadd -g 1001 judge && useradd -u 1001 -g judge -s /sbin/nologin judge
RUN apt-get update && apt-get install -y --no-install-recommends coreutils && rm -rf /var/lib/apt/lists/*

WORKDIR /sandbox
RUN chown judge:judge /sandbox

USER judge

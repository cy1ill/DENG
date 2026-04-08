FROM kestra/kestra:latest

RUN /app/kestra plugins install \
  io.kestra.plugin:plugin-script-shell:LATEST

COPY --from=docker:27-cli /usr/local/bin/docker /usr/local/bin/docker
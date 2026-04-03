FROM kestra/kestra:latest

USER root

COPY --from=docker:27-cli /usr/local/bin/docker /usr/local/bin/docker
FROM alpine:3.20

# Dung cu do dac nam trong cung mang frontend voi load balancer de IP nguon
# cua request la that, khong bi Docker Desktop NAT ghi de nhu khi goi tu
# Windows.
RUN apk add --no-cache curl apache2-utils bash jq coreutils openssl

WORKDIR /scripts

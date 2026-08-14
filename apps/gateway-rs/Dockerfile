FROM rust:1.89-bookworm AS builder

WORKDIR /app
COPY Cargo.toml Cargo.toml
COPY src src
RUN cargo build --release

FROM debian:bookworm-slim

RUN apt-get update \
  && apt-get install -y --no-install-recommends ca-certificates curl \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /app/target/release/runledger-gateway-rs /usr/local/bin/runledger-gateway-rs

EXPOSE 8210

CMD ["runledger-gateway-rs"]

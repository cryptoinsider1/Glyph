#!/bin/bash
cd "$(dirname "$0")/../modules/crypto_rust"
cargo build --release
echo "Rust module built at target/release/crypto_rust"

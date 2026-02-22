use serde::{Deserialize, Serialize};
use std::io::{self, BufRead};
use sha2::{Sha256, Digest};
use aes_gcm::{
    aead::{Aead, KeyInit, OsRng},
    Aes256Gcm, Nonce,
};
use base64::{engine::general_purpose::STANDARD as BASE64, Engine as _};

#[derive(Deserialize, Debug)]
struct Request {
    cmd: String,
    data: Option<String>,          // hex-encoded bytes
    algorithm: Option<String>,
    key: Option<String>,           // для шифрования
}

#[derive(Serialize, Debug)]
struct Response {
    result: Option<String>,        // hex или base64 результат
    error: Option<String>,
}

fn main() {
    let stdin = io::stdin();
    for line in stdin.lock().lines() {
        let line = match line {
            Ok(l) => l,
            Err(e) => {
                eprintln!("Error reading stdin: {}", e);
                continue;
            }
        };
        let req: Request = match serde_json::from_str(&line) {
            Ok(r) => r,
            Err(e) => {
                let resp = Response { result: None, error: Some(format!("Invalid JSON: {}", e)) };
                println!("{}", serde_json::to_string(&resp).unwrap());
                continue;
            }
        };
        let resp = match req.cmd.as_str() {
            "hash" => handle_hash(&req),
            "encrypt" => handle_encrypt(&req),
            _ => Response { result: None, error: Some(format!("Unknown command: {}", req.cmd)) },
        };
        println!("{}", serde_json::to_string(&resp).unwrap());
    }
}

fn handle_hash(req: &Request) -> Response {
    let data_hex = match &req.data {
        Some(d) => d,
        None => return Response { result: None, error: Some("Missing data".to_string()) },
    };
    let data = match hex::decode(data_hex) {
        Ok(d) => d,
        Err(e) => return Response { result: None, error: Some(format!("Invalid hex: {}", e)) },
    };
    let algo = req.algorithm.as_deref().unwrap_or("sha256");
    match algo {
        "sha256" => {
            let mut hasher = Sha256::new();
            hasher.update(&data);
            let result = hasher.finalize();
            Response { result: Some(hex::encode(result)), error: None }
        }
        _ => Response { result: None, error: Some(format!("Unsupported hash algorithm: {}", algo)) },
    }
}

fn handle_encrypt(req: &Request) -> Response {
    let data_hex = match &req.data {
        Some(d) => d,
        None => return Response { result: None, error: Some("Missing data".to_string()) },
    };
    let data = match hex::decode(data_hex) {
        Ok(d) => d,
        Err(e) => return Response { result: None, error: Some(format!("Invalid hex: {}", e)) },
    };
    let key_b64 = match &req.key {
        Some(k) => k,
        None => return Response { result: None, error: Some("Missing key".to_string()) },
    };
    let key_bytes = match BASE64.decode(key_b64) {
        Ok(k) => k,
        Err(e) => return Response { result: None, error: Some(format!("Invalid base64 key: {}", e)) },
    };
    if key_bytes.len() != 32 {
        return Response { result: None, error: Some("Key must be 32 bytes".to_string()) };
    }
    let key = aes_gcm::aead::generic_array::GenericArray::from_slice(&key_bytes);
    let cipher = Aes256Gcm::new(key);
    let nonce = aes_gcm::aead::generic_array::GenericArray::from_slice(&[0u8; 12]); // В реальном проекте используйте случайный nonce и передавайте его
    let ciphertext = match cipher.encrypt(nonce, data.as_ref()) {
        Ok(ct) => ct,
        Err(e) => return Response { result: None, error: Some(format!("Encryption failed: {}", e)) },
    };
    Response { result: Some(hex::encode(ciphertext)), error: None }
}

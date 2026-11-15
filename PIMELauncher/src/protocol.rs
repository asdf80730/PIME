use serde_json::Value;
use std::time::Duration;

/// Maximum allowed length (in bytes) for a single message line.
pub const MAX_MESSAGE_LINE_LENGTH: usize = 1048576;

/// Exact length for a client ID string (standard UUID v4: 36 characters).
pub const CLIENT_ID_LENGTH: usize = 36;

/// Timeout for backend output hang detection.
pub const HANG_TIMEOUT: Duration = Duration::from_secs(15);

/// Timeout for backend write operations.
pub const BACKEND_WRITE_TIMEOUT: Duration = Duration::from_secs(5);

/// Parses the first line received from a client to determine which backend to use.
///
/// Supports standard `{"method": "init", "id": "{GUID}"}`.
pub fn parse_client_handshake(first_line: &str) -> Result<String, String> {
    let json: Value = serde_json::from_str(first_line).map_err(|e| e.to_string())?;

    if let Some(method) = json["method"].as_str() {
        if method == "init" {
            if let Some(guid) = json["id"].as_str() {
                return Ok(guid.to_string());
            }
            return Err("Missing 'id' field in init message".to_string());
        }
        return Err(format!("Unknown method '{}' in initial message", method));
    }
    Err("Invalid initial message format: missing 'method' field".to_string())
}

/// Parses a line of output from a backend process.
///
/// Expects the format `PIME_MSG|<client_id>|<payload>`.
/// Returns `Some((client_id, payload))` if valid.
pub fn parse_backend_output(line: &str) -> Option<(String, String)> {
    let rest = line.strip_prefix("PIME_MSG|")?;
    let sep = rest.find('|')?;
    Some((rest[..sep].to_string(), rest[sep + 1..].to_string()))
}

/// Formats a message to be sent to a backend process.
///
/// Format: <client_id>|<payload>
pub fn format_backend_input(client_id: &str, message: &str) -> String {
    format!("{}|{}", client_id, message)
}

/// Validates and parses a message to be sent to a backend process.
///
/// Expects `<client_id>|<payload>`, where `client_id` is exactly CLIENT_ID_LENGTH characters.
/// Returns `Some((client_id, payload))`.
pub fn parse_backend_input(data: &str) -> Option<(&str, &str)> {
    let (client_id, payload) = data.split_once('|')?;
    if client_id.len() != CLIENT_ID_LENGTH {
        return None;
    }
    Some((client_id, payload))
}

/// Extracts the `seqNum` field from a pure JSON payload (no `client_id|` prefix).
pub fn extract_seq_num(json_str: &str) -> Option<i64> {
    // Fast path: skip parsing messages that cannot contain a seqNum.
    if !json_str.contains("\"seqNum\"") {
        return None;
    }
    serde_json::from_str::<Value>(json_str)
        .ok()?
        .get("seqNum")?
        .as_i64()
}

#[cfg(test)]
mod tests {
    use super::*;

    /// The one committed request/reply set that every adapter's suite iterates;
    /// read from the checkout root relative to this crate.
    fn fixture() -> Value {
        let text = std::fs::read_to_string("../tests/wire-fixtures.json")
            .expect("tests/wire-fixtures.json must be committed");
        serde_json::from_str(&text).expect("the wire fixture must be valid JSON")
    }

    /// Fills the fixture's guid sentinels with the values this adapter sees.
    /// The launcher is a pass-through, so it reuses the python twin's guid.
    fn resolve(value: &Value, root: &Value) -> Value {
        match value {
            Value::String(text) => match text.as_str() {
                "$guid" => root["guid"]["python"].clone(),
                "$unknownGuid" => root["unknownGuid"].clone(),
                other => Value::String(other.to_string()),
            },
            Value::Array(items) => {
                Value::Array(items.iter().map(|item| resolve(item, root)).collect())
            }
            Value::Object(map) => Value::Object(
                map.iter()
                    .map(|(key, item)| (key.clone(), resolve(item, root)))
                    .collect(),
            ),
            other => other.clone(),
        }
    }

    #[test]
    fn test_wire_fixture_frames_round_trip() {
        let root = fixture();
        let client_id = root["clientId"].as_str().expect("clientId");
        let prefix = root["protocol"]["prefix"].as_str().expect("prefix");
        let cases = root["cases"].as_array().expect("cases");
        assert!(!cases.is_empty(), "the fixture must carry cases");

        for case in cases {
            let name = case["name"].as_str().expect("case name");
            for step in case["steps"].as_array().expect("steps") {
                // Request direction: one frame per line, split at the first '|'.
                let frame = match step.get("raw") {
                    Some(raw) => raw.as_str().expect("raw line").to_string(),
                    None => format_backend_input(client_id, &step["request"].to_string()),
                };
                match parse_backend_input(&frame) {
                    None => {
                        assert!(!frame.contains('|'), "{name}: {frame}");
                        assert!(step["reply"].is_null(), "{name}: reply for {frame}");
                        continue;
                    }
                    Some((id, payload)) => {
                        assert_eq!(id, client_id, "{name}: client id");
                        if let Some(request) = step.get("request") {
                            let expected = resolve(request, &root);
                            let decoded: Value = serde_json::from_str(payload)
                                .unwrap_or_else(|e| panic!("{name}: {e}"));
                            assert_eq!(decoded, expected, "{name}: request payload");
                            if expected["method"] == "init" {
                                let guid = expected["id"].as_str().expect("init id");
                                assert_eq!(
                                    parse_client_handshake(payload).ok().as_deref(),
                                    Some(guid),
                                    "{name}: handshake"
                                );
                            }
                        }
                    }
                }

                // Reply direction: the PIME_MSG prefix, then the same first-split rule.
                let reply = &step["reply"];
                if reply.is_null() {
                    continue;
                }
                let line = format!("{prefix}|{client_id}|{reply}");
                let (reply_id, reply_payload) =
                    parse_backend_output(&line).unwrap_or_else(|| panic!("{name}: {line}"));
                assert_eq!(reply_id, client_id, "{name}: reply client id");
                let decoded: Value =
                    serde_json::from_str(&reply_payload).unwrap_or_else(|e| panic!("{name}: {e}"));
                assert_eq!(&decoded, reply, "{name}: reply payload");
                match reply.get("seqNum") {
                    Some(seq_num) => assert_eq!(
                        extract_seq_num(&reply_payload),
                        seq_num.as_i64(),
                        "{name}: seqNum echo"
                    ),
                    None => assert_eq!(extract_seq_num(&reply_payload), None, "{name}: seqNum"),
                }
            }
        }
    }

    #[test]
    fn test_parse_client_handshake_invalid() {
        assert!(parse_client_handshake("not json").is_err());
        assert!(parse_client_handshake(r#"{"method": "unknown"}"#).is_err());
        assert!(parse_client_handshake(r#"{"method": "init"}"#).is_err()); // missing id
    }

    // The valid-frame forms of parse_backend_output / format_backend_input are
    // settled by test_wire_fixture_frames_round_trip; these are the forms the
    // fixture cannot express.
    #[test]
    fn test_parse_backend_output_invalid() {
        assert!(parse_backend_output("JUST_TEXT").is_none());
        assert!(parse_backend_output("PIME_MSG|incomplete").is_none());
    }

    #[test]
    fn test_extract_seq_num_with_pipe_in_payload() {
        assert_eq!(
            extract_seq_num(r#"{"commitString":"a|b","seqNum":7}"#),
            Some(7)
        );
        assert_eq!(extract_seq_num(r#"{"success":true}"#), None);
    }

    #[test]
    fn test_parse_backend_input() {
        let uuid = "12345678-1234-1234-1234-123456789012";

        // Missing pipe delimiter
        assert_eq!(parse_backend_input("no_delimiter"), None);

        // Empty client_id
        assert_eq!(parse_backend_input("|{\"method\":\"test\"}"), None);

        // Client ID not matching CLIENT_ID_LENGTH (36 chars)
        assert_eq!(parse_backend_input("short_id|{\"method\":\"test\"}"), None);
        let oversized = format!("{}extra|{{\"method\":\"test\"}}", uuid);
        assert_eq!(parse_backend_input(&oversized), None);
    }
}

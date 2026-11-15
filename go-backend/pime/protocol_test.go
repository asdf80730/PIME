package pime

import (
	"encoding/json"
	"os"
	"reflect"
	"strings"
	"testing"
)

// readWireFixture loads the one committed request/reply set that every
// adapter's suite iterates: tests/wire-fixtures.json, two directories up from
// this package (go test runs with the package directory as the working one).
func readWireFixture(t *testing.T) map[string]interface{} {
	t.Helper()

	raw, err := os.ReadFile("../../tests/wire-fixtures.json")
	if err != nil {
		t.Fatalf("read tests/wire-fixtures.json: %v", err)
	}
	var doc map[string]interface{}
	if err := json.Unmarshal(raw, &doc); err != nil {
		t.Fatalf("unmarshal wire fixture: %v", err)
	}
	return doc
}

// wireFold compares the `return` key across the backends: python and node
// write JSON booleans, this backend writes 1/0 for the same answer.
func wireFold(value interface{}) interface{} {
	if flag, ok := value.(bool); ok {
		if flag {
			return float64(1)
		}
		return float64(0)
	}
	return value
}

func wireSubset(t *testing.T, name string, expected map[string]interface{}, decoded map[string]interface{}) {
	t.Helper()

	for key, want := range expected {
		got, ok := decoded[key]
		if !ok {
			t.Fatalf("%s: reply lacks %q, got %#v", name, key, decoded)
		}
		if !reflect.DeepEqual(wireFold(got), wireFold(want)) {
			t.Fatalf("%s: %s = %#v, want %#v", name, key, got, want)
		}
	}
}

// resolveWireValue replaces the fixture's '$guid' and '$unknownGuid'
// placeholders with this adapter's own values, the same substitution the
// python and node suites apply, so a request frame is sent with the ids the
// dispatcher actually registers.
func resolveWireValue(value interface{}, guid, unknown string) interface{} {
	switch typed := value.(type) {
	case string:
		switch typed {
		case "$guid":
			return guid
		case "$unknownGuid":
			return unknown
		}
		return typed
	case map[string]interface{}:
		out := make(map[string]interface{}, len(typed))
		for key, item := range typed {
			out[key] = resolveWireValue(item, guid, unknown)
		}
		return out
	case []interface{}:
		out := make([]interface{}, 0, len(typed))
		for _, item := range typed {
			out = append(out, resolveWireValue(item, guid, unknown))
		}
		return out
	}
	return value
}

// TestWireFixturePinsFramingAndReplyKeys drives the shared fixture through the
// two functions this package owns: ParseRequest for the request keys and
// Response.ToJSON for the reply key names.
func TestWireFixturePinsFramingAndReplyKeys(t *testing.T) {
	doc := readWireFixture(t)

	protocol, _ := doc["protocol"].(map[string]interface{})
	if protocol["prefix"] != "PIME_MSG" || protocol["separator"] != "|" {
		t.Fatalf("unexpected framing constants: %#v", protocol)
	}
	if maxsplit, ok := protocol["maxsplit"].(float64); !ok || maxsplit != 1 {
		t.Fatalf("the request must split at the first separator only, got %#v", protocol["maxsplit"])
	}
	clientID, _ := doc["clientId"].(string)
	if clientID == "" {
		t.Fatal("fixture carries no clientId")
	}
	guids, _ := doc["guid"].(map[string]interface{})
	guid, _ := guids["go"].(string)
	unknown, _ := doc["unknownGuid"].(string)

	declared := map[string]bool{}
	for _, list := range []string{"replyKeys", "extraKeys"} {
		items, _ := doc[list].([]interface{})
		for _, item := range items {
			if key, ok := item.(string); ok {
				declared[key] = true
			}
		}
	}

	cases, _ := doc["cases"].([]interface{})
	if len(cases) == 0 {
		t.Fatal("the fixture carries no case")
	}
	for _, rawCase := range cases {
		fixtureCase, _ := rawCase.(map[string]interface{})
		name, _ := fixtureCase["name"].(string)
		steps, _ := fixtureCase["steps"].([]interface{})
		for _, rawStep := range steps {
			step, _ := rawStep.(map[string]interface{})

			if line, hasRaw := step["raw"].(string); hasRaw {
				parts := strings.SplitN(line, "|", 2)
				if len(parts) != 2 {
					if step["reply"] != nil {
						t.Fatalf("%s: a frame without a separator must still answer %#v", name, step["reply"])
					}
					continue
				}
				if parts[0] != clientID {
					t.Fatalf("%s: client id %q, want %q", name, parts[0], clientID)
				}
				if _, err := ParseRequest([]byte(parts[1])); err == nil {
					t.Fatalf("%s: %q must not parse as a request", name, parts[1])
				}
			} else if raw, hasRequest := step["request"].(map[string]interface{}); hasRequest {
				request, _ := resolveWireValue(raw, guid, unknown).(map[string]interface{})
				data, err := json.Marshal(request)
				if err != nil {
					t.Fatalf("%s: marshal request: %v", name, err)
				}
				req, err := ParseRequest(data)
				if err != nil {
					t.Fatalf("%s: ParseRequest: %v", name, err)
				}
				method, _ := request["method"].(string)
				if req.Method != method {
					t.Fatalf("%s: method %q, want %q", name, req.Method, method)
				}
				if seqNum, ok := request["seqNum"].(float64); ok && float64(req.SeqNum) != seqNum {
					t.Fatalf("%s: seqNum %d, want %v", name, req.SeqNum, seqNum)
				}
				switch method {
				case "init":
					want := guid
					if id, _ := request["id"].(string); id == unknown {
						want = unknown
					}
					if got := req.ID.StringValue(); got != want {
						t.Fatalf("%s: init id %q, want %q", name, got, want)
					}
				case "onCommand", "onMenu":
					if id, ok := request["id"].(string); ok && req.ID.StringValue() != id {
						t.Fatalf("%s: id %q, want %q", name, req.ID.StringValue(), id)
					}
				}
			}

			expected, hasReply := step["reply"].(map[string]interface{})
			if !hasReply {
				continue
			}
			data, err := json.Marshal(expected)
			if err != nil {
				t.Fatalf("%s: marshal reply: %v", name, err)
			}
			var resp Response
			if err := json.Unmarshal(data, &resp); err != nil {
				t.Fatalf("%s: unmarshal reply: %v", name, err)
			}
			out, err := resp.ToJSON()
			if err != nil {
				t.Fatalf("%s: ToJSON: %v", name, err)
			}
			var decoded map[string]interface{}
			if err := json.Unmarshal(out, &decoded); err != nil {
				t.Fatalf("%s: unmarshal serialized reply: %v", name, err)
			}
			wireSubset(t, name, expected, decoded)
			for key := range decoded {
				if !declared[key] {
					t.Fatalf("%s: %s is not a declared reply key", name, key)
				}
			}
		}
	}
}

func TestResponseJSONIncludesClearedCompositionState(t *testing.T) {
	resp := NewResponse(1, true)
	resp.ReturnValue = 1

	payload, err := resp.ToJSON()
	if err != nil {
		t.Fatalf("ToJSON failed: %v", err)
	}

	var decoded map[string]interface{}
	if err := json.Unmarshal(payload, &decoded); err != nil {
		t.Fatalf("unmarshal response failed: %v", err)
	}

	if value, ok := decoded["compositionString"]; !ok || value != "" {
		t.Fatalf("expected empty compositionString to be serialized, got %#v", decoded["compositionString"])
	}
	if value, ok := decoded["showCandidates"]; !ok || value.(bool) {
		t.Fatalf("expected showCandidates=false to be serialized, got %#v", decoded["showCandidates"])
	}
	if value, ok := decoded["candidateList"]; !ok {
		t.Fatalf("expected candidateList to be serialized, got %#v", decoded)
	} else if list, ok := value.([]interface{}); !ok || len(list) != 0 {
		t.Fatalf("expected empty candidateList, got %#v", value)
	}
}

func TestParseRequestAcceptsNumericKeyStates(t *testing.T) {
	req, err := ParseRequest([]byte(`{
		"method": "onKeyDown",
		"seqNum": 1,
		"keyStates": [0, 1, 0, 2]
	}`))
	if err != nil {
		t.Fatalf("ParseRequest returned error: %v", err)
	}

	want := []int{0, 1, 0, 2}
	if len(req.KeyStates) != len(want) {
		t.Fatalf("expected %d key states, got %d", len(want), len(req.KeyStates))
	}
	for i, expected := range want {
		if req.KeyStates[i] != expected {
			t.Fatalf("expected keyStates[%d]=%d, got %d", i, expected, req.KeyStates[i])
		}
	}
}

func TestParseRequestAcceptsBooleanKeyStates(t *testing.T) {
	req, err := ParseRequest([]byte(`{
		"method": "onKeyDown",
		"seqNum": 1,
		"keyStates": [true, false, true]
	}`))
	if err != nil {
		t.Fatalf("ParseRequest returned error: %v", err)
	}

	want := []int{1, 0, 1}
	if len(req.KeyStates) != len(want) {
		t.Fatalf("expected %d key states, got %d", len(want), len(req.KeyStates))
	}
	for i, expected := range want {
		if req.KeyStates[i] != expected {
			t.Fatalf("expected keyStates[%d]=%d, got %d", i, expected, req.KeyStates[i])
		}
	}
}

func TestParseRequestAcceptsStringAndNumericID(t *testing.T) {
	stringReq, err := ParseRequest([]byte(`{"method":"init","seqNum":1,"id":"{guid}"}`))
	if err != nil {
		t.Fatalf("ParseRequest returned error for string id: %v", err)
	}
	if got := stringReq.ID.StringValue(); got != "{guid}" {
		t.Fatalf("expected string id {guid}, got %q", got)
	}

	numericReq, err := ParseRequest([]byte(`{"method":"onCommand","seqNum":2,"id":3}`))
	if err != nil {
		t.Fatalf("ParseRequest returned error for numeric id: %v", err)
	}
	if got := numericReq.ID.IntValue(); got != 3 {
		t.Fatalf("expected numeric id 3, got %d", got)
	}
}

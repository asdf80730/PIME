package main

import (
	"encoding/json"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"

	"github.com/EasyIME/pime-go/pime"
)

// #481: 中州韻 registers a second TSF language profile for the other Windows
// input locale, and that profile activates with its own GUID. The loader has to
// know it, or the init request from that profile answers 未知的输入法.
func TestAdditionalProfileGuidsFromShippedRimeManifest(t *testing.T) {
	data, err := os.ReadFile(filepath.Join("input_methods", "rime", "ime.json"))
	if err != nil {
		t.Fatalf("read the shipped rime manifest: %v", err)
	}
	var imeConfig map[string]interface{}
	if err := json.Unmarshal(data, &imeConfig); err != nil {
		t.Fatalf("parse the shipped rime manifest: %v", err)
	}

	got := additionalProfileGuids(imeConfig)
	want := []string{"{9882e350-9462-4d42-9882-7847044ea725}"}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("additionalProfileGuids() = %v, want %v", got, want)
	}

	// The additional profile is a second bucket, not a rename of the first:
	// both must resolve, and they must differ.
	primary, _ := imeConfig["guid"].(string)
	primary = strings.ToLower(primary)
	if primary == got[0] {
		t.Fatalf("the additional profile reuses the primary guid %s", primary)
	}
	if primary != "{3f6b5a12-8d44-4e71-9a2e-6b4f9c1d2a30}" {
		t.Fatalf("primary guid = %s, want {3f6b5a12-8d44-4e71-9a2e-6b4f9c1d2a30}", primary)
	}
}

func TestAdditionalProfileGuidsSkipsBadEntries(t *testing.T) {
	imeConfig := map[string]interface{}{
		"additionalProfiles": []interface{}{
			map[string]interface{}{"guid": "{AAAA0000-0000-0000-0000-000000000001}"},
			map[string]interface{}{"locale": "zh-CN"},
			"not-an-object",
			map[string]interface{}{"guid": 7},
		},
	}
	got := additionalProfileGuids(imeConfig)
	want := []string{"{aaaa0000-0000-0000-0000-000000000001}"}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("additionalProfileGuids() = %v, want %v", got, want)
	}

	if got := additionalProfileGuids(map[string]interface{}{}); len(got) != 0 {
		t.Fatalf("a manifest without additionalProfiles must give no extra guid, got %v", got)
	}
}

func TestConvertResponseIncludesClearedCompositionState(t *testing.T) {
	server := NewServer()
	resp := pime.NewResponse(1, true)
	resp.ReturnValue = 1

	got := server.convertResponse(resp)

	if value, ok := got["compositionString"]; !ok || value != "" {
		t.Fatalf("expected empty compositionString, got %#v", got["compositionString"])
	}
	if value, ok := got["candidateList"]; !ok {
		t.Fatalf("expected candidateList in response, got %#v", got)
	} else if list, ok := value.([]string); !ok || len(list) != 0 {
		t.Fatalf("expected empty candidateList, got %#v", value)
	}
	if value, ok := got["showCandidates"]; !ok || value.(bool) {
		t.Fatalf("expected showCandidates=false, got %#v", got["showCandidates"])
	}
	if value, ok := got["selStart"]; !ok || value.(int) != 0 {
		t.Fatalf("expected selStart=0, got %#v", got["selStart"])
	}
	if value, ok := got["selEnd"]; !ok || value.(int) != 0 {
		t.Fatalf("expected selEnd=0, got %#v", got["selEnd"])
	}
}

func TestConvertResponseUsesReturnDataWhenPresent(t *testing.T) {
	server := NewServer()
	resp := pime.NewResponse(2, true)
	resp.ReturnValue = 1
	resp.ReturnData = []map[string]interface{}{
		{"id": 1, "text": "中文 → 西文"},
	}

	got := server.convertResponse(resp)

	items, ok := got["return"].([]map[string]interface{})
	if !ok || len(items) != 1 {
		t.Fatalf("expected menu return data, got %#v", got["return"])
	}
}

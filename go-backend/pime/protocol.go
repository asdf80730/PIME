// PIME 通信协议定义
package pime

import (
	"encoding/json"
	"fmt"
)

// 消息类型
const (
	MsgPIME = "PIME_MSG"
)

type FlexibleID struct {
	String string
	Int    int
	IsInt  bool
}

type KeyStates []int

func (k *KeyStates) UnmarshalJSON(data []byte) error {
	var bools []bool
	if err := json.Unmarshal(data, &bools); err == nil {
		states := make(KeyStates, len(bools))
		for i, v := range bools {
			if v {
				states[i] = 1
			}
		}
		*k = states
		return nil
	}

	var ints []int
	if err := json.Unmarshal(data, &ints); err == nil {
		states := make(KeyStates, len(ints))
		copy(states, ints)
		*k = states
		return nil
	}

	return fmt.Errorf("invalid keyStates payload: %s", string(data))
}

func (k KeyStates) IsKeyDown(code int) bool {
	return code >= 0 && code < len(k) && (k[code]&(1<<7)) != 0
}

func (k KeyStates) IsKeyToggled(code int) bool {
	return code >= 0 && code < len(k) && (k[code]&1) != 0
}

func (id FlexibleID) StringValue() string {
	if id.IsInt {
		return ""
	}
	return id.String
}

func (id FlexibleID) IntValue() int {
	if id.IsInt {
		return id.Int
	}
	return 0
}

// Request PIME请求结构
type Request struct {
	Method            string     `json:"method"`
	SeqNum            int        `json:"seqNum"`
	ID                FlexibleID `json:"-"`
	IsWindows8Above   bool       `json:"isWindows8Above,omitempty"`
	IsMetroApp        bool       `json:"isMetroApp,omitempty"`
	IsUiLess          bool       `json:"isUiLess,omitempty"`
	IsConsole         bool       `json:"isConsole,omitempty"`
	IsKeyboardOpen    bool       `json:"isKeyboardOpen,omitempty"`
	Opened            bool       `json:"opened,omitempty"`
	Forced            bool       `json:"forced,omitempty"`
	CommandType       int        `json:"type,omitempty"`
	CharCode          int        `json:"charCode,omitempty"`
	KeyCode           int        `json:"keyCode,omitempty"`
	RepeatCount       int        `json:"repeatCount,omitempty"`
	ScanCode          int        `json:"scanCode,omitempty"`
	IsExtended        bool       `json:"isExtended,omitempty"`
	KeyStates         KeyStates  `json:"keyStates,omitempty"`
	CompositionString string     `json:"compositionString,omitempty"`
	CandidateList     []string   `json:"candidateList,omitempty"`
	ShowCandidates    bool       `json:"showCandidates,omitempty"`
	CursorPos         int        `json:"cursorPos,omitempty"`
	SelStart          int        `json:"selStart,omitempty"`
	SelEnd            int        `json:"selEnd,omitempty"`
	// 扩展字段
	Data map[string]interface{} `json:"data,omitempty"`
}

func (r *Request) UnmarshalJSON(data []byte) error {
	type Alias Request
	aux := &struct {
		ID json.RawMessage `json:"id,omitempty"`
		*Alias
	}{
		Alias: (*Alias)(r),
	}
	if err := json.Unmarshal(data, aux); err != nil {
		return err
	}
	if len(aux.ID) == 0 {
		return nil
	}

	var s string
	if err := json.Unmarshal(aux.ID, &s); err == nil {
		r.ID = FlexibleID{String: s}
		return nil
	}

	var n int
	if err := json.Unmarshal(aux.ID, &n); err == nil {
		r.ID = FlexibleID{Int: n, IsInt: true}
		return nil
	}

	return fmt.Errorf("invalid id payload: %s", string(aux.ID))
}

// ButtonInfo 按钮信息
type ButtonInfo struct {
	ID        string `json:"id"`
	Icon      string `json:"icon,omitempty"`
	Text      string `json:"text,omitempty"`
	Tooltip   string `json:"tooltip,omitempty"`
	CommandID int    `json:"commandId,omitempty"`
	Type      string `json:"type,omitempty"` // "button", "toggle", "menu"
	Enable    bool   `json:"enable,omitempty"`
	Toggled   bool   `json:"toggled,omitempty"`
}

// Response PIME响应结构
type Response struct {
	SeqNum            int                    `json:"seqNum"`
	Success           bool                   `json:"success"`
	ReturnValue       int                    `json:"returnValue,omitempty"`
	// "return" is the wire key the C++ client reads; a method either fills
	// ReturnData (the menu and list answers) or leaves the folded ReturnValue.
	ReturnData        interface{}            `json:"return,omitempty"`
	CompositionString string                 `json:"compositionString"`
	CommitString      string                 `json:"commitString,omitempty"`
	CandidateList     []string               `json:"candidateList"`
	ShowCandidates    bool                   `json:"showCandidates"`
	CursorPos         int                    `json:"cursorPos"`
	CompositionCursor int                    `json:"compositionCursor"`
	CandidateCursor   int                    `json:"candidateCursor"`
	SelStart          int                    `json:"selStart"`
	SelEnd            int                    `json:"selEnd"`
	SetSelKeys        string                 `json:"setSelKeys,omitempty"`
	Message           string                 `json:"message,omitempty"`
	CustomizeUI       map[string]interface{} `json:"customizeUI,omitempty"`
	// 按钮相关
	AddButton    []ButtonInfo `json:"addButton,omitempty"`
	RemoveButton []string     `json:"removeButton,omitempty"`
	ChangeButton []ButtonInfo `json:"changeButton,omitempty"`
}

// ParseRequest 解析请求消息
func ParseRequest(data []byte) (*Request, error) {
	var req Request
	if err := json.Unmarshal(data, &req); err != nil {
		return nil, fmt.Errorf("unmarshal request failed: %w", err)
	}
	return &req, nil
}

// WireMap is the reply shape the C++ client reads (PIMETextService/PIMEClient.cpp
// reads "return" for the eaten/not-eaten answer, plus the composition and
// candidate keys). One shape for both servers: the shipped backend builds its
// line through it, and the pime-package server serializes it in ToJSON.
// "return" carries ReturnData when the method filled one, otherwise the folded
// ReturnValue, which is how the go backend answers the same key python and node
// write as a boolean.
func (r *Response) WireMap() map[string]interface{} {
	candidateList := r.CandidateList
	if candidateList == nil {
		candidateList = []string{}
	}
	m := map[string]interface{}{
		"success":           r.Success,
		"seqNum":            r.SeqNum,
		"cursorPos":         r.CursorPos,
		"compositionCursor": r.CompositionCursor,
		"candidateCursor":   r.CandidateCursor,
		"showCandidates":    r.ShowCandidates,
		"compositionString": r.CompositionString,
		"candidateList":     candidateList,
		"selStart":          r.SelStart,
		"selEnd":            r.SelEnd,
	}
	if r.ReturnData != nil {
		m["return"] = r.ReturnData
	} else {
		m["return"] = r.ReturnValue
	}
	if r.CommitString != "" {
		m["commitString"] = r.CommitString
	}
	if r.SetSelKeys != "" {
		m["setSelKeys"] = r.SetSelKeys
	}
	if len(r.CustomizeUI) > 0 {
		m["customizeUI"] = r.CustomizeUI
	}
	if len(r.AddButton) > 0 {
		m["addButton"] = r.AddButton
	}
	if len(r.RemoveButton) > 0 {
		m["removeButton"] = r.RemoveButton
	}
	if len(r.ChangeButton) > 0 {
		m["changeButton"] = r.ChangeButton
	}
	return m
}

// ToJSON 转换为 JSON 字节（與 WireMap 同一個線上形制）
func (r *Response) ToJSON() ([]byte, error) {
	return json.Marshal(r.WireMap())
}

// NewResponse 创建新响应
func NewResponse(seqNum int, success bool) *Response {
	return &Response{
		SeqNum:            seqNum,
		Success:           success,
		CandidateList:     []string{},
		CompositionString: "",
	}
}

package service

import (
	"context"
	"github.com/teamgram/proto/mtproto"
	"testing"
)

func TestAccountConfirmBotConnectionReturnsUnsupported(t *testing.T) {
	result, err := (&Service{}).AccountConfirmBotConnection(context.Background(), &mtproto.TLAccountConfirmBotConnection{})
	if result != nil || err != mtproto.ErrMethodNotImpl {
		t.Fatalf("result=%v error=%v", result, err)
	}
}

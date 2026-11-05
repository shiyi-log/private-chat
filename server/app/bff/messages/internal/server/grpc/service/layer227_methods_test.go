package service

import (
	"context"
	"github.com/teamgram/proto/mtproto"
	"testing"
)

func TestMessagesGetRichMessageReturnsUnsupported(t *testing.T) {
	result, err := (&Service{}).MessagesGetRichMessage(context.Background(), &mtproto.TLMessagesGetRichMessage{})
	if result != nil || err != mtproto.ErrMethodNotImpl {
		t.Fatalf("result=%v error=%v", result, err)
	}
}

package service

import (
	"context"
	"github.com/teamgram/proto/mtproto"
	"testing"
)

func TestInviteVersionsPreserveInputValidation(t *testing.T) {
	for _, tc := range []struct {
		hash string
		want error
	}{
		{"", mtproto.ErrInviteHashEmpty}, {"invalid", mtproto.ErrInviteHashInvalid},
	} {
		service := &Service{}
		old, oldErr := service.MessagesImportChatInvite6C50051C(context.Background(), &mtproto.TLMessagesImportChatInvite6C50051C{Hash: tc.hash})
		latest, latestErr := service.MessagesImportChatInviteDE91436E(context.Background(), &mtproto.TLMessagesImportChatInviteDE91436E{Hash: tc.hash})
		if old != nil || latest != nil || oldErr != tc.want || latestErr != tc.want {
			t.Fatalf("hash=%q old=%v/%v latest=%v/%v", tc.hash, old, oldErr, latest, latestErr)
		}
	}
}

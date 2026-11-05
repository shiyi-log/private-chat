package service

import (
	"context"
	"github.com/teamgram/proto/mtproto"
)

// MessagesGetRichMessage is outside the server's implemented feature set.
func (s *Service) MessagesGetRichMessage(ctx context.Context, request *mtproto.TLMessagesGetRichMessage) (*mtproto.Messages_Messages, error) {
	return nil, mtproto.ErrMethodNotImpl
}

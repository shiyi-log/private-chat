package service

import (
	"context"
	"github.com/teamgram/proto/mtproto"
)

// AccountConfirmBotConnection is outside the server's implemented feature set.
func (s *Service) AccountConfirmBotConnection(ctx context.Context, request *mtproto.TLAccountConfirmBotConnection) (*mtproto.Bool, error) {
	return nil, mtproto.ErrMethodNotImpl
}

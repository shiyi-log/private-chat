package service

import (
	"context"
	"github.com/teamgram/proto/mtproto"
)

// MessagesImportChatInviteDE91436E wraps the existing join behavior in layer 227's response.
func (s *Service) MessagesImportChatInviteDE91436E(ctx context.Context, request *mtproto.TLMessagesImportChatInviteDE91436E) (*mtproto.Messages_ChatInviteJoinResult, error) {
	updates, err := s.MessagesImportChatInvite6C50051C(ctx, &mtproto.TLMessagesImportChatInvite6C50051C{
		Constructor: mtproto.CRC32_messages_importChatInvite6C50051C,
		Hash:        request.GetHash(),
	})
	if err != nil {
		return nil, err
	}
	return mtproto.MakeTLMessagesChatInviteJoinResultOk(&mtproto.Messages_ChatInviteJoinResult{Updates: updates}).To_Messages_ChatInviteJoinResult(), nil
}

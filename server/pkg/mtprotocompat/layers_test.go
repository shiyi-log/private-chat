package mtprotocompat_test

import (
	"encoding/binary"
	"encoding/json"
	"fmt"
	"os"
	"testing"

	"github.com/teamgram/proto/mtproto"
)

// These wire IDs come from the schemas used by the three local clients.
// Layer 224 is the protocol smoke, 225 Android, and 227 Desktop and iOS.
func TestLocalClientLayersEncodeCoreResponses(t *testing.T) {
	data, err := os.ReadFile("../../teamgramd/bin/config.json")
	if err != nil {
		t.Fatal(err)
	}
	var config mtproto.TLConfig
	if err := json.Unmarshal(data, &config); err != nil {
		t.Fatal(err)
	}
	user := mtproto.MakeTLUserEmpty(nil)
	user.SetId(100001)
	sms := mtproto.MakeTLAuthSentCodeTypeSms(nil)
	sms.SetLength(5)
	sent := mtproto.MakeTLAuthSentCode(nil)
	sent.SetType(sms.To_Auth_SentCodeType())
	sent.SetPhoneCodeHash("offline-layer-test")
	auth := mtproto.MakeTLAuthAuthorization(nil)
	auth.SetUser(user.To_User())
	peer := mtproto.MakeTLPeerUser(nil)
	peer.SetUserId(100001)
	message := mtproto.MakeTLMessage(nil)
	message.SetId(1)
	message.SetPeerId(peer.To_Peer())
	message.SetDate(1)
	message.SetMessage("offline-layer-test")
	history := mtproto.MakeTLMessagesMessages(nil)
	history.SetMessages([]*mtproto.Message{message.To_Message()})
	history.SetUsers([]*mtproto.User{user.To_User()})

	for _, layer := range []int32{224, 225, 227} {
		messageID := map[int32]uint32{224: 0x3ae56482, 225: 0x95ef6f2b, 227: 0x7600b9d3}[layer]
		cases := []struct {
			name        string
			object      mtproto.TLObject
			constructor uint32
		}{
			{"config", &config, 0xcc1a241e},
			{"auth.sentCode", sent, 0x5e002502},
			{"auth.sentCodeTypeSms", sms, 0xc000bba2},
			{"auth.authorization", auth, 0x2ea2c0d4},
			{"userEmpty", user, 0xd3bc4b7a},
			{"message", message, messageID},
			{"messages.messages", history, 0x1d73e7ea},
			{"updates", mtproto.MakeTLUpdates(nil), 0x74ae4240},
			{"updateShortSentMessage", mtproto.MakeTLUpdateShortSentMessage(nil), 0x9015e101},
		}
		for _, tc := range cases {
			t.Run(fmt.Sprintf("layer%d/%s", layer, tc.name), func(t *testing.T) {
				buffer := mtproto.GetEncodeBuf()
				defer mtproto.PutEncodeBuf(buffer)
				if err := tc.object.Encode(buffer, layer); err != nil {
					t.Fatalf("encode: %v", err)
				}
				wire := buffer.GetBuf()
				if len(wire) < 4 {
					t.Fatalf("encoded only %d bytes", len(wire))
				}
				if got := binary.LittleEndian.Uint32(wire[:4]); got != tc.constructor {
					t.Fatalf("constructor = %#x, want %#x", got, tc.constructor)
				}
				decoded := mtproto.NewDecodeBuf(wire)
				if object := decoded.Object(); object == nil || decoded.GetError() != nil {
					t.Fatalf("decode: object=%T error=%v", object, decoded.GetError())
				}
				if decoded.GetOffset() != len(wire) {
					t.Fatalf("decode consumed %d of %d bytes", decoded.GetOffset(), len(wire))
				}
				rpc := mtproto.GetEncodeBuf()
				defer mtproto.PutEncodeBuf(rpc)
				if err := (&mtproto.TLRpcResult{ReqMsgId: 1, Result: tc.object}).Encode(rpc, layer); err != nil {
					t.Fatalf("rpc_result encode: %v", err)
				}
				if rpc.GetOffset() <= 12 {
					t.Fatalf("rpc_result contains no result payload (%d bytes)", rpc.GetOffset())
				}
			})
		}
	}
}

// sendMessage changed constructor between Android's schema and Desktop/iOS.
// Request bytes are assembled independently of the generated request encoder.
func TestLocalClientSendMessageWireRequests(t *testing.T) {
	for _, tc := range []struct {
		layer       int32
		constructor uint32
	}{
		{224, 0x545cd15a}, {225, 0x545cd15a}, {227, 0xfef48f62},
	} {
		t.Run(fmt.Sprintf("layer%d", tc.layer), func(t *testing.T) {
			wire := mtproto.GetEncodeBuf()
			defer mtproto.PutEncodeBuf(wire)
			wire.UInt(tc.constructor)
			wire.Int(0)           // flags
			wire.UInt(0x7da07ec9) // inputPeerSelf
			wire.String("native-schema-wire-test")
			wire.Long(987654321)
			decoded := mtproto.NewDecodeBuf(wire.GetBuf())
			request, ok := decoded.Object().(*mtproto.TLMessagesSendMessage)
			if !ok || decoded.GetError() != nil {
				t.Fatalf("decode request: request=%T error=%v", request, decoded.GetError())
			}
			if request.GetMessage() != "native-schema-wire-test" || request.GetRandomId() != 987654321 {
				t.Fatalf("request fields changed: %v", request)
			}
			if decoded.GetOffset() != wire.GetOffset() {
				t.Fatalf("decode consumed %d of %d bytes", decoded.GetOffset(), wire.GetOffset())
			}
		})
	}
}

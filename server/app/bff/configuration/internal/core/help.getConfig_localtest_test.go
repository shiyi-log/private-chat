//go:build privatechat_localtest

package core

import (
	"context"
	"encoding/binary"
	"fmt"
	"testing"

	"github.com/teamgram/proto/mtproto"
	"github.com/teamgram/teamgram-server/app/bff/configuration/internal/svc"
	"google.golang.org/protobuf/proto"
)

// Omitting handler routing, reading Langpack instead of Client, or encoding the
// wrong native schema must all break the public response contract.
func TestHelpGetConfigLocalEndpointsFromIncomingMetadata(t *testing.T) {
	t.Setenv("PRIVATECHAT_LOCALTEST", "1")
	for _, tc := range []struct {
		client, langpack, host string
	}{
		{"android", "ios", "10.0.2.2"},
		{"tdesktop", "android", "127.0.0.1"},
		{"ios", "ios", "127.0.0.1"},
		{"", "", "127.0.0.1"},
	} {
		for _, layer := range []int32{224, 225, 227} {
			t.Run(fmt.Sprintf("%s/layer%d", tc.client, layer), func(t *testing.T) {
				base := deploymentConfig()
				original := proto.Clone(base)
				response := getConfiguration(t, configurationRequest(t, base, tc.client, tc.langpack, layer))
				assertLocalEndpoint(t, response, tc.host)
				if !proto.Equal(base, original) {
					t.Fatal("local request mutated shared deployment config")
				}
				if response.GetChatSizeMax() != 200 || response.GetMessageLengthMax() != 4096 {
					t.Fatal("local routing changed unrelated deployment limits")
				}
				encoded := mtproto.GetEncodeBuf()
				defer mtproto.PutEncodeBuf(encoded)
				if err := mtproto.MakeTLConfig(response).Encode(encoded, layer); err != nil {
					t.Fatal(err)
				}
				wire := encoded.GetBuf()
				if len(wire) < 4 || binary.LittleEndian.Uint32(wire[:4]) != 0xcc1a241e {
					t.Fatal("wrong native Config constructor")
				}
				decoder := mtproto.NewDecodeBuf(wire)
				object := decoder.Object()
				decoded, ok := object.(*mtproto.TLConfig)
				if !ok || decoder.GetError() != nil || decoder.GetOffset() != len(wire) {
					t.Fatalf("decode type=%T error=%v consumed=%d/%d", object, decoder.GetError(), decoder.GetOffset(), len(wire))
				}
				assertLocalEndpoint(t, decoded.To_Config(), tc.host)
				rpc := mtproto.GetEncodeBuf()
				defer mtproto.PutEncodeBuf(rpc)
				if err := (&mtproto.TLRpcResult{ReqMsgId: 1, Result: mtproto.MakeTLConfig(response)}).Encode(rpc, layer); err != nil {
					t.Fatal(err)
				}
				if rpc.GetOffset() != len(wire)+12 {
					t.Fatalf("rpc_result payload bytes = %d, want %d", rpc.GetOffset()-12, len(wire))
				}
			})
		}
	}
}

func assertLocalEndpoint(t *testing.T, response *mtproto.Config, host string) {
	t.Helper()
	if response.GetThisDc() != 1 || response.GetWebfileDcId() != 1 || response.GetDcTxtDomainName() != "localhost" {
		t.Fatalf("nonlocal routing: %v", response)
	}
	if len(response.GetDcOptions()) != 1 {
		t.Fatalf("got %d DC options, want one reachable local DC", len(response.GetDcOptions()))
	}
	dc := response.GetDcOptions()[0]
	if dc.GetId() != 1 || dc.GetIpAddress() != host || dc.GetPort() != 10443 {
		t.Fatalf("endpoint = %v, want DC 1 %s:10443", dc, host)
	}
	if dc.GetIpv6() || dc.GetCdn() || dc.GetMediaOnly() || len(dc.GetSecret()) != 0 || !dc.GetThisPortOnly() {
		t.Fatalf("unexpected DC option flags: %v", dc)
	}
}

func TestHelpGetConfigLocalResponsesStayIndependent(t *testing.T) {
	t.Setenv("PRIVATECHAT_LOCALTEST", "1")
	base := deploymentConfig()
	original := proto.Clone(base)
	android := getConfiguration(t, configurationRequest(t, base, "android", "android", 225))
	host := getConfiguration(t, configurationRequest(t, base, "tdesktop", "tdesktop", 227))
	assertLocalEndpoint(t, android, "10.0.2.2")
	android.DcOptions[0].IpAddress = "changed.invalid"
	assertLocalEndpoint(t, host, "127.0.0.1")
	if !proto.Equal(base, original) {
		t.Fatal("request mutated deployment config")
	}
	withoutMetadata := getConfiguration(t, New(context.Background(), &svc.ServiceContext{ClientConfig: base}))
	assertLocalEndpoint(t, withoutMetadata, "127.0.0.1")
}

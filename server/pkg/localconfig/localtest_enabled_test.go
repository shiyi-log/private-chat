//go:build privatechat_localtest

package localconfig

import (
	"fmt"
	"testing"

	"github.com/teamgram/proto/mtproto"
	"google.golang.org/protobuf/proto"
)

func TestLocalConfigAdvertisesOnlyReachableClientDC(t *testing.T) {
	t.Setenv("PRIVATECHAT_LOCALTEST", "1")
	for _, tc := range []struct{ client, host string }{
		{"android", "10.0.2.2"}, {"tdesktop", "127.0.0.1"}, {"ios", "127.0.0.1"}, {"", "127.0.0.1"},
	} {
		for _, layer := range []int32{224, 225, 227} {
			t.Run(fmt.Sprintf("%s/layer%d", tc.client, layer), func(t *testing.T) {
				config := mtproto.MakeTLConfig(nil)
				config.SetTestMode(mtproto.ToBool(false))
				Apply(config, tc.client)
				options := config.GetDcOptions()
				if config.GetThisDc() != 1 || config.GetWebfileDcId() != 1 || config.GetDcTxtDomainName() != "localhost" {
					t.Fatalf("nonlocalDC config: %v", config)
				}
				if len(options) != 1 {
					t.Fatalf("got%d DC options, want1", len(options))
				}
				dc := options[0]
				if dc.GetId() != 1 || dc.GetIpAddress() != tc.host || dc.GetPort() != 10443 {
					t.Fatalf("endpoint=%v, wantDC1 %s:10443", dc, tc.host)
				}
				if dc.GetIpv6() || dc.GetCdn() || dc.GetMediaOnly() || len(dc.GetSecret()) != 0 || !dc.GetThisPortOnly() {
					t.Fatalf("unexpected DC flags: %v", dc)
				}
				encoded := mtproto.GetEncodeBuf()
				defer mtproto.PutEncodeBuf(encoded)
				if err := config.Encode(encoded, layer); err != nil {
					t.Fatal(err)
				}
				decoder := mtproto.NewDecodeBuf(encoded.GetBuf())
				decoded, ok := decoder.Object().(*mtproto.TLConfig)
				if !ok || decoder.GetError() != nil || decoder.GetOffset() != encoded.GetOffset() {
					t.Fatalf("decode=%T/%v consumed=%d bytes=%d", decoded, decoder.GetError(), decoder.GetOffset(), encoded.GetOffset())
				}
				if len(decoded.GetDcOptions()) != 1 || decoded.GetDcOptions()[0].GetIpAddress() != tc.host || decoded.GetWebfileDcId() != 1 {
					t.Fatalf("wire endpoint mismatch: %v", decoded)
				}
			})
		}
	}
}

func TestLocalConfigDisabledAndClientResponsesAreIndependent(t *testing.T) {
	base := mtproto.MakeTLConfig(&mtproto.Config{ThisDc: 9, WebfileDcId: 8, DcTxtDomainName: "deployment.example"})
	original := proto.Clone(base).(*mtproto.TLConfig)
	t.Setenv("PRIVATECHAT_LOCALTEST", "0")
	Apply(base, "android")
	if !proto.Equal(base, original) {
		t.Fatal("disabled mode changed deployment config")
	}
	t.Setenv("PRIVATECHAT_LOCALTEST", "1")
	android := proto.Clone(base).(*mtproto.TLConfig)
	desktop := proto.Clone(base).(*mtproto.TLConfig)
	Apply(android, "android")
	Apply(desktop, "tdesktop")
	if len(android.GetDcOptions()) != 1 || len(desktop.GetDcOptions()) != 1 {
		t.Fatal("missing independent client DC options")
	}
	android.GetDcOptions()[0].IpAddress = "changed.invalid"
	if desktop.GetDcOptions()[0].GetIpAddress() != "127.0.0.1" || !proto.Equal(base, original) {
		t.Fatal("response options shared across clients")
	}
}

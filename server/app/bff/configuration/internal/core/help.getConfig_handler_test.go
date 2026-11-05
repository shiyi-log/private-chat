package core

import (
	"context"
	"testing"
	"time"

	"github.com/teamgram/proto/mtproto"
	rpcmetadata "github.com/teamgram/proto/mtproto/rpc/metadata"
	"github.com/teamgram/teamgram-server/app/bff/configuration/internal/svc"
	grpcmetadata "google.golang.org/grpc/metadata"
	"google.golang.org/protobuf/proto"
)

func deploymentConfig() *mtproto.TLConfig {
	return mtproto.MakeTLConfig(&mtproto.Config{
		ThisDc: 9, WebfileDcId: 8, DcTxtDomainName: "deployment.example",
		TestMode: mtproto.ToBool(false), ChatSizeMax: 200, MessageLengthMax: 4096,
		Date: 1, Expires: 2,
		DcOptions: []*mtproto.DcOption{mtproto.MakeTLDcOption(&mtproto.DcOption{
			Id: 9, IpAddress: "192.0.2.9", Port: 443,
		}).To_DcOption()},
	})
}

func configurationRequest(t *testing.T, base *mtproto.TLConfig, client, langpack string, layer int32) *ConfigurationCore {
	t.Helper()
	outgoing, err := rpcmetadata.RpcMetadataToOutgoing(context.Background(), &rpcmetadata.RpcMetadata{
		Client: client, Langpack: langpack, Layer: layer,
	})
	if err != nil {
		t.Fatal(err)
	}
	headers, ok := grpcmetadata.FromOutgoingContext(outgoing)
	if !ok {
		t.Fatal("missing real RPC metadata")
	}
	incoming := grpcmetadata.NewIncomingContext(context.Background(), headers)
	return New(incoming, &svc.ServiceContext{ClientConfig: base})
}

func getConfiguration(t *testing.T, core *ConfigurationCore) *mtproto.Config {
	t.Helper()
	response, err := core.HelpGetConfig(&mtproto.TLHelpGetConfig{})
	if err != nil {
		t.Fatal(err)
	}
	if response == nil {
		t.Fatal("missing config response")
	}
	return response
}

// A request must refresh only its own time fields when local routing is disabled.
func TestHelpGetConfigPreservesDeploymentWhenLocalModeDisabled(t *testing.T) {
	for _, enabled := range []string{"", "0", "true", "01"} {
		t.Run("enabled="+enabled, func(t *testing.T) {
			t.Setenv("PRIVATECHAT_LOCALTEST", enabled)
			base := deploymentConfig()
			original := proto.Clone(base)
			before := int32(time.Now().Unix())
			response := getConfiguration(t, configurationRequest(t, base, "android", "ios", 225))
			if response.GetDate() < before || response.GetDate() > int32(time.Now().Unix()) {
				t.Fatalf("response date = %d, outside request interval", response.GetDate())
			}
			if response.GetExpires()-response.GetDate() != 3600 {
				t.Fatalf("expiry lifetime = %d, want 3600", response.GetExpires()-response.GetDate())
			}
			response.Date, response.Expires = 1, 2
			if !proto.Equal(response, base.To_Config()) {
				t.Fatal("disabled request changed deployment-owned config")
			}
			if !proto.Equal(base, original) {
				t.Fatal("request mutated shared deployment config")
			}
		})
	}
}

func TestHelpGetConfigClonesNestedDeploymentOptions(t *testing.T) {
	t.Setenv("PRIVATECHAT_LOCALTEST", "0")
	base := deploymentConfig()
	original := proto.Clone(base)
	first := getConfiguration(t, configurationRequest(t, base, "android", "android", 225))
	first.DcOptions[0].IpAddress = "changed.invalid"
	second := getConfiguration(t, configurationRequest(t, base, "tdesktop", "tdesktop", 227))
	if second.GetDcOptions()[0].GetIpAddress() != "192.0.2.9" || !proto.Equal(base, original) {
		t.Fatal("request mutated shared nested DC options")
	}
}

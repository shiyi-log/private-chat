//go:build !privatechat_localtest

package localconfig

import (
	"testing"

	"github.com/teamgram/proto/mtproto"
	"google.golang.org/protobuf/proto"
)

func TestProductionConfigRemainsDeploymentOwned(t *testing.T) {
	t.Setenv("PRIVATECHAT_LOCALTEST", "1")
	config := mtproto.MakeTLConfig(&mtproto.Config{ThisDc: 9, WebfileDcId: 8, DcTxtDomainName: "deployment.example"})
	expected := proto.Clone(config)
	Apply(config, "android")
	if !proto.Equal(config, expected) {
		t.Fatal("normal build changed config from localtest environment")
	}
}

//go:build !privatechat_localtest

package core

import (
	"testing"

	"google.golang.org/protobuf/proto"
)

func TestHelpGetConfigProductionIgnoresLocalRoutingEnvironment(t *testing.T) {
	t.Setenv("PRIVATECHAT_LOCALTEST", "1")
	base := deploymentConfig()
	response := getConfiguration(t, configurationRequest(t, base, "android", "android", 225))
	response.Date, response.Expires = 1, 2
	if !proto.Equal(response, base.To_Config()) {
		t.Fatal("production build changed deployment config for localtest environment")
	}
}

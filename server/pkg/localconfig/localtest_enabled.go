//go:build privatechat_localtest

// Package localconfig applies the isolated host/emulator routing contract.
package localconfig

import (
	"os"

	"github.com/teamgram/proto/mtproto"
)

// Apply changes only a request's cloned response in the explicitly enabled
// local stack. Android's emulator reaches its host through 10.0.2.2; native
// host clients and iOS Simulator reach it through 127.0.0.1.
func Apply(config *mtproto.TLConfig, client string) {
	if os.Getenv("PRIVATECHAT_LOCALTEST") != "1" {
		return
	}
	host := "127.0.0.1"
	if client == "android" {
		host = "10.0.2.2"
	}
	option := mtproto.MakeTLDcOption(&mtproto.DcOption{
		Id: 1, IpAddress: host, Port: 10443, ThisPortOnly: true,
	}).To_DcOption()
	config.SetThisDc(1)
	config.SetDcOptions([]*mtproto.DcOption{option})
	config.SetWebfileDcId(1)
	config.SetDcTxtDomainName("localhost")
}

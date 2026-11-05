//go:build !privatechat_localtest

package localconfig

import "github.com/teamgram/proto/mtproto"

// Apply preserves the deployment config in normal production builds.
func Apply(config *mtproto.TLConfig, client string) {}

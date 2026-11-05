//go:build !privatechat_localtest

package code

import (
	"github.com/teamgram/teamgram-server/pkg/code/conf"
	"github.com/teamgram/teamgram-server/pkg/code/none"
)

// Production builds never include the local outbox verifier.
func newLocalTestVerifyCode(c *conf.SmsVerifyCodeConfig) VerifyCodeInterface {
	return none.New(c)
}

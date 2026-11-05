//go:build !privatechat_localtest

package code

import (
	"context"
	"testing"

	"github.com/teamgram/teamgram-server/pkg/code/conf"
)

func TestProductionBuildRejectsLocalTestProviderEvenWithEnvironmentGate(t *testing.T) {
	t.Setenv("PRIVATECHAT_LOCALTEST", "1")
	t.Setenv("PRIVATECHAT_LOCALTEST_PHONES", "12025550101")
	t.Setenv("PRIVATECHAT_LOCALTEST_OUTBOX", t.TempDir())
	verifier := NewVerifyCode(&conf.SmsVerifyCodeConfig{Name: "localtest"})
	if out, err := verifier.SendSmsVerifyCode(context.Background(), "12025550101", "54321", "hash-production"); err == nil || out != "" {
		t.Fatalf("production build enabled localtest: out=%q, err=%v", out, err)
	}
	if err := verifier.VerifySmsCode(context.Background(), "hash-production", "54321", "54321"); err == nil {
		t.Fatal("production build accepted a test OTP")
	}
}

package none

import (
	"context"
	"testing"

	"github.com/teamgram/proto/mtproto"
	"github.com/teamgram/teamgram-server/pkg/code/conf"
)

func TestDisabledSmsVerifierDoesNotExposeOrAcceptCodes(t *testing.T) {
	verifier := New(&conf.SmsVerifyCodeConfig{})

	code, err := verifier.SendSmsVerifyCode(context.Background(), "+15551234567", "12345", "test-hash")
	if err == nil {
		t.Fatal("expected disabled SMS provider to reject sending a code")
	}
	if code != "" {
		t.Fatalf("disabled SMS provider exposed a code: %q", code)
	}

	if err := verifier.VerifySmsCode(context.Background(), "test-hash", "12345", ""); err != mtproto.ErrPhoneCodeInvalid {
		t.Fatalf("expected fixed test code to be rejected, got %v", err)
	}
}

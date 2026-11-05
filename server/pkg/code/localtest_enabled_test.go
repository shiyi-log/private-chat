//go:build privatechat_localtest

package code

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/teamgram/teamgram-server/pkg/code/conf"
)

type localTestDelivery struct {
	PhoneNumber string `json:"phone_number"`
	CodeHash    string `json:"code_hash"`
	Code        string `json:"code"`
	Binding     string `json:"binding"`
	ExpiresAt   int64  `json:"expires_at"`
}

func localTestDeliveryPath(outbox, codeHash string) string {
	digest := sha256.Sum256([]byte(codeHash))
	return filepath.Join(outbox, hex.EncodeToString(digest[:])+".json")
}

func configureLocalTestVerifier(t *testing.T, phones string) (VerifyCodeInterface, string) {
	t.Helper()
	outbox := t.TempDir()
	t.Setenv("PRIVATECHAT_LOCALTEST", "1")
	t.Setenv("PRIVATECHAT_LOCALTEST_PHONES", phones)
	t.Setenv("PRIVATECHAT_LOCALTEST_OUTBOX", outbox)
	return NewVerifyCode(&conf.SmsVerifyCodeConfig{Name: "localtest"}), outbox
}

func readLocalTestDelivery(t *testing.T, outbox, codeHash string) localTestDelivery {
	t.Helper()
	name := localTestDeliveryPath(outbox, codeHash)
	data, err := os.ReadFile(name)
	if err != nil {
		t.Fatalf("read local OTP delivery: %v", err)
	}
	var record localTestDelivery
	if err := json.Unmarshal(data, &record); err != nil {
		t.Fatalf("decode local OTP delivery: %v", err)
	}
	return record
}

func TestLocalTestVerifierDeliversPerTransactionCodeAndVerifiesBinding(t *testing.T) {
	verifier, outbox := configureLocalTestVerifier(t, "12025550101,12025550102")

	firstBinding, err := verifier.SendSmsVerifyCode(context.Background(), "12025550101", "54321", "hash-first")
	if err != nil {
		t.Fatalf("send allowed test number: %v", err)
	}
	secondBinding, err := verifier.SendSmsVerifyCode(context.Background(), "12025550102", "97531", "hash-second")
	if err != nil {
		t.Fatalf("send second allowed test number: %v", err)
	}
	if firstBinding == secondBinding {
		t.Fatal("expected transaction-specific bindings")
	}

	first := readLocalTestDelivery(t, outbox, "hash-first")
	second := readLocalTestDelivery(t, outbox, "hash-second")
	if first.Code != "54321" || first.PhoneNumber != "12025550101" || first.CodeHash != "hash-first" {
		t.Fatalf("first outbox delivery = %+v", first)
	}
	if second.Code != "97531" || second.PhoneNumber != "12025550102" || second.CodeHash != "hash-second" {
		t.Fatalf("second outbox delivery = %+v", second)
	}
	if err := verifier.VerifySmsCode(context.Background(), "hash-first", first.Code, firstBinding); err != nil {
		t.Fatalf("verify matching OTP and binding: %v", err)
	}
}

func TestLocalTestVerifierRejectsDisallowedNumberAndMismatchedTransaction(t *testing.T) {
	verifier, outbox := configureLocalTestVerifier(t, "12025550101")
	if _, err := verifier.SendSmsVerifyCode(context.Background(), "12025550199", "54321", "hash-denied"); err == nil {
		t.Fatal("expected unlisted phone number to be rejected")
	}

	binding, err := verifier.SendSmsVerifyCode(context.Background(), "12025550101", "54321", "hash-allowed")
	if err != nil {
		t.Fatalf("send allowed number: %v", err)
	}
	record := readLocalTestDelivery(t, outbox, "hash-allowed")
	for _, attempt := range []struct {
		name, hash, code, binding string
	}{
		{name: "wrong hash", hash: "hash-other", code: record.Code, binding: binding},
		{name: "wrong code", hash: "hash-allowed", code: "00000", binding: binding},
		{name: "wrong binding", hash: "hash-allowed", code: record.Code, binding: "unbound"},
	} {
		t.Run(attempt.name, func(t *testing.T) {
			if err := verifier.VerifySmsCode(context.Background(), attempt.hash, attempt.code, attempt.binding); err == nil {
				t.Fatal("expected mismatched transaction to be rejected")
			}
		})
	}
	if _, err := os.Stat(localTestDeliveryPath(outbox, "hash-denied")); !errors.Is(err, os.ErrNotExist) {
		t.Fatalf("disallowed phone wrote an outbox file, stat error = %v", err)
	}
}

func TestLocalTestVerifierRejectsExpiredDelivery(t *testing.T) {
	verifier, outbox := configureLocalTestVerifier(t, "12025550101")
	binding, err := verifier.SendSmsVerifyCode(context.Background(), "12025550101", "54321", "hash-expired")
	if err != nil {
		t.Fatalf("send allowed number: %v", err)
	}
	record := readLocalTestDelivery(t, outbox, "hash-expired")
	record.ExpiresAt = time.Now().Add(-time.Second).Unix()
	data, err := json.Marshal(record)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(localTestDeliveryPath(outbox, "hash-expired"), data, 0o600); err != nil {
		t.Fatal(err)
	}
	if err := verifier.VerifySmsCode(context.Background(), "hash-expired", record.Code, binding); err == nil {
		t.Fatal("expected expired OTP to be rejected")
	}
}

func TestLocalTestVerifierRequiresExplicitEnvironmentGate(t *testing.T) {
	outbox := t.TempDir()
	t.Setenv("PRIVATECHAT_LOCALTEST", "0")
	t.Setenv("PRIVATECHAT_LOCALTEST_PHONES", "12025550101")
	t.Setenv("PRIVATECHAT_LOCALTEST_OUTBOX", outbox)
	verifier := NewVerifyCode(&conf.SmsVerifyCodeConfig{Name: "localtest"})
	if _, err := verifier.SendSmsVerifyCode(context.Background(), "12025550101", "54321", "hash-gated"); err == nil {
		t.Fatal("expected missing explicit gate to fail closed")
	}
}

func TestLocalTestOutboxIsPrivate(t *testing.T) {
	verifier, outbox := configureLocalTestVerifier(t, "12025550101")
	if _, err := verifier.SendSmsVerifyCode(context.Background(), "12025550101", "54321", "hash-private"); err != nil {
		t.Fatalf("send allowed number: %v", err)
	}
	info, err := os.Stat(outbox)
	if err != nil {
		t.Fatal(err)
	}
	if info.Mode().Perm()&0o077 != 0 {
		t.Fatalf("outbox permissions = %o, want no group/other access", info.Mode().Perm())
	}
	fileInfo, err := os.Stat(filepath.Clean(localTestDeliveryPath(outbox, "hash-private")))
	if err != nil {
		t.Fatal(err)
	}
	if fileInfo.Mode().Perm()&0o077 != 0 {
		t.Fatalf("delivery permissions = %o, want no group/other access", fileInfo.Mode().Perm())
	}
}

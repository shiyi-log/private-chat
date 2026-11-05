//go:build privatechat_localtest

package code

import (
	"context"
	"crypto/rand"
	"crypto/sha256"
	"crypto/subtle"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"time"

	"github.com/teamgram/proto/mtproto"
	"github.com/teamgram/teamgram-server/pkg/code/conf"
	"github.com/teamgram/teamgram-server/pkg/code/none"
)

// localTestVerifyCode is compiled only into explicitly tagged integration builds.
// It delivers the transaction's OTP to a private local outbox; it sends no SMS.
type localTestVerifyCode struct {
	phones map[string]bool
	outbox string
}

type localTestOTP struct {
	PhoneNumber string `json:"phone_number"`
	CodeHash    string `json:"code_hash"`
	Code        string `json:"code"`
	Binding     string `json:"binding"`
	ExpiresAt   int64  `json:"expires_at"`
}

var localTestPhonePattern = regexp.MustCompile(`^[0-9]{5,15}$`)
var localTestCodePattern = regexp.MustCompile(`^[0-9]{5}$`)

func newLocalTestVerifyCode(c *conf.SmsVerifyCodeConfig) VerifyCodeInterface {
	if os.Getenv("PRIVATECHAT_LOCALTEST") != "1" {
		return none.New(c)
	}
	outbox := os.Getenv("PRIVATECHAT_LOCALTEST_OUTBOX")
	if !filepath.IsAbs(outbox) {
		return none.New(c)
	}
	phones := make(map[string]bool)
	for _, phone := range strings.Split(os.Getenv("PRIVATECHAT_LOCALTEST_PHONES"), ",") {
		phone = strings.TrimSpace(phone)
		if !localTestPhonePattern.MatchString(phone) {
			return none.New(c)
		}
		phones[phone] = true
	}
	if len(phones) == 0 {
		return none.New(c)
	}
	if err := os.MkdirAll(outbox, 0o700); err != nil {
		return none.New(c)
	}
	if err := os.Chmod(outbox, 0o700); err != nil {
		return none.New(c)
	}
	return &localTestVerifyCode{phones: phones, outbox: outbox}
}

func (v *localTestVerifyCode) deliveryPath(codeHash string) string {
	digest := sha256.Sum256([]byte(codeHash))
	return filepath.Join(v.outbox, hex.EncodeToString(digest[:])+".json")
}

func (v *localTestVerifyCode) SendSmsVerifyCode(ctx context.Context, phoneNumber, code, codeHash string) (string, error) {
	if err := ctx.Err(); err != nil {
		return "", err
	}
	if !v.phones[phoneNumber] || !localTestCodePattern.MatchString(code) || codeHash == "" {
		return "", errors.New("localtest requires an allowed test number and a valid transaction")
	}
	var nonce [32]byte
	if _, err := rand.Read(nonce[:]); err != nil {
		return "", err
	}
	binding := base64.RawURLEncoding.EncodeToString(nonce[:])
	record := localTestOTP{
		PhoneNumber: phoneNumber,
		CodeHash:    codeHash,
		Code:        code,
		Binding:     binding,
		ExpiresAt:   time.Now().Add(3 * time.Minute).Unix(),
	}
	data, err := json.Marshal(record)
	if err != nil {
		return "", err
	}
	file, err := os.CreateTemp(v.outbox, ".otp-*")
	if err != nil {
		return "", err
	}
	defer os.Remove(file.Name())
	if _, err := file.Write(data); err != nil {
		file.Close()
		return "", err
	}
	if err := file.Close(); err != nil {
		return "", err
	}
	if err := os.Rename(file.Name(), v.deliveryPath(codeHash)); err != nil {
		return "", err
	}
	return binding, nil
}

func (v *localTestVerifyCode) VerifySmsCode(ctx context.Context, codeHash, code, extraData string) error {
	if err := ctx.Err(); err != nil {
		return err
	}
	data, err := os.ReadFile(v.deliveryPath(codeHash))
	if err != nil {
		return mtproto.ErrPhoneCodeInvalid
	}
	var record localTestOTP
	if json.Unmarshal(data, &record) != nil || !v.phones[record.PhoneNumber] || record.ExpiresAt <= time.Now().Unix() {
		return mtproto.ErrPhoneCodeInvalid
	}
	if subtle.ConstantTimeCompare([]byte(codeHash), []byte(record.CodeHash)) != 1 ||
		subtle.ConstantTimeCompare([]byte(code), []byte(record.Code)) != 1 ||
		subtle.ConstantTimeCompare([]byte(extraData), []byte(record.Binding)) != 1 {
		return mtproto.ErrPhoneCodeInvalid
	}
	return nil
}

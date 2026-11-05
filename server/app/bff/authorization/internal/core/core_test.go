package core

import (
	"testing"

	"github.com/teamgram/proto/mtproto"
)

func TestCheckPhoneNumberInvalidUsesSharedLocalTestPool(t *testing.T) {
	tests := []struct {
		name      string
		input     string
		wantPhone string
		wantErr   error
	}{
		{name: "primary smoke number", input: "+42400", wantPhone: "42400"},
		{name: "second emulator number", input: "42401", wantPhone: "42401"},
		{name: "spaced android input", input: "+4 2402", wantPhone: "42402"},
		{name: "range end", input: "+42409", wantPhone: "42409"},
		{name: "admin smoke number", input: "42777", wantPhone: "42777"},
		{name: "outside local range", input: "+42410", wantErr: mtproto.ErrPhoneNumberInvalid},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			_, gotPhone, err := checkPhoneNumberInvalid(tt.input)
			if tt.wantErr != nil {
				if err == nil {
					t.Fatalf("checkPhoneNumberInvalid(%q) error = nil, want %v", tt.input, tt.wantErr)
				}
				return
			}
			if err != nil {
				t.Fatalf("checkPhoneNumberInvalid(%q) error = %v", tt.input, err)
			}
			if gotPhone != tt.wantPhone {
				t.Fatalf("checkPhoneNumberInvalid(%q) phone = %q, want %q", tt.input, gotPhone, tt.wantPhone)
			}
		})
	}
}

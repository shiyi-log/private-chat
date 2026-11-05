// Copyright 2022 Teamgram Authors
//  All rights reserved.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//   http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//
// Author: teamgramio (teamgram.io@gmail.com)
//

package phonenumber

import (
	"fmt"
	"testing"

	"github.com/teamgram/proto/mtproto"
)

//func TestCheckPhoneNumber(t *testing.T) {
//	phone, err := CheckAndGetPhoneNumber("+639611429606")
//	fmt.Println(phone, err)
//}
//
//func TestMakePhoneNumber(t *testing.T) {
//	pNumber, err := MakePhoneNumberHelper(""+
//		"588021430", "CN")
//	if err != nil {
//		fmt.Println(err)
//		return
//	}
//
//	fmt.Println(pNumber.GetNormalizeDigits())
//}

func TestMakePhoneNumber2(t *testing.T) {
	// 63 969 025 1456
	// 63 995 659 1464
	pNumber, err := MakePhoneNumberHelper("+63 969 659 1464", "")
	if err != nil {
		fmt.Println(err)
		return
	}

	fmt.Println(pNumber)
	fmt.Println(pNumber.GetNormalizeDigits(), ", ", pNumber.GetRegionCode(), ", ", pNumber.GetCountryCode())
}

func TestCheckPhoneNumberInvalidLocalTestPhones(t *testing.T) {
	tests := []struct {
		name      string
		input     string
		wantPhone string
		wantErr   error
	}{
		{name: "primary android smoke number with plus", input: "+42400", wantPhone: "42400"},
		{name: "primary android smoke number without plus", input: "42400", wantPhone: "42400"},
		{name: "second account number with plus", input: "+42401", wantPhone: "42401"},
		{name: "range end number without plus", input: "42409", wantPhone: "42409"},
		{name: "spaces from client input", input: "+4 2402", wantPhone: "42402"},
		{name: "reserved admin smoke number", input: "+42777", wantPhone: "42777"},
		{name: "outside local range", input: "+42410", wantErr: mtproto.ErrPhoneNumberInvalid},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			_, gotPhone, err := CheckPhoneNumberInvalid(tt.input)
			if tt.wantErr != nil {
				if err == nil {
					t.Fatalf("CheckPhoneNumberInvalid(%q) error = nil, want %v", tt.input, tt.wantErr)
				}
				return
			}
			if err != nil {
				t.Fatalf("CheckPhoneNumberInvalid(%q) error = %v", tt.input, err)
			}
			if gotPhone != tt.wantPhone {
				t.Fatalf("CheckPhoneNumberInvalid(%q) phone = %q, want %q", tt.input, gotPhone, tt.wantPhone)
			}
		})
	}
}

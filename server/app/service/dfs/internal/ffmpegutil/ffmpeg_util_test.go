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

package ffmpegutil

import (
	"bytes"
	"image"
	"image/color"
	"image/gif"
	"image/jpeg"
	"os"
	"os/exec"
	"path/filepath"
	"testing"
)

func TestConvertGifToMp4(t *testing.T) {
	for _, tool := range []string{"ffmpeg", "ffprobe"} {
		if _, err := exec.LookPath(tool); err != nil {
			t.Fatalf("%s is required for this integration test: %v", tool, err)
		}
	}

	input := filepath.Join(t.TempDir(), "input.gif")
	if err := writeGIFFixture(input); err != nil {
		t.Fatalf("write GIF fixture: %v", err)
	}

	ffmpegUtil := NewFFmpegUtil()
	data, duration, err := ffmpegUtil.ConvertToMp4ByPipe(input, 64, 48)
	if err != nil {
		t.Fatalf("convert GIF to MP4: %v", err)
	}
	if len(data) == 0 {
		t.Fatal("conversion returned empty MP4 data")
	}
	if duration <= 0 {
		t.Fatalf("expected positive progress duration, got %d", duration)
	}

	md, err := ffmpegUtil.GetMetadataByPipe(data)
	if err != nil {
		t.Fatalf("read converted MP4 metadata: %v", err)
	}
	if w, h := GetWidthHeight(md); w != 64 || h != 48 {
		t.Fatalf("converted MP4 has size %dx%d, want 64x48", w, h)
	}
	if GetDuration(md) <= 0 {
		t.Fatalf("converted MP4 has invalid duration %q", md.Format.Duration)
	}

	firstFrame, err := ffmpegUtil.GetFirstFrameByPipe(data)
	if err != nil {
		t.Fatalf("extract first frame: %v", err)
	}
	if len(firstFrame) == 0 {
		t.Fatal("first-frame extraction returned empty data")
	}
	if _, err := jpeg.Decode(bytes.NewReader(firstFrame)); err != nil {
		t.Fatalf("decode extracted JPEG frame: %v", err)
	}
}

func writeGIFFixture(path string) error {
	palette := color.Palette{color.Black, color.White}
	animation := &gif.GIF{LoopCount: 0}
	for frameIndex := 0; frameIndex < 6; frameIndex++ {
		frame := image.NewPaletted(image.Rect(0, 0, 32, 24), palette)
		for y := 0; y < 24; y++ {
			for x := 0; x < 32; x++ {
				if (x+y+frameIndex)%2 == 0 {
					frame.SetColorIndex(x, y, 1)
				}
			}
		}
		animation.Image = append(animation.Image, frame)
		animation.Delay = append(animation.Delay, 100)
	}

	file, err := os.Create(path)
	if err != nil {
		return err
	}
	if err := gif.EncodeAll(file, animation); err != nil {
		_ = file.Close()
		return err
	}
	return file.Close()
}

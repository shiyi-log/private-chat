package test

import (
	"encoding/json"
	"errors"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"testing"

	"github.com/teamgram/teamgram-server/pkg/goffmpeg/ffmpeg"
	"github.com/teamgram/teamgram-server/pkg/goffmpeg/transcoder"
)

type probeResult struct {
	Format struct {
		Duration string `json:"duration"`
	} `json:"format"`
	Streams []struct {
		CodecType string `json:"codec_type"`
	} `json:"streams"`
}

func ffmpegConfig() ffmpeg.Configuration {
	return ffmpeg.Configuration{FfmpegBin: "ffmpeg", FfprobeBin: "ffprobe"}
}

func requireMediaTools(t *testing.T) {
	t.Helper()
	for _, tool := range []string{"ffmpeg", "ffprobe"} {
		if _, err := exec.LookPath(tool); err != nil {
			t.Fatalf("%s is required for goffmpeg integration tests: %v", tool, err)
		}
	}
}

func makeFixture(t *testing.T, name, muxer, codec string) string {
	t.Helper()
	requireMediaTools(t)
	path := filepath.Join(t.TempDir(), name)
	args := []string{
		"-nostdin", "-hide_banner", "-loglevel", "error",
		"-f", "lavfi", "-i", "testsrc2=size=64x48:rate=5",
		"-frames:v", "5", "-threads", "1", "-an", "-c:v", codec,
		"-pix_fmt", "yuv420p", "-f", muxer, path,
	}
	if output, err := exec.Command("ffmpeg", args...).CombinedOutput(); err != nil {
		t.Fatalf("create %s fixture: %v\n%s", name, err, output)
	}
	return path
}

func makeWavFixture(t *testing.T) string {
	t.Helper()
	requireMediaTools(t)
	path := filepath.Join(t.TempDir(), "input.wav")
	args := []string{
		"-nostdin", "-hide_banner", "-loglevel", "error",
		"-f", "lavfi", "-i", "sine=frequency=1000:sample_rate=44100",
		"-t", "1", "-threads", "1", "-c:a", "pcm_s16le", path,
	}
	if output, err := exec.Command("ffmpeg", args...).CombinedOutput(); err != nil {
		t.Fatalf("create WAV fixture: %v\n%s", err, output)
	}
	return path
}

func probeMedia(t *testing.T, path string) probeResult {
	t.Helper()
	output, err := exec.Command("ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type", "-of", "json", path).CombinedOutput()
	if err != nil {
		t.Fatalf("probe %s: %v\n%s", path, err, output)
	}
	var result probeResult
	if err := json.Unmarshal(output, &result); err != nil {
		t.Fatalf("decode ffprobe output for %s: %v", path, err)
	}
	return result
}

func assertTranscoded(t *testing.T, path, expectedStream string) {
	t.Helper()
	result := probeMedia(t, path)
	duration, err := strconv.ParseFloat(result.Format.Duration, 64)
	if err != nil || duration <= 0 {
		t.Fatalf("transcoded file has invalid duration %q: %v", result.Format.Duration, err)
	}
	for _, stream := range result.Streams {
		if stream.CodecType == expectedStream {
			return
		}
	}
	t.Fatalf("transcoded file has no %s stream: %+v", expectedStream, result.Streams)
}

func transcodeFixture(t *testing.T, name, muxer, codec string) {
	t.Helper()
	input := makeFixture(t, name, muxer, codec)
	output := filepath.Join(t.TempDir(), name+".mp4")
	trans := new(transcoder.Transcoder)
	trans.SetConfiguration(ffmpegConfig())
	if err := trans.Initialize(input, output); err != nil {
		t.Fatalf("initialize transcoder for %s: %v", name, err)
	}
	trans.MediaFile().SetThreads(1)
	trans.MediaFile().SetVideoCodec("mpeg4")
	if err := <-trans.Run(false); err != nil {
		t.Fatalf("transcode %s: %v", name, err)
	}
	assertTranscoded(t, output, "video")
}

func TestInputNotFound(t *testing.T) {
	requireMediaTools(t)
	trans := new(transcoder.Transcoder)
	trans.SetConfiguration(ffmpegConfig())
	err := trans.Initialize(filepath.Join(t.TempDir(), "missing.mkv"), filepath.Join(t.TempDir(), "out.mp4"))
	if err == nil {
		t.Fatal("expected ffprobe to reject a missing input")
	}
}

func TestTranscoding3GP(t *testing.T) {
	transcodeFixture(t, "input.3gp", "3gp", "mpeg4")
}

func TestTranscodingAVI(t *testing.T) {
	transcodeFixture(t, "input.avi", "avi", "mpeg4")
}

func TestTranscodingFLV(t *testing.T) {
	transcodeFixture(t, "input.flv", "flv", "flv1")
}

func TestTranscodingMKV(t *testing.T) {
	transcodeFixture(t, "input.mkv", "matroska", "mpeg4")
}

func TestTranscodingMOV(t *testing.T) {
	transcodeFixture(t, "input.mov", "mov", "mpeg4")
}

func TestTranscodingMPEG(t *testing.T) {
	transcodeFixture(t, "input.mpeg", "mpeg", "mpeg2video")
}

func TestTranscodingOGG(t *testing.T) {
	transcodeFixture(t, "input.ogg", "ogg", "libtheora")
}

func TestTranscodingWAV(t *testing.T) {
	requireMediaTools(t)
	input := makeWavFixture(t)
	output := filepath.Join(t.TempDir(), "wav.mp4")
	trans := new(transcoder.Transcoder)
	trans.SetConfiguration(ffmpegConfig())
	if err := trans.Initialize(input, output); err != nil {
		t.Fatalf("initialize WAV transcoder: %v", err)
	}
	trans.MediaFile().SetThreads(1)
	trans.MediaFile().SetAudioCodec("aac")
	if err := <-trans.Run(false); err != nil {
		t.Fatalf("transcode WAV: %v", err)
	}
	assertTranscoded(t, output, "audio")
}

func TestTranscodingWEBM(t *testing.T) {
	transcodeFixture(t, "input.webm", "webm", "libvpx")
}

func TestTranscodingWMV(t *testing.T) {
	transcodeFixture(t, "input.wmv", "asf", "wmv2")
}

func TestTranscodingProgress(t *testing.T) {
	input := makeFixture(t, "progress.mkv", "matroska", "mpeg4")
	output := filepath.Join(t.TempDir(), "progress.mp4")
	trans := new(transcoder.Transcoder)
	trans.SetConfiguration(ffmpegConfig())
	if err := trans.Initialize(input, output); err != nil {
		t.Fatalf("initialize progress transcoder: %v", err)
	}
	trans.MediaFile().SetThreads(1)
	trans.MediaFile().SetVideoCodec("mpeg4")
	done := trans.Run(true)
	progress := trans.Output()
	updates := 0
	for range progress {
		updates++
	}
	if err := <-done; err != nil {
		t.Fatalf("run progress transcode: %v", err)
	}
	if updates == 0 {
		t.Fatal("progress transcode returned no progress updates")
	}
	assertTranscoded(t, output, "video")
}

func TestTranscodePipes(t *testing.T) {
	requireMediaTools(t)
	input := makeFixture(t, "pipe.mkv", "matroska", "mpeg4")
	trans := new(transcoder.Transcoder)
	trans.SetConfiguration(ffmpegConfig())
	if err := trans.InitializeEmptyTranscoder(); err != nil {
		t.Fatalf("initialize pipe transcoder: %v", err)
	}
	inputWriter, err := trans.CreateInputPipe()
	if err != nil {
		t.Fatalf("create input pipe: %v", err)
	}
	t.Cleanup(func() { _ = inputWriter.Close() })
	outputReader, err := trans.CreateOutputPipe("mp4")
	if err != nil {
		t.Fatalf("create output pipe: %v", err)
	}
	t.Cleanup(func() { _ = outputReader.Close() })
	trans.MediaFile().SetThreads(1)
	trans.MediaFile().SetVideoCodec("mpeg4")

	inputFile, err := os.Open(input)
	if err != nil {
		t.Fatalf("open pipe fixture: %v", err)
	}
	inputDone := make(chan error, 1)
	go func() {
		_, copyErr := io.Copy(inputWriter, inputFile)
		closeErr := inputWriter.Close()
		inputDone <- errors.Join(copyErr, closeErr, inputFile.Close())
	}()

	outputDone := make(chan struct {
		data []byte
		err  error
	}, 1)
	go func() {
		data, readErr := io.ReadAll(outputReader)
		outputDone <- struct {
			data []byte
			err  error
		}{data: data, err: readErr}
	}()
	if err := <-trans.Run(false); err != nil {
		t.Fatalf("run pipe transcode: %v", err)
	}
	if err := <-inputDone; err != nil {
		t.Fatalf("write pipe input: %v", err)
	}
	pipeOutput := <-outputDone
	if pipeOutput.err != nil {
		t.Fatalf("read pipe output: %v", pipeOutput.err)
	}
	if len(pipeOutput.data) == 0 {
		t.Fatal("pipe transcode returned empty output")
	}
	outputPath := filepath.Join(t.TempDir(), "pipe-output.mp4")
	if err := os.WriteFile(outputPath, pipeOutput.data, 0600); err != nil {
		t.Fatalf("write pipe output fixture: %v", err)
	}
	assertTranscoded(t, outputPath, "video")
}

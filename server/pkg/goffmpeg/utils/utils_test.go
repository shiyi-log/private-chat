package utils

import "testing"

func TestDurToSec(t *testing.T) {
	tests := []struct {
		name  string
		input string
		want  float64
	}{
		{name: "ffmpeg clock timestamp", input: "00:00:06.50", want: 6.5},
		{name: "ffprobe seconds", input: "6.500000", want: 6.5},
		{name: "invalid duration", input: "N/A", want: 0},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := DurToSec(tt.input); got != tt.want {
				t.Fatalf("DurToSec(%q) = %v, want %v", tt.input, got, tt.want)
			}
		})
	}
}

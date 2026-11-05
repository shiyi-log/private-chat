package svc

import (
	"os"
	"testing"

	"github.com/teamgram/teamgram-server/app/bff/configuration/internal/config"
)

func TestNewServiceContextRejectsMissingClientConfiguration(t *testing.T) {
	inConfigurationDirectory(t)
	defer func() {
		if recover() == nil {
			t.Error("service initialized without required config.json")
		}
	}()
	NewServiceContext(config.Config{})
}

func TestNewServiceContextRejectsMalformedClientConfiguration(t *testing.T) {
	inConfigurationDirectory(t)
	if err := os.WriteFile("config.json", []byte("{"), 0600); err != nil {
		t.Fatal(err)
	}
	defer func() {
		if recover() == nil {
			t.Error("service initialized with malformed config.json")
		}
	}()
	NewServiceContext(config.Config{})
}

func TestNewServiceContextLoadsDeploymentClientConfiguration(t *testing.T) {
	inConfigurationDirectory(t)
	if err := os.WriteFile("config.json", []byte(`{"data2":{"predicate_name":"config","this_dc":9,"webfile_dc_id":8,"dc_txt_domain_name":"deployment.example"}}`), 0600); err != nil {
		t.Fatal(err)
	}
	ctx := NewServiceContext(config.Config{})
	if ctx.ClientConfig == nil || ctx.ClientConfig.GetThisDc() != 9 || ctx.ClientConfig.GetWebfileDcId() != 8 || ctx.ClientConfig.GetDcTxtDomainName() != "deployment.example" {
		t.Fatalf("deployment configuration not loaded: %v", ctx.ClientConfig)
	}
}

func inConfigurationDirectory(t *testing.T) {
	t.Helper()
	previous, err := os.Getwd()
	if err != nil {
		t.Fatal(err)
	}
	if err := os.Chdir(t.TempDir()); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() {
		if err := os.Chdir(previous); err != nil {
			t.Error(err)
		}
	})
}

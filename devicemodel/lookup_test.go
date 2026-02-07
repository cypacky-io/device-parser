package devicemodel

import (
	"strings"
	"sync"
	"testing"
)

func TestLookupKnownIOSModel(t *testing.T) {
	name := Lookup("iPhone18,1")
	if name == "" {
		t.Fatalf("Lookup(iPhone18,1) 应返回非空")
	}
	if !strings.Contains(strings.ToLower(name), "iphone") {
		t.Fatalf("Lookup(iPhone18,1) 返回异常: %q", name)
	}
}

func TestLookupWithPlatformWatchOS(t *testing.T) {
	name := LookupWithPlatform(PlatformWatchOS, "Watch1,1")
	if name == "" {
		t.Fatalf("LookupWithPlatform(watchos, Watch1,1) 应返回非空")
	}
}

func TestLookupWithPlatformIPadOS(t *testing.T) {
	name := LookupWithPlatform(PlatformIPADOS, "iPad16,3")
	if name == "" {
		t.Fatalf("LookupWithPlatform(ipados, iPad16,3) 应返回非空")
	}
}

func TestLookupWithPlatformMacOS(t *testing.T) {
	name := LookupWithPlatform(PlatformMACOS, "iMac11,2")
	if name == "" {
		t.Fatalf("LookupWithPlatform(macos, iMac11,2) 应返回非空")
	}
}

func TestLookupWithPlatformVisionOS(t *testing.T) {
	name := LookupWithPlatform(PlatformVisionOS, "RealityDevice14,1")
	if name == "" {
		t.Fatalf("LookupWithPlatform(visionos, RealityDevice14,1) 应返回非空")
	}
}

func TestLookupUnknownModel(t *testing.T) {
	name := Lookup("Unknown,0")
	if name != "" {
		t.Fatalf("未知型号应返回空字符串，got=%q", name)
	}
}

func TestLookupWithInvalidPlatform(t *testing.T) {
	name := LookupWithPlatform("android", "SM-S9280")
	if name != "" {
		t.Fatalf("非法平台应返回空字符串，got=%q", name)
	}
}

func TestDataVersion(t *testing.T) {
	repo, ref, syncedAt := DataVersion()
	if strings.TrimSpace(repo) == "" {
		t.Fatalf("DataVersion upstream repo 不能为空")
	}
	if strings.TrimSpace(ref) == "" {
		t.Fatalf("DataVersion upstream ref 不能为空")
	}
	if strings.TrimSpace(syncedAt) == "" {
		t.Fatalf("DataVersion synced time 不能为空")
	}
}

func TestConcurrentLookup(t *testing.T) {
	codes := []struct {
		platform string
		code     string
	}{
		{PlatformIOS, "iPhone18,1"},
		{PlatformIPADOS, "iPad16,3"},
		{PlatformMACOS, "iMac11,2"},
		{PlatformIOS, "iPad16,3"},
		{PlatformTVOS, "AppleTV14,1"},
		{PlatformWatchOS, "Watch7,1"},
		{PlatformVisionOS, "RealityDevice14,1"},
		{"", "iPhone18,1"},
		{"unknown", "foo"},
	}

	var wg sync.WaitGroup
	for i := 0; i < 100; i++ {
		for _, c := range codes {
			wg.Add(1)
			go func(platform, code string) {
				defer wg.Done()
				_ = LookupWithPlatform(platform, code)
			}(c.platform, c.code)
		}
	}
	wg.Wait()
}

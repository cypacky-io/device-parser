package devicemodel

import (
	"embed"
	"encoding/json"
	"strings"
	"sync"
)

const (
	PlatformIOS      = "ios"
	PlatformIPADOS   = "ipados"
	PlatformMACOS    = "macos"
	PlatformTVOS     = "tvos"
	PlatformWatchOS  = "watchos"
	PlatformVisionOS = "visionos"
)

//go:embed data/ios-device-identifiers.json data/mac-device-identifiers.json data/tvos-device-identifiers.json data/watchos-device-identifiers.json data/visionos-device-identifiers.json data/UPSTREAM.json
var embeddedData embed.FS

type upstreamMeta struct {
	UpstreamRepo string `json:"upstream_repo"`
	UpstreamRef  string `json:"upstream_ref"`
	UpstreamSHA  string `json:"upstream_sha"`
	SyncedAtUTC  string `json:"synced_at_utc"`
}

var (
	loadOnce sync.Once

	iosMap      map[string]string
	macosMap    map[string]string
	tvosMap     map[string]string
	watchosMap  map[string]string
	visionosMap map[string]string
	meta        upstreamMeta
)

func Lookup(code string) string {
	return LookupWithPlatform(PlatformIOS, code)
}

func LookupWithPlatform(platform, code string) string {
	loadAll()

	code = strings.TrimSpace(code)
	if code == "" {
		return ""
	}

	switch normalizePlatform(platform) {
	case PlatformIOS:
		return iosMap[code]
	case PlatformIPADOS:
		return iosMap[code]
	case PlatformMACOS:
		return macosMap[code]
	case PlatformTVOS:
		return tvosMap[code]
	case PlatformWatchOS:
		return watchosMap[code]
	case PlatformVisionOS:
		return visionosMap[code]
	default:
		return ""
	}
}

func DataVersion() (upstreamRepo, upstreamRef, syncedAtUTC string) {
	loadAll()
	return meta.UpstreamRepo, meta.UpstreamRef + " sha:" + meta.UpstreamSHA, meta.SyncedAtUTC
}

func normalizePlatform(platform string) string {
	platform = strings.TrimSpace(strings.ToLower(platform))
	if platform == "" {
		return PlatformIOS
	}
	return platform
}

func loadAll() {
	loadOnce.Do(func() {
		iosMap = readDeviceMap("data/ios-device-identifiers.json")
		macosMap = readDeviceMap("data/mac-device-identifiers.json")
		tvosMap = readDeviceMap("data/tvos-device-identifiers.json")
		watchosMap = readDeviceMap("data/watchos-device-identifiers.json")
		visionosMap = readDeviceMap("data/visionos-device-identifiers.json")
		meta = readUpstreamMeta("data/UPSTREAM.json")
	})
}

func readDeviceMap(path string) map[string]string {
	out := map[string]string{}
	b, err := embeddedData.ReadFile(path)
	if err != nil {
		return out
	}

	var raw map[string]any
	if err := json.Unmarshal(b, &raw); err != nil {
		return out
	}
	for key, value := range raw {
		if modelName := firstModelName(value); modelName != "" {
			out[key] = modelName
		}
	}

	return out
}

func firstModelName(value any) string {
	switch typed := value.(type) {
	case string:
		return strings.TrimSpace(typed)
	case []any:
		for _, item := range typed {
			if s, ok := item.(string); ok {
				s = strings.TrimSpace(s)
				if s != "" {
					return s
				}
			}
		}
	}
	return ""
}

func readUpstreamMeta(path string) upstreamMeta {
	var out upstreamMeta
	b, err := embeddedData.ReadFile(path)
	if err != nil {
		return out
	}
	_ = json.Unmarshal(b, &out)
	return out
}

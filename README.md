# device-parser

`device-parser` 是一个 Go 库项目，提供 `devicemodel` 包，用于把 Apple 设备硬件码（model identifier）映射为营销机型名。

例如：

- `iPhone18,1` -> `iPhone 17 Pro`
- `iMac11,2` -> `iMac (21.5-inch, Mid 2010)`
- `Watch1,1` -> `Apple Watch (1st generation)`
- `RealityDevice14,1` -> `Apple Vision Pro`

## 安装

```bash
go get github.com/cypacky-io/device-parser@latest
```

## 使用

```go
package main

import (
    "fmt"

    devicemodel "github.com/cypacky-io/device-parser"
)

func main() {
    fmt.Println(devicemodel.Lookup("iPhone18,1"))
    fmt.Printf("%+v\n", devicemodel.LookupDetailed("iPad16,3"))
    fmt.Println(devicemodel.LookupWithPlatform(devicemodel.PlatformIPADOS, "iPad16,3"))
    fmt.Println(devicemodel.LookupWithPlatform(devicemodel.PlatformMACOS, "iMac11,2"))
    fmt.Println(devicemodel.LookupWithPlatform(devicemodel.PlatformWatchOS, "Watch1,1"))
    fmt.Println(devicemodel.LookupWithPlatform(devicemodel.PlatformVisionOS, "RealityDevice14,1"))

    repo, ref, syncedAt := devicemodel.DataVersion()
    fmt.Println(repo, ref, syncedAt)
}
```

## API

- `devicemodel.Lookup(code string) string`
  - 自动跨平台查找（`ios` / `ipados` / `macos` / `tvos` / `watchos` / `visionos`）。
  - 未识别返回空字符串。

- `devicemodel.LookupDetailed(code string) LookupDetail`
  - 自动跨平台查找并返回 `{platform, name}`。
  - 未识别返回空对象（两个字段都为空）。

- `devicemodel.LookupWithPlatform(platform, code string) string`
  - 支持平台：`ios` / `ipados` / `macos` / `tvos` / `watchos` / `visionos`。
  - `platform` 为空时，等同于 `Lookup` 的自动匹配。
  - 未识别返回空字符串。

- `devicemodel.DataVersion() (upstreamRepo, upstreamRef, syncedAtUTC string)`
  - 返回内置数据的上游来源和同步时间。

## 数据来源

- Upstream: `kyle-seongwoo-jun/apple-device-identifiers`
- License: MIT

本仓库会通过 GitHub Actions 定时同步上游数据并自动创建 PR。

说明：上游并未单独提供 `ipados-device-identifiers.json`，因此 `ipados` 查询会复用 iOS 映射表中的 iPad 型号。

## 数据同步（手动）

```bash
python3 scripts/sync_apple_identifiers.py
```

支持可选参数：

- `--ref main`
- `--tag <tag>`
- `--sha <commit_sha>`

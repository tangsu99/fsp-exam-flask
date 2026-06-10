# Changelog

## [0.2.1] (Developing)

### Refactor

- 重命名 responses 表的 response_time 字段为 submit_time
- 为 responses 表添加 end_time 字段
- 重命名 users 表的 addtime 字段为 registered_at
- 删除了 surveys 表的 status 字段

### Bug Fixes

- 修复了答卷过期时间会动态变化的问题 (#2)
- 修复白名单用户信任链接口缺少必要属性的问题
- 修复初始化项目时默认管理员无法创建的问题 (#6)
- 修复其他问题

## [0.2.0] (2026-06-05)

### Features

- 添加投影相关接口

### Bug Fixes

- 修复了一些问题

# Changelog

## [0.2.3] (Developing)

## [0.2.2] (2026-06-16)

此次更新我们重构了大量的代码，几乎是重写了整个项目，将全部代码替换为最新写法并添加类型提示

### Refactor

- 重构 admin 接口
- 数据表类的基类从 `db.Model` 转为 `Base`，以获取更好的 pyright 等静态检查工具的支持
- 重构 ORM 调用，从 sqlalchemy1.0 写法全面转换为 sqlalchemy2.0 写法
- 为代码添加类型提示以提供更好的静态检查支持
- 使用 Enum 标注数据库字段

## [0.2.1] (2026-06-10)

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

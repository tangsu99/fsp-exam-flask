# Changelog

## [0.2.3] (Developing)

### Features

- 添加生产环境的数据库迁移脚本
- 默认配置添加'开服日期'项
- 默认配置添加'在线人数采集间隔'项
- 生产环境用 gunicorn 跑的时候自动关闭 debug 模式

### Refactor

- 重构问卷和阅卷相关代码
- OPTIONS 预检请求统一返回 204

### Bug Fixes

- 修复 `/admin/config/set` 的字段问题
- 修复 `/admin/survey/<int:sid>` 和 `/survey/survey/<int:sid>` 中图片列表的字段错误

## [0.2.2] (2026-06-29)

此次更新我们重构了大量的代码并引入单元测试，将全部代码替换为最新写法并添加类型提示，以保障代码质量。

### Features

- 添加 Profile 表、Statuslog 表
- 添加自定义背景接口
- 添加修改用户名接口
- 添加仪表盘相关接口
- 合并了来自 fsp-mcstatuslog 的功能：采集服务器玩家在线人数
- 答卷状态 Enum 添加超时状态

### Refactor

- 重构 admin 接口
- 数据表类的基类从 `db.Model` 转为 `Base`，以获取更好的 pyright 等静态检查工具的支持
- 重构 ORM 调用，从 sqlalchemy1.0 写法全面转换为 sqlalchemy2.0 写法
- 为代码添加类型提示以提供更好的静态检查支持
- 使用 Enum 标注数据库字段

### Bug Fixes

- 修复 default_config 字段错误
- 修复了开始考试之后, 更改 URL 地址可以访问其他问卷的问题，同时在提交答卷时也对问卷ID和服务器记录做比对 (#8)
- 修复了 Response 表的 submit_time 和 end_time 字段缺少空值处理的问题并修正字段类型标注 (#9)

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

# 项目接口文档

## 概述

- `Base URL`: `http://127.0.0.1:5000`
- `Content-Type`: `application/json`
- `Authorization`: `Bearer <token>`
- `/dashboard/*` 及大部分用户接口需要登录
- `/admin/*` 接口需要管理员权限
- `/api/usersInfo` 由 MC 服务端上报数据，数据保存在内存中，不写入数据库

---

## 全局返回说明

多数接口返回标准 JSON：

```json
{
  "code": 0,
  "desc": "success",
  "data": {}
}
```

- `code`: 0 表示成功，非 0 表示失败
- `desc`: 结果说明
- `data`: 业务数据

部分接口也可能直接返回对象、列表或字符串。

---

## 1. MC 上报和仪表盘接口

### 1.1 MC 用户信息上报

- 方法：`POST`
- 路径：`/api/usersInfo`
- 认证：`Authorization: Bearer <token>`
- 描述：MC 服务端上报在线用户统计和在线玩家数据，写入内存缓存

请求示例：

```json
{
  "user_count": 123,
  "user_w_list_count": 45,
  "online_players": [
    {
      "playerName": "player1",
      "playerUuid": "uuid-1234",
      "currentServer": "server-1"
    }
  ]
}
```

字段说明：

- `user_count`: 已注册用户总数
- `user_w_list_count`: 白名单用户数量
- `online_players`: 在线玩家列表
- `online_players[].playerName`: 玩家名称
- `online_players[].playerUuid`: 玩家 UUID
- `online_players[].currentServer`: 当前服务器

成功响应：

```json
{
  "code": 0,
  "desc": "上报成功"
}
```

错误响应：

```json
{
  "code": 1,
  "desc": "请求数据格式错误"
}
```

```json
{
  "code": 1,
  "desc": "字段类型错误"
}
```

---

### 1.2 获取仪表盘用户概览

- 方法：`GET`
- 路径：`/dashboard/usersInfo`
- 认证：`Authorization: Bearer <token>`
- 描述：读取 MC 上报到的用户统计和在线玩家数据

成功响应：

```json
{
  "data": {
    "user_count": 123,
    "user_w_list_count": 45,
    "online_players": [
      {
        "playerName": "player1",
        "playerUuid": "uuid-1234",
        "currentServer": "server-1"
      }
    ]
  }
}
```

### 1.3 获取仪表盘系统概览

- 方法：`GET`
- 路径：`/dashboard/sysInfo`
- 认证：`Authorization: Bearer <token>`
- 描述：获取系统级统计数据

成功响应：

```json
{
  "data": {
    "ban_wl_count": 0,
    "ban_count": 0,
    "whitelist_block_count": 0,
    "response_not_reviewed_count": 0,
    "guarantee_not_passed_count": 0,
    "question_count": 0,
    "survey_count": 0,
    "schematic_count": 0
  }
}
```

数据说明：

- `ban_wl_count`: 白名单封禁数
- `ban_count`: 封禁数
- `whitelist_block_count`: 白名单拦截次数
- `response_not_reviewed_count`: 未审核答卷数
- `guarantee_not_passed_count`: 待通过担保数
- `question_count`: 题目总数
- `survey_count`: 问卷总数
- `schematic_count`: 投影总数

---

## 2. 公共游戏接口 (/api)

### 2.1 验证玩家白名单

- 方法：`POST`
- 路径：`/api/whitelist`
- 认证：`Authorization: Bearer <token>`

请求示例：

```json
{
  "uuid": "uuid-1234",
  "name": "player1"
}
```

成功响应：

```json
{
  "code": 0,
  "desc": "在白名单中",
  "uuid": "uuid-1234",
  "name": "player1"
}
```

失败响应：

```json
{
  "code": 1,
  "desc": "not fond"
}
```

```json
{
  "code": 3,
  "desc": "账户状态异常！"
}
```

### 2.2 添加白名单

- 方法：`POST`
- 路径：`/api/whitelistAdd`
- 认证：`Authorization: Bearer <token>`

请求示例：

```json
{
  "uuid": "uuid-1234",
  "name": "player1"
}
```

成功响应：

```json
{
  "code": 0,
  "desc": "成功"
}
```

---

## 3. 认证接口 (/auth)

### 3.1 登录

- 方法：`POST`
- 路径：`/auth/login`

请求示例：

```json
{
  "username": "user1",
  "password": "pass123"
}
```

成功响应：

```json
{
  "code": 0,
  "token": "<jwt-token>",
  "username": "user1",
  "avatar": "avatar-uuid",
  "isAdmin": false,
  "play_permission": true
}
```

### 3.2 注销

- 方法：`POST`
- 路径：`/auth/logout`
- 认证：`Authorization: Bearer <token>`

成功响应：

```json
{
  "code": 0,
  "desc": "退出成功"
}
```

### 3.3 注册

- 方法：`POST`
- 路径：`/auth/register`

请求示例：

```json
{
  "username": "user1",
  "userQQ": "123456789",
  "password": "pass123",
  "passwordAgain": "pass123"
}
```

成功响应：

```json
{
  "code": 0,
  "desc": "注册成功",
  "token": "<jwt-token>",
  "username": "user1",
  "avatar": "avatar-uuid",
  "isAdmin": false
}
```

### 3.4 登录状态检查

- 方法：`GET`
- 路径：`/auth/check`

成功响应：

```json
{
  "code": 0,
  "username": "user1",
  "avatar": "avatar-uuid",
  "isAdmin": false,
  "play_permission": true
}
```

未登录响应：

```json
{
  "code": 1,
  "desc": "User is not logged in",
  "avatar": "b83565e6-b0d0-4265-bb4f-fdb5e8d00655"
}
```

### 3.5 请求找回密码

- 方法：`POST`
- 路径：`/auth/findPassword`

请求示例：

```json
{
  "userQQ": "123456789"
}
```

成功响应：

```json
{
  "code": 0,
  "desc": "发送成功！请查找邮箱!"
}
```

### 3.6 重置密码

- 方法：`PUT`
- 路径：`/auth/findPassword?token=<token>`

请求示例：

```json
{
  "password": "newPass123"
}
```

### 3.7 请求激活邮件

- 方法：`POST`
- 路径：`/auth/reqActivation`
- 认证：`Authorization: Bearer <token>`

成功响应：

```json
{
  "code": 0,
  "desc": "发送成功！请查找邮箱!"
}
```

### 3.8 激活账户

- 方法：`PUT`
- 路径：`/auth/activation?token=<token>`

请求示例：

```json
{
  "username": "user1"
}
```

成功响应：

```json
{
  "code": 0,
  "desc": "激活成功！"
}
```

---

## 4. 用户接口 (/user)

### 4.1 当前用户信息

- 方法：`GET`
- 路径：`/user/getInfo`
- 认证：`Authorization: Bearer <token>`

成功响应：

```json
{
  "code": 0,
  "data": {
    "id": 1,
    "username": "user1",
    "user_qq": "123456789",
    "role": "user",
    "addtime": "2026-01-01T00:00:00+00:00",
    "avatar": "avatar-uuid",
    "status": 1,
    "play_permission": true
  }
}
```

### 4.2 当前用户白名单

- 方法：`GET`
- 路径：`/user/getWhitelist`
- 认证：`Authorization: Bearer <token>`

成功响应：

```json
{
  "code": 0,
  "list": [
    {"id": 1, "name": "player1", "uuid": "uuid-1234"}
  ]
}
```

### 4.3 修改头像

- 方法：`POST`
- 路径：`/user/setAvatar`
- 认证：`Authorization: Bearer <token>`

请求示例：

```json
{
  "uuid": "avatar-uuid"
}
```

成功响应：

```json
{
  "code": 0,
  "desc": "头像修改成功！"
}
```

### 4.4 获取信任链

- 方法：`GET`
- 路径：`/user/getChainOfTrust`
- 认证：`Authorization: Bearer <token>`

查询参数：

- `uuid`: 玩家 UUID

成功响应：

```json
{
  "code": 0,
  "desc": "success",
  "data": {
    "playerUUID": "uuid-1234",
    "playerName": "player1",
    "chain": [
      {
        "guarantor": {
          "id": 2,
          "username": "guarantor1",
          "user_qq": "123456789",
          "avatar": "avatar-uuid"
        },
        "applicant": {
          "id": 1,
          "username": "applicant1",
          "user_qq": "987654321",
          "avatar": "avatar-uuid"
        }
      }
    ]
  }
}
```

---

## 5. 查询接口 (/query)

### 5.1 Query 测试

- 方法：`GET`
- 路径：`/query/`
- 认证：`Authorization: Bearer <token>`

响应：字符串 `is query api`

### 5.2 获取答卷列表

- 方法：`GET`
- 路径：`/query/response`
- 认证：`Authorization: Bearer <token>`

成功响应：

```json
{
  "code": 0,
  "desc": "成功! ",
  "list": [
    {
      "id": 1,
      "survey_name": "问卷名称",
      "responseTime": "2026-01-01T00:00:00+00:00",
      "state": false,
      "get_score": 90.0,
      "full_score": 100.0
    }
  ]
}
```

---

## 6. 问卷接口 (/survey)

### 6.1 获取问卷插槽

- 方法：`GET`
- 路径：`/survey/get_slots`
- 认证：`Authorization: Bearer <token>`

成功响应：

```json
{
  "code": 0,
  "desc": "成功! ",
  "list": [
    {"id": 1, "slotName": "插槽A", "mountedSID": 2}
  ]
}
```

### 6.2 获取问卷

- 方法：`GET`
- 路径：`/survey/survey/<int:sid>`
- 认证：`Authorization: Bearer <token>`

成功响应：

```json
{
  "id": 2,
  "name": "问卷名称",
  "description": "描述",
  "create_time": "2026-01-01T00:00:00+00:00",
  "ddl": "2026-01-01T01:00:00+00:00",
  "questions": [
    {
      "display_order": 1,
      "id": 10,
      "title": "题目一",
      "type": 1,
      "score": 5,
      "img_list": [],
      "options": [
        {"id": 101, "text": "选项A"}
      ]
    }
  ]
}
```

### 6.3 检查未完成问卷

- 方法：`POST`
- 路径：`/survey/check_survey`
- 认证：`Authorization: Bearer <token>`

成功响应：

```json
{
  "code": 0,
  "desc": "暂无问卷! "
}
```

失败响应：

```json
{
  "code": 1,
  "desc": "您有未完成问卷！",
  "response": 2
}
```

### 6.4 开始问卷

- 方法：`POST`
- 路径：`/survey/start_survey`
- 认证：`Authorization: Bearer <token>`

请求示例：

```json
{
  "sid": 2,
  "slot_name": "问卷名称",
  "playerName": "player1",
  "playerUUID": "uuid-1234"
}
```

成功响应：

```json
{
  "code": 0,
  "desc": "问卷开始！",
  "response": 2
}
```

### 6.5 提交问卷

- 方法：`POST`
- 路径：`/survey/complete_survey`
- 认证：`Authorization: Bearer <token>`

请求示例：

```json
[
  {"id": 10, "answer": ["A"]},
  {"id": 11, "answer": ["B"]}
]
```

成功响应：

```json
{
  "code": 0,
  "desc": "提交成功！",
  "score": 95.0
}
```

---

## 7. 投影接口 (/schematic)

### 7.1 基础测试

- 方法：`GET`
- 路径：`/schematic/`
- 认证：`Authorization: Bearer <token>`

响应：字符串 `is schematic api`

### 7.2 上传投影

- 方法：`POST`
- 路径：`/schematic/upload`
- 认证：`Authorization: Bearer <token>`
- 描述：使用 `multipart/form-data` 上传投影文件

表单字段：

- `name`: 投影名称
- `originalAuthor`: 原作者，空则使用当前登录用户名
- `desc`: 描述
- `type`: 投影类型整数
- `tags`: 空格分隔标签
- `isPublic`: `true` / `false`
- `gameVersion`: 游戏版本
- `backupLink`: 备份链接（必须是白名单 URL）
- `uploadFile`: 投影文件

成功响应：

```json
{
  "code": 0,
  "desc": "投影上传成功! "
}
```

### 7.3 更新投影

- 方法：`POST`
- 路径：`/schematic/update`
- 认证：`Authorization: Bearer <token>`
- 描述：更新投影元数据，可选上传新文件

表单字段：

- `id`: 投影 ID
- 其余字段与 `/schematic/upload` 相同

### 7.4 按类型分页查询

- 方法：`GET`
- 路径：`/schematic/query_by_type`
- 认证：`Authorization: Bearer <token>`

查询参数：

- `type`: 投影类型
- `page`: 页码，默认 1
- `per_page`: 每页数量，默认 10，最大 100

### 7.5 查询投影详情

- 方法：`GET`
- 路径：`/schematic/query_detail`
- 认证：`Authorization: Bearer <token>`

查询参数：

- `id`: 投影 ID

### 7.6 搜索投影

- 方法：`GET`
- 路径：`/schematic/search`
- 认证：`Authorization: Bearer <token>`

查询参数：

- `text`: 搜索文本
- `type`: 投影类型
- `page`: 页码
- `per_page`: 每页数量

### 7.7 下载投影

- 方法：`GET`
- 路径：`/schematic/download`
- 认证：`Authorization: Bearer <token>`

查询参数：

- `id`: 投影 ID

### 7.8 删除投影

- 方法：`GET`
- 路径：`/schematic/delete`
- 认证：`Authorization: Bearer <token>`

查询参数：

- `id`: 投影 ID

---

## 8. 担保接口 (/guarantee)

### 8.1 发起担保请求

- 方法：`POST`
- 路径：`/guarantee/request`
- 认证：`Authorization: Bearer <token>`

请求示例：

```json
{
  "userInfo": {
    "playerName": "player1",
    "playerUUID": "uuid-1234"
  },
  "guarantorInfo": {
    "playerName": "player2",
    "playerUUID": "uuid-5678"
  }
}
```

成功响应：

```json
{
  "code": 0,
  "desc": "有效期<小时>..."
}
```

### 8.2 查询担保记录

- 方法：`GET`
- 路径：`/guarantee/query_all`
- 认证：`Authorization: Bearer <token>`

成功响应：

```json
{
  "code": 0,
  "desc": "yes",
  "data": {
    "guarantee": [],
    "applicant": []
  }
}
```

### 8.3 处理担保动作

- 方法：`POST`
- 路径：`/guarantee/action`
- 认证：`Authorization: Bearer <token>`

请求示例：

```json
{
  "id": 1,
  "action": "accept"
}
```

可选 `action`：`accept` / `reject`

---

## 9. 管理后台接口 (/admin)

> 所有 `/admin/*` 接口均需要管理员权限。

### 9.1 配置管理

#### 9.1.1 查询配置

- 方法：`GET`
- 路径：`/admin/config/get`
- 查询参数：`key`, `page`, `per_page`

#### 9.1.2 新增配置

- 方法：`POST`
- 路径：`/admin/config/set`

请求示例：

```json
{
  "key": "site_name",
  "value": "FSP",
  "type": "string",
  "description": "站点名称"
}
```

#### 9.1.3 删除配置

- 方法：`POST`
- 路径：`/admin/config/delete`

请求示例：

```json
{
  "key": "site_name"
}
```

### 9.2 问卷管理

#### 9.2.1 创建问卷

- 方法：`POST`
- 路径：`/admin/survey/add`

请求示例：

```json
{
  "name": "问卷A",
  "description": "描述"
}
```

#### 9.2.2 删除问卷

- 方法：`POST`
- 路径：`/admin/survey/delete`

请求示例：

```json
{
  "id": 2
}
```

#### 9.2.3 修改问卷

- 方法：`POST`
- 路径：`/admin/survey/update`

请求示例：

```json
{
  "id": 2,
  "name": "问卷A",
  "desc": "新描述"
}
```

### 9.3 题目管理

#### 9.3.1 添加题目

- 方法：`POST`
- 路径：`/admin/question/add`

请求示例：

```json
{
  "surveyId": 2,
  "questions": [
    {
      "surveyId": 2,
      "title": "题目1",
      "type": 1,
      "score": 5,
      "display_order": 0,
      "options": [
        {"text": "A", "is_correct": true}
      ],
      "images": []
    }
  ]
}
```

#### 9.3.2 迁移题目

- 方法：`POST`
- 路径：`/admin/question/migration`

请求示例：

```json
{
  "target_sid": 3,
  "qid": 10
}
```

#### 9.3.3 编辑题目

- 方法：`POST`
- 路径：`/admin/question/edit`

请求示例：

```json
{
  "question": {
    "id": 10,
    "surveyId": 2,
    "title": "题目1修改",
    "type": 1,
    "score": 6,
    "display_order": 1,
    "options": [
      {"text": "A", "is_correct": true}
    ],
    "images": []
  }
}
```

#### 9.3.4 删除题目

- 方法：`POST`
- 路径：`/admin/question/delete`

请求示例：

```json
{
  "id": 10
}
```

#### 9.3.5 排序题目

- 方法：`POST`
- 路径：`/admin/question/sort`

请求示例：

```json
[
  {"id": 10, "display_order": 1},
  {"id": 11, "display_order": 2}
]
```

### 9.4 白名单 & 用户管理

#### 9.4.1 查询白名单

- 方法：`GET`
- 路径：`/admin/whitelist`
- 查询参数：`page`, `size`

#### 9.4.2 查询用户列表

- 方法：`GET`
- 路径：`/admin/users`
- 查询参数：`page`, `size`

#### 9.4.3 查询单个用户

- 方法：`GET`
- 路径：`/admin/user`
- 查询参数：`id`

#### 9.4.4 创建用户

- 方法：`POST`
- 路径：`/admin/user`

请求示例：

```json
{
  "username": "admin2",
  "userQQ": "123456789",
  "role": "admin",
  "password": "pass123"
}
```

#### 9.4.5 更新用户

- 方法：`PUT`
- 路径：`/admin/user`

请求示例：

```json
{
  "id": 3,
  "username": "admin2",
  "password": "newpass",
  "userQQ": "987654321",
  "addtime": "2026-01-01T00:00:00+00:00",
  "role": "admin",
  "status": 1
}
```

#### 9.4.6 删除用户

- 方法：`DELETE`
- 路径：`/admin/user`

请求示例：

```json
{
  "id": 3
}
```

### 9.5 问卷 & 答卷管理

#### 9.5.1 获取问卷列表

- 方法：`GET`
- 路径：`/admin/surveys`

#### 9.5.2 获取答卷列表

- 方法：`GET`
- 路径：`/admin/responses`
- 查询参数：`page`, `size`

#### 9.5.3 获取指定问卷

- 方法：`GET`
- 路径：`/admin/survey/<int:sid>`

#### 9.5.4 审核答卷

- 方法：`POST`
- 路径：`/admin/reviewed`

请求示例：

```json
{
  "response": 5,
  "status": 1
}
```

#### 9.5.5 获取答卷详情

- 方法：`GET`
- 路径：`/admin/detail/<int:resp_id>`

#### 9.5.6 批改题目分数

- 方法：`POST`
- 路径：`/admin/detail_score`

请求示例：

```json
{
  "score": 5,
  "questionId": 10,
  "responseId": 5
}
```

### 9.6 插槽管理

#### 9.6.1 新建插槽

- 方法：`POST`
- 路径：`/admin/slot/add`

请求示例：

```json
{
  "slotName": "插槽A",
  "mountedSID": 2
}
```

#### 9.6.2 修改插槽挂载

- 方法：`POST`
- 路径：`/admin/slot/set`

请求示例：

```json
{
  "id": 1,
  "mountedSID": 3
}
```

#### 9.6.3 删除插槽

- 方法：`POST`
- 路径：`/admin/slot/delete`

请求示例：

```json
{
  "id": 1
}
```

### 9.7 管理员查询担保列表

- 方法：`GET`
- 路径：`/admin/guarantee/get`
- 查询参数：`page`, `size`

---

## 10. 备注

- `/admin/*` 接口需管理员权限。
- `/user/*`, `/query/*`, `/survey/*`, `/schematic/*`, `/guarantee/*`, `/dashboard/*` 接口需登录。
- `/api/whitelist`, `/api/whitelistAdd` 使用 `token_check()` 认证。
- `/api/usersInfo` 为 MC 上报接口，数据保存在内存中，不写入数据库。
- `/schematic/upload`、`/schematic/update` 使用 `multipart/form-data`。

---

## 11. Apipost 导入说明

- 本文档使用标准 Markdown 结构组织接口说明、请求示例和响应示例。
- Apipost 可直接识别该文档大部分接口内容。
- 若需生成 `apipost_api_collection.json` 精确导入，请告知。

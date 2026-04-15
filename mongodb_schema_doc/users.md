# 集合：users（用户）

存储账号信息。模型见 `app/models/user.py`；注册/登录见 `app` 认证相关路由。

## 示例文档

```javascript
// users 集合
{
  "_id": ObjectId("65a1b2c3d4e5f6a7b8c9d0e1"),
  "username": "zhangsan",
  "password": "$2b$10$EnH3X5qZ...",  // bcrypt 加密后的密码
  "email": "zhangsan@example.com",
  "role": "user",                     // user | admin
  "status": "active",                 // active | disabled
  "created_at": ISODate("2024-01-15T10:30:00Z"),
  "last_login": ISODate("2024-01-20T14:25:00Z")
}
```

## 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `_id` | ObjectId | 用户唯一标识 |
| `username` | string | 用户名，唯一索引 |
| `password` | string | bcrypt 哈希密码 |
| `email` | string | 邮箱（可选），稀疏唯一索引 |
| `role` | string | 角色，默认为 user |
| `status` | string | 账号状态，active/disabled |
| `created_at` | date | 注册时间 |
| `last_login` | date | 最后登录时间 |

## 索引

见 `app/models/indexes.py` → `USER_INDEXES`，与 [indexes.mongodb.js](./indexes.mongodb.js) 中 `users` 段一致。

```javascript
db.users.createIndex({ username: 1 }, { unique: true })
db.users.createIndex({ email: 1 }, { sparse: true, unique: true })
db.users.createIndex({ created_at: -1 })
```

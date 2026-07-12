


## Password Hashing Architecture  

   [ Client Request ]
           │ (Plain text password via HTTPS)
           ▼
   [ Pydantic Schema ] ──► (Validates format, drops plain text from response)
           │
           ▼
 [ Security Utility Layer ] ──► (Hashes with Argon2id / Bcrypt)
           │
           ▼
  [ SQLAlchemy Model ] ──► (Stores ONLY the secure hash string)

## Message Idempotency

Message creation requires an `Idempotency-Key` header to make client retries safe:

```http
POST /rooms/{room_id}/messages
Authorization: Bearer <access_token>
Idempotency-Key: 8f4b1b7e-9e3a-4d8c-9c7f-123456789abc
Content-Type: application/json
```

```json
{
  "content": "Hola"
}
```

The API scopes each key by `room_id + sender_id + Idempotency-Key`, stores a backend-generated request hash, and rejects key reuse with different content using `409 Conflict`.

See [docs/idempotency.md](docs/idempotency.md) for the full technical reference and security practices.

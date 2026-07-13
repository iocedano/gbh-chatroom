def test_create_and_list_messages_include_sender_username(client, fixture_factory):
    sender = fixture_factory.user("sender")
    room = fixture_factory.room(sender)
    headers = fixture_factory.auth_headers(sender)

    create_response = client.post(
        f"/rooms/{room.id}/messages",
        json={"content": "  Hello room  "},
        headers={**headers, "Idempotency-Key": "message-1"},
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["content"] == "Hello room"
    assert created["sender_id"] == sender.id
    assert created["sender_username"] == "sender"

    list_response = client.get(f"/rooms/{room.id}/messages", headers=headers)
    assert list_response.status_code == 200
    assert list_response.json()[0]["sender_username"] == "sender"


def test_message_validation_for_blank_and_max_length(client, fixture_factory):
    sender = fixture_factory.user("sender")
    room = fixture_factory.room(sender)
    headers = fixture_factory.auth_headers(sender)

    blank_response = client.post(
        f"/rooms/{room.id}/messages",
        json={"content": "   "},
        headers={**headers, "Idempotency-Key": "blank"},
    )
    assert blank_response.status_code == 422

    too_long_response = client.post(
        f"/rooms/{room.id}/messages",
        json={"content": "x" * 1001},
        headers={**headers, "Idempotency-Key": "too-long"},
    )
    assert too_long_response.status_code == 422


def test_message_permissions_require_active_membership(client, fixture_factory):
    owner = fixture_factory.user("owner")
    outsider = fixture_factory.user("outsider")
    room = fixture_factory.room(owner)
    outsider_headers = fixture_factory.auth_headers(outsider)

    create_response = client.post(
        f"/rooms/{room.id}/messages",
        json={"content": "No access"},
        headers={**outsider_headers, "Idempotency-Key": "outsider"},
    )
    assert create_response.status_code == 403

    list_response = client.get(f"/rooms/{room.id}/messages", headers=outsider_headers)
    assert list_response.status_code == 403


def test_message_idempotency_retries_and_conflicts(client, fixture_factory):
    sender = fixture_factory.user("sender")
    room = fixture_factory.room(sender)
    headers = {**fixture_factory.auth_headers(sender), "Idempotency-Key": "same-key"}

    first_response = client.post(f"/rooms/{room.id}/messages", json={"content": "First"}, headers=headers)
    retry_response = client.post(f"/rooms/{room.id}/messages", json={"content": "First"}, headers=headers)
    conflict_response = client.post(f"/rooms/{room.id}/messages", json={"content": "Different"}, headers=headers)

    assert first_response.status_code == 201
    assert retry_response.status_code == 201
    assert retry_response.json()["id"] == first_response.json()["id"]
    assert conflict_response.status_code == 409

def test_room_crud(client, fixture_factory):
    owner = fixture_factory.user("owner")
    other = fixture_factory.user("other")
    owner_headers = fixture_factory.auth_headers(owner)
    other_headers = fixture_factory.auth_headers(other)

    create_response = client.post("/rooms", json={"name": "General"}, headers=owner_headers)
    assert create_response.status_code == 201
    room = create_response.json()
    assert room["name"] == "General"
    assert room["created_by"] == owner.id

    list_response = client.get("/rooms", headers=owner_headers)
    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()] == [room["id"]]

    read_response = client.get(f"/rooms/{room['id']}", headers=owner_headers)
    assert read_response.status_code == 200
    assert read_response.json()["name"] == "General"

    forbidden_update = client.patch(f"/rooms/{room['id']}", json={"name": "Nope"}, headers=other_headers)
    assert forbidden_update.status_code == 403

    update_response = client.patch(f"/rooms/{room['id']}", json={"name": "Announcements"}, headers=owner_headers)
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Announcements"

    forbidden_delete = client.delete(f"/rooms/{room['id']}", headers=other_headers)
    assert forbidden_delete.status_code == 403

    delete_response = client.delete(f"/rooms/{room['id']}", headers=owner_headers)
    assert delete_response.status_code == 204

    missing_response = client.get(f"/rooms/{room['id']}", headers=owner_headers)
    assert missing_response.status_code == 404


def test_join_leave_and_rejoin_room(client, fixture_factory):
    owner = fixture_factory.user("owner")
    member = fixture_factory.user("member")
    room = fixture_factory.room(owner)
    headers = fixture_factory.auth_headers(member)

    join_response = client.post(f"/rooms/{room.id}/join", headers=headers)
    assert join_response.status_code == 200
    membership = join_response.json()
    assert membership["room_id"] == room.id
    assert membership["user_id"] == member.id
    assert membership["left_at"] is None

    leave_response = client.post(f"/rooms/{room.id}/leave", headers=headers)
    assert leave_response.status_code == 200
    assert leave_response.json()["left_at"] is not None

    rejoin_response = client.post(f"/rooms/{room.id}/join", headers=headers)
    assert rejoin_response.status_code == 200
    assert rejoin_response.json()["id"] == membership["id"]
    assert rejoin_response.json()["left_at"] is None
